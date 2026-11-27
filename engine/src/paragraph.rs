//! 文章（ゲームが単語ごとに折り返して描くテキスト）の日本語化。
//!
//! ゲームは文章を「マークアップ文章」（単語の配列）に変換し（markup_process_string）、
//! 幅に合わせて各単語の位置を決め（markup_format）、単語ごとに addst / top_addst で描く。
//!
//! 1. markup_process_string: 元の英文に訳があれば、訳文を「1文字 = 1単語」に区切った文字列を渡す。
//!    作られた単語オブジェクトを記録する。どこから新しい単語かは、渡した文字列と実際の中身を
//!    後ろから突き合わせて決める（ゲームが先に古い単語を捨てることがあり、呼ぶ前の個数は当てにならない）。
//! 2. markup_format: 元の処理の後、記録した文章を画素幅で並べ直す。同じ行に続く日本語の単語は
//!    行の先頭の単語にまとめ、残りは何も描かない。
//! 3. addst / top_addst: 渡された文字列が記録した単語なら、決めた表示文字列を描く。
//!
//! ゲーム側の構造（53.17 Windows）
//!   markup_text_boxst: +0x00 word* の vector（begin/end/cap）, +0x30 幅, +0x34 最大行
//!   markup_text_wordst: +0x00 std::string, +0x28 px, +0x2c py, +0x30 flags（1 改行, 2 空行, 4 字下げ）

use std::collections::{HashMap, HashSet};

use crate::{encodings, utils};

const BOX_BEGIN: usize = 0x00;
const BOX_END: usize = 0x08;
const BOX_WIDTH: usize = 0x30;
const BOX_MAX_Y: usize = 0x34;
const WORD_COLOR: usize = 0x20;
const WORD_LINK: usize = 0x24; // リンク [LPAGE] の番号（-1 = リンクではない）。リンクの色は描くときに付く
const WORD_PX: usize = 0x28;
const WORD_PY: usize = 0x2c;
const WORD_FLAGS: usize = 0x30;

const TILE_PX: u32 = encodings::CURSES_FONT_WIDTH;

struct Word {
  bytes: Vec<u8>,
  own: String,
  display: Option<String>,
  /// 記録したときの通し番号。解放された単語の番地が別の単語に使い回されても、
  /// 古い記録を消すときに今の単語を巻き添えにしないための目印
  gen: u64,
}

/// 可変部分（{1} {2} ...）を含む文章の訳
struct Template {
  regex: regex::Regex,
  slots: Vec<String>,
  translation: String,
}

#[derive(Default)]
pub struct Paragraphs {
  dict: HashMap<String, String>,
  templates: Vec<Template>,
  words: HashMap<usize, Word>,
  boxes: HashMap<usize, Vec<(usize, u64)>>,
  gen: u64,
  reported: HashSet<String>,
}

#[derive(Debug, serde::Deserialize)]
struct Entry {
  text: String,
  translation: String,
}

#[static_init::dynamic]
pub static mut PARAGRAPHS: Paragraphs = {
  let mut ret = Paragraphs::default();
  let slot = regex::Regex::new(r"\{(\d+)\}").unwrap();
  let mut files = vec![utils::data_path("paragraph-dictionary.csv")];
  files.extend(utils::mod_translation_files("paragraphs.csv"));
  for file in files {
  utils::load_csv(file, |Entry { text, translation }| {
    if translation.is_empty() {
      return;
    }
    let text = normalize(&text);
    if !slot.is_match(&text) {
      ret.dict.insert(text, translation);
      return;
    }
    // {N} を「任意の文字列」にした正規表現を作る
    let mut pattern = String::from("^");
    let mut slots = Vec::new();
    let mut last = 0;
    for m in slot.captures_iter(&text) {
      let whole = m.get(0).unwrap();
      pattern.push_str(&regex::escape(&text[last..whole.start()]));
      pattern.push_str("(.+?)");
      slots.push(m[1].to_owned());
      last = whole.end();
    }
    pattern.push_str(&regex::escape(&text[last..]));
    pattern.push('$');
    match regex::Regex::new(&pattern) {
      Ok(regex) => ret.templates.push(Template { regex, slots, translation }),
      Err(err) => log::warn!("文章のテンプレートを読めません {text:?}: {err}"),
    }
  });
  }
  log::info!("文章の訳: {} 件 / テンプレート {} 件", ret.dict.len(), ret.templates.len());
  ret
};

fn read<T: Copy>(addr: usize) -> T {
  unsafe { (addr as *const T).read_unaligned() }
}

fn write<T>(addr: usize, value: T) {
  unsafe { (addr as *mut T).write_unaligned(value) }
}

/// 空白の連続を1つにまとめる（訳の照合用）
fn normalize(text: &str) -> String {
  text.split_whitespace().collect::<Vec<&str>>().join(" ")
}

pub fn word_count(box_: usize) -> usize {
  let begin: usize = read(box_ + BOX_BEGIN);
  let end: usize = read(box_ + BOX_END);
  if begin == 0 || end < begin {
    0
  } else {
    (end - begin) / 8
  }
}

fn word_at(box_: usize, i: usize) -> usize {
  let begin: usize = read(box_ + BOX_BEGIN);
  read(begin + i * 8)
}

/// ゲームに渡した文字列から作られるはずの単語。None は「中身は分からないが1語になる」
/// （[KEY:29] のようなキー名の指定。ゲームが w や a などの実際のキー名に置き換える）
pub type ExpectedWord = Option<String>;

/// ゲームに渡した単語の並びが、箱の何番目から始まるかを後ろから突き合わせて求める。
/// 全部そろえば Some(位置)、合わなければ None
fn locate(box_: usize, words: &[ExpectedWord], len: usize) -> Option<usize> {
  let mut i = len;
  let mut t = words.len();
  while i > 0 && t > 0 {
    let word = word_at(box_, i - 1);
    let bytes = raw::cxxstring_as_bytes(word);
    // 改行や段落の区切りだけの単語は中身が空
    if bytes.is_empty() {
      i -= 1;
      continue;
    }
    match &words[t - 1] {
      Some(text) if bytes != text.as_bytes() => return None,
      _ => {}
    }
    i -= 1;
    t -= 1;
  }
  if t == 0 {
    Some(i)
  } else {
    None
  }
}

pub fn is_closing_punct(ch: char) -> bool {
  "、。，．・：；？！」』）】〕〉》ー…‥ゃゅょっャュョッぁぃぅぇぉァィゥェォ".contains(ch)
}

/// 単語の中身が UTF-8 の日本語（こちらが入れた訳）なら、その文字列を返す
pub fn utf8_text(word: usize) -> Option<String> {
  let bytes = raw::cxxstring_as_bytes(word);
  if bytes.is_ascii() {
    return None;
  }
  std::str::from_utf8(bytes).ok().map(|s| s.to_owned())
}

/// 訳文をゲームに渡す形にする: [..] のトークンと英数字の並びはそのまま、日本語は1文字ずつ空白で区切る
fn split_for_game(text: &str) -> Vec<String> {
  let mut out: Vec<String> = Vec::new();
  let mut ascii = String::new();
  let mut chars = text.chars().peekable();
  let flush = |ascii: &mut String, out: &mut Vec<String>| {
    if !ascii.is_empty() {
      out.push(std::mem::take(ascii));
    }
  };
  while let Some(ch) = chars.next() {
    if ch == '[' {
      flush(&mut ascii, &mut out);
      let mut token = String::from("[");
      for c in chars.by_ref() {
        token.push(c);
        if c == ']' {
          break;
        }
      }
      out.push(token);
    } else if ch.is_whitespace() {
      flush(&mut ascii, &mut out);
    } else if ch.is_ascii() {
      ascii.push(ch);
    } else {
      flush(&mut ascii, &mut out);
      out.push(ch.to_string());
    }
  }
  flush(&mut ascii, &mut out);
  out
}

impl Paragraphs {
  /// markup_process_string の前に呼ぶ。訳があれば、ゲームに渡す文字列（UTF-8）と、
  /// そこから作られるはずの単語の一覧を返す
  pub fn prepare(&mut self, box_: usize, src: &[u8]) -> Option<(Vec<u8>, Vec<ExpectedWord>)> {
    let english = normalize(&encodings::bytes_to_string(src));
    log::debug!("paragraph piece box={box_:x}: {english:?}");
    let found = self.translate_only(&english);
    match found {
      Some(translation) => {
        let pieces = split_for_game(&translation);
        let words: Vec<ExpectedWord> = pieces
          .iter()
          .filter_map(|p| match p.as_str() {
            // [KEY:29] はゲームが実際のキー名（w など）に置き換えて1語にする
            p if p.starts_with("[KEY:") => Some(None),
            // [C:..] や [B] のような指定は、読み取られるだけで中身のある単語にはならない
            p if p.starts_with('[') => None,
            _ => Some(Some(p.to_owned())),
          })
          .collect();
        Some((pieces.join(" ").into_bytes(), words))
      }
      None => {
        if english.len() >= 40 && english.contains(' ') && self.reported.insert(english.clone()) {
          log::debug!("missing paragraph translation:\n{english:?}\n");
        }
        None
      }
    }
  }

  /// 文章の訳だけを引く（辞書 → テンプレート → 文）。検査用コマンドからも使う
  pub fn translate_only(&self, english: &str) -> Option<String> {
    let english = normalize(english);
    self
      .dict
      .get(&english)
      .cloned()
      .or_else(|| self.apply_template(&english))
      .or_else(|| crate::sentence::SENTENCES.translate_text(&english))
      // 文が1語だけの見出しなど、文の訳が届かないものは単語辞書を引く
      .or_else(|| crate::translator::lookup_plain(&english))
  }

  fn apply_template(&self, english: &str) -> Option<String> {
    for t in &self.templates {
      if let Some(caps) = t.regex.captures(english) {
        let mut out = t.translation.clone();
        for (i, slot) in t.slots.iter().enumerate() {
          let value = caps.get(i + 1).map(|m| m.as_str()).unwrap_or("");
          // 辞書にある語（季節、生き物など）は訳す。名前などはそのまま
          let value = crate::translator::lookup_term(value).unwrap_or_else(|| value.to_owned());
          out = out.replace(&format!("{{{slot}}}"), &value);
        }
        return Some(out);
      }
    }
    None
  }

  /// markup_process_string の後に呼ぶ。今回追加された単語を記録する。
  /// 渡した単語の一覧を実際の中身と後ろから突き合わせ、どこからが今回ぶんかを決める
  pub fn record(&mut self, box_: usize, words: &[ExpectedWord]) {
    let len = word_count(box_);
    let (start, only_ja) = match locate(box_, words, len) {
      Some(start) => (start, false),
      None => {
        // 突き合わせられないときは全体を見て、こちらが入れた日本語だけ拾う
        log::debug!("文章の単語の位置が合いません box={box_:x} len={len} 渡した数={}", words.len());
        (0, true)
      }
    };
    // 先頭から入れ直すなら、前の中身の記録は捨てる
    if start == 0 {
      self.forget(box_);
    }
    self.gen += 1;
    let gen = self.gen;
    let list = self.boxes.entry(box_).or_default();
    for i in start..len {
      let word = word_at(box_, i);
      let bytes = raw::cxxstring_as_bytes(word).to_vec();
      if bytes.is_empty() || (only_ja && bytes.is_ascii()) {
        continue;
      }
      let own = String::from_utf8_lossy(&bytes).into_owned();
      self.words.insert(word, Word { bytes, own, display: None, gen });
      list.push((word, gen));
    }
  }

  fn forget(&mut self, box_: usize) {
    if let Some(list) = self.boxes.remove(&box_) {
      for (word, gen) in list {
        // 番地が使い回されて今は別の単語になっているものは消さない
        if self.words.get(&word).map(|w| w.gen == gen).unwrap_or(false) {
          self.words.remove(&word);
        }
      }
    }
  }

  /// markup_format の後に呼ぶ。日本語を含む文章を画素幅で並べ直す
  pub fn relayout(&mut self, box_: usize) {
    if !self.boxes.contains_key(&box_) {
      return;
    }
    let len = word_count(box_);
    let width: i32 = read(box_ + BOX_WIDTH);
    if width <= 0 {
      return;
    }
    // 記録から外れた日本語の単語があれば拾い直す（外れたままだと素のバイトで描かれて文字化けする）
    self.gen += 1;
    let gen = self.gen;
    for i in 0..len {
      let word = word_at(box_, i);
      let known = self.words.get(&word).map(|w| w.bytes == raw::cxxstring_as_bytes(word)).unwrap_or(false);
      if known {
        continue;
      }
      if let Some(own) = utf8_text(word) {
        let bytes = raw::cxxstring_as_bytes(word).to_vec();
        self.words.insert(word, Word { bytes, own, display: None, gen });
        self.boxes.entry(box_).or_default().push((word, gen));
      }
    }
    let width_px = width as u32 * TILE_PX;

    let mut x_px: u32 = 0;
    let mut y: i32 = 0;
    let mut force_break = false;
    let mut max_y: i32 = 0;
    let mut prev_ascii = false;
    // 今の行でまとめている日本語の並び（先頭の単語、まとめた文字列、色とリンク番号）
    let mut run: Option<(usize, String, ([u8; 3], i32))> = None;

    fn close_run(words: &mut HashMap<usize, Word>, run: &mut Option<(usize, String, ([u8; 3], i32))>) {
      if let Some((head, text, _)) = run.take() {
        if let Some(w) = words.get_mut(&head) {
          w.display = Some(text);
        }
      }
    }

    for i in 0..len {
      let word = word_at(box_, i);
      let flags: u32 = read(word + WORD_FLAGS);
      if flags & 1 != 0 {
        force_break = true;
        continue;
      }
      if flags & 2 != 0 {
        // 段落の区切り: 改行して1行空ける（元の処理と同じく2行進む）
        close_run(&mut self.words, &mut run);
        x_px = 0;
        y += 2;
        force_break = false;
        continue;
      }
      if flags & 4 != 0 {
        close_run(&mut self.words, &mut run);
        y += 1;
        x_px = 4 * TILE_PX;
        force_break = false;
        continue;
      }

      let (text, is_ja) = match self.words.get(&word) {
        Some(w) => (w.own.clone(), w.own.chars().any(|c| !c.is_ascii())),
        None => (encodings::bytes_to_string(raw::cxxstring_as_bytes(word)), false),
      };
      if text.is_empty() {
        continue;
      }
      let color: ([u8; 3], i32) = (read(word + WORD_COLOR), read(word + WORD_LINK));
      let w_px = encodings::string_width_in_pixels(&text);
      // 英単語どうしの間だけ1マス空ける
      let gap = if !is_ja && prev_ascii && x_px > 0 { TILE_PX } else { 0 };
      let hang = is_ja && text.chars().next().map(is_closing_punct).unwrap_or(false);
      // 日本語の字は1.5マス幅で描くので、右端に1マス余裕を残す。行頭に来てはいけない記号だけ右端まで使う
      let limit = if hang { width_px } else if is_ja { width_px.saturating_sub(TILE_PX) } else { width_px };
      if (force_break && x_px > 0) || (x_px > 0 && x_px + gap + w_px > limit) {
        close_run(&mut self.words, &mut run);
        y += 1;
        x_px = 0;
      } else {
        x_px += gap;
      }
      force_break = false;

      let px = ((x_px + TILE_PX - 1) / TILE_PX) as i32;
      if is_ja {
        // 色やリンクが変わったら別の並びにする（並びは先頭の単語の色・リンクで描かれるため）
        if run.as_ref().map(|(_, _, c)| *c != color).unwrap_or(false) {
          close_run(&mut self.words, &mut run);
        }
        match run.as_mut() {
          Some((_, s, _)) => {
            s.push_str(&text);
            write::<i32>(word + WORD_PX, px);
            write::<i32>(word + WORD_PY, y);
            if let Some(w) = self.words.get_mut(&word) {
              w.display = Some(String::new());
            }
            x_px += w_px;
          }
          None => {
            write::<i32>(word + WORD_PX, px);
            write::<i32>(word + WORD_PY, y);
            run = Some((word, text.clone(), color));
            x_px = (px as u32) * TILE_PX + w_px;
          }
        }
        prev_ascii = false;
      } else {
        close_run(&mut self.words, &mut run);
        write::<i32>(word + WORD_PX, px);
        write::<i32>(word + WORD_PY, y);
        if let Some(w) = self.words.get_mut(&word) {
          w.display = None;
        }
        x_px = (px as u32) * TILE_PX + w_px;
        prev_ascii = true;
      }
      max_y = max_y.max(y);
    }
    close_run(&mut self.words, &mut run);
    write::<i32>(box_ + BOX_MAX_Y, max_y);
  }

  /// addst / top_addst から呼ぶ。記録した単語なら表示する文字列を返す
  pub fn display(&self, word: usize) -> Option<String> {
    let w = self.words.get(&word)?;
    if raw::cxxstring_as_bytes(word) != w.bytes.as_slice() {
      return None;
    }
    Some(w.display.clone().unwrap_or_else(|| w.own.clone()))
  }
}
