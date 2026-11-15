//! ゲームが自分で折り返して1行ずつ描く文章（性格の説明、ゲームの種類の説明など）を、行の並びで追う。
//!
//! 行は1行ずつ addst に来るので、1行だけでは訳せない。同じ呼び出し元から続けて来た行をつなぎ、
//! 訳せたら同じ行数に折り返して「段落」として覚える。次の描画からは、覚えた段落を行の順になぞって訳の行を返す。
//!
//! 行ごと（英語の1行 → 日本語の1行）に覚えると、1行目が同じで続きが違う文章（文化の説明は
//! 誰でも同じ行で始まる）で、1行目に別人の訳が出て、2行目以降が訳せなくなる。
//! そこで段落ごとに覚え、途中で食い違ったら、なぞってきた行ごと組み立て直しに回す。
//!
//! 流れには2つの状態がある。
//! - まだ折り返した文章を描くと分かっていない呼び出し元: 初めて見る行だけを積む（大半の UI はこちら）
//! - 折り返した文章を描くと分かった呼び出し元（armed）: 描画ごとに、すべての行を順に受け取る

use std::collections::{HashMap, HashSet};
use std::hash::{DefaultHasher, Hash, Hasher};

/// 未解決の行をためる上限
const MAX_OPEN: usize = 40;
/// 呼び出し元ごとに覚える段落の上限（超えたら覚え直す）
const MAX_KNOWN: usize = 400;
/// 試した並びを覚える上限（超えたら忘れて試し直す）
const MAX_SETTLED: usize = 20_000;
/// 「並びの終わりで試した」印（途中で試した印と分けるため）
const FINISH: u64 = 0x5bd1_e995_9e37_79b9;

struct Paragraph {
  en: Vec<String>,
  ja: Vec<String>,
}

#[derive(Default)]
pub(super) struct Flow {
  /// まだ組み立てられていない行（行のハッシュと英語）
  open: Vec<(u64, String)>,
  /// open の中身を表すハッシュ（同じ並びを二度試さないため）
  state: u64,
  /// 試し終えた並び
  settled: HashSet<u64>,
  /// なぞっている段落: (段落の番号, なぞり始めた行, 次に来るはずの行)
  follow: Option<(usize, usize, usize)>,
  /// 覚えた段落
  known: Vec<Paragraph>,
  /// 行のハッシュ → その行を含む段落と行番号（最近使ったものほど後ろ）
  index: HashMap<u64, Vec<(usize, usize)>>,
  /// この描画で出てきた段落の順
  seq: Vec<usize>,
  /// 前の描画で出てきた段落の順（同じ行で始まる段落が複数あるとき、前と同じ順のものを選ぶ）
  last_seq: Vec<usize>,
  /// 折り返した文章を描く呼び出し元と分かったか
  pub armed: bool,
  /// この描画で行が来たか
  pub touched: bool,
}

fn line_hash(s: &str) -> u64 {
  let mut hasher = DefaultHasher::new();
  s.hash(&mut hasher);
  hasher.finish()
}

fn mix(state: u64, h: u64) -> u64 {
  (state.rotate_left(7) ^ h).wrapping_mul(0x9e37_79b9_7f4a_7c15)
}

/// a の次に b が来たとき、折り返しの途中か。
/// 折り返された行は、最後の行以外が空白で終わる（"You can play a sequence of fortresses and "）。
/// ユニットの画面の性格の説明のように、行末の空白を削って渡す画面もある（"She often feels filled with joy, though she"）。
/// 行末が文の終わり（. ! ? :）でないか、次の行が小文字で始まれば、折り返しの途中とみなす
fn wrapped(a: &str, b: &str) -> bool {
  a.ends_with(' ')
    || !a.trim_end().ends_with(['.', '!', '?', ':'])
    || b.trim_start().starts_with(|c: char| c.is_ascii_lowercase())
}

fn ends_sentence(s: &str) -> bool {
  s.trim_end().ends_with(['.', '!', '?'])
}

/// 行をつなぐ。行末の空白が削られた行は、空白を補う
fn join(part: &[&str]) -> String {
  let mut joined = String::new();
  for l in part {
    if !joined.is_empty() && !joined.ends_with(' ') {
      joined.push(' ');
    }
    joined.push_str(l);
  }
  joined
}

/// 幅いっぱいで折り返された行の並びか。次の行の最初の語は、前の行に入らなかったはず。
/// 見出しと文のように、たまたま続けて描かれただけの行を文章とみなさないために使う
fn greedy(part: &[&str]) -> bool {
  let len = |l: &str| l.trim_end().chars().count();
  let max = part.iter().map(|l| len(l)).max().unwrap_or(0);
  part.windows(2).all(|w| {
    let first = w[1].trim_start().split(' ').next().unwrap_or("").chars().count();
    // 文末の後ろに空白を2つ置く文章があるので、2字ぶんの余裕を見る
    len(w[0]) + first + 3 > max
  })
}

impl Flow {
  pub fn ja(&self, p: usize, i: usize) -> &str {
    self.known[p].ja[i].as_str()
  }

  fn push_open(&mut self, h: u64, s: &str) {
    self.open.push((h, s.to_owned()));
    if self.open.len() > MAX_OPEN {
      self.open.remove(0);
      self.state = self.open.iter().fold(0, |state, (h, _)| mix(state, *h));
    } else {
      self.state = mix(self.state, h);
    }
  }

  fn clear_open(&mut self) {
    self.open.clear();
    self.state = 0;
  }

  /// まだ試していない並びなら true（同じ並びは二度試さない）
  fn untried(&mut self, key: u64) -> bool {
    if self.settled.len() > MAX_SETTLED {
      self.settled.clear();
    }
    self.settled.insert(key)
  }

  /// 段落 p の i 行目まで進んだ
  fn advance(&mut self, p: usize, from: usize, i: usize) {
    self.follow = (i + 1 < self.known[p].en.len()).then_some((p, from, i + 1));
  }

  /// この行を含む覚えた段落を探す。前の描画で同じ順に出てきた段落を優先し、無ければ最近使ったもの
  fn find(&self, h: u64, s: &str, expect: Option<usize>, ok: impl Fn(usize, usize) -> bool) -> Option<(usize, usize)> {
    let list = self.index.get(&h)?;
    let fits = |c: &(usize, usize)| self.known[c.0].en[c.1] == s && ok(c.0, c.1);
    list
      .iter()
      .copied()
      .find(|c| Some(c.0) == expect && fits(c))
      .or_else(|| list.iter().rev().copied().find(|c| fits(c)))
  }

  /// 使った段落を、同じ行を持つ候補の中でいちばん後ろへ回す
  fn touch(&mut self, h: u64, q: usize, j: usize) {
    if let Some(list) = self.index.get_mut(&h) {
      if list.last() != Some(&(q, j)) {
        list.retain(|c| *c != (q, j));
        list.push((q, j));
      }
    }
  }

  /// 初めて見る行を積む（折り返した文章を描くとまだ分かっていない呼び出し元）
  pub fn push_new(&mut self, caller: &str, s: &str) {
    self.push_open(line_hash(s), s);
    self.assemble(caller);
  }

  /// 行を1つ受け取る（折り返した文章を描くと分かった呼び出し元）。
  /// 覚えた段落の行なら (段落, 行) を返す。そうでなければ未解決の行に積んで、組み立て直しを試す
  pub fn feed(&mut self, caller: &str, s: &str) -> Option<(usize, usize)> {
    let h = line_hash(s);
    let hit = self.step(caller, h, s);
    if hit.is_none() {
      self.assemble(caller);
    }
    hit
  }

  fn step(&mut self, caller: &str, h: u64, s: &str) -> Option<(usize, usize)> {
    if let Some((p, from, i)) = self.follow {
      if self.known[p].en[i] == s {
        self.advance(p, from, i);
        return Some((p, i));
      }
      // 食い違った。ここまでの行が同じで、次がこの行になっている別の段落があれば、そちらへ移る
      let run = i - from;
      let switch =
        self.find(h, s, None, |q, j| q != p && j >= run && self.known[q].en[j - run..j] == self.known[p].en[from..i]);
      if let Some((q, j)) = switch {
        if let Some(last) = self.seq.last_mut() {
          *last = q;
        }
        self.touch(h, q, j);
        self.advance(q, j - run, j);
        return Some((q, j));
      }
      self.follow = None;
      // 覚えた段落の頭の行なら、前の段落は途中までしか描かれなかったものとして、新しくなぞる
      let prev_ends = !wrapped(&self.known[p].en[i - 1], s);
      if let Some((q, j)) = self.find(h, s, None, |_, j| j == 0 || prev_ends) {
        self.seq.push(q);
        self.touch(h, q, j);
        self.advance(q, j, j);
        return Some((q, j));
      }
      // どちらでもなければ、なぞってきた行を未解決に戻して、組み立て直しに回す
      self.seq.pop();
      let lines: Vec<String> = self.known[p].en[from..i].to_vec();
      self.clear_open();
      for l in &lines {
        self.push_open(line_hash(l), l);
      }
      self.push_open(h, s);
      return None;
    }

    // 前の行の続きでなければ、ためていた行の並びはここで終わり
    let fresh_start = self.open.last().map_or(true, |(_, last)| !wrapped(last, s));
    let pick = |me: &Self| me.find(h, s, me.last_seq.get(me.seq.len()).copied(), |_, j| j == 0 || fresh_start);
    if !self.open.is_empty() && (fresh_start || pick(self).is_some()) {
      self.finish(caller);
    }
    if let Some((q, j)) = pick(self) {
      self.clear_open();
      self.seq.push(q);
      self.touch(h, q, j);
      self.advance(q, j, j);
      return Some((q, j));
    }
    self.push_open(h, s);
    None
  }

  /// ためた行をつないで、辞書か文テンプレートで全部訳せたら、段落として覚える
  fn assemble(&mut self, caller: &str) {
    let state = self.state;
    if self.open.len() < 2 || !self.untried(state) {
      return;
    }
    let lines: Vec<&str> = self.open.iter().map(|(_, l)| l.as_str()).collect();
    let n = lines.len();
    // 文の終わりで終わる行が来たら、文テンプレートでも訳してみる（外見・性格の説明など、ゲームが作る文章）
    // 最後の行が短くても（価値観の段落の最後は "society." の1語だけ）つなぎ直せるように、長さはつないだ文で見る
    let ends = ends_sentence(lines[n - 1]);
    let mut prose = false;
    let mut result = None;
    // 1行だけのものは、ふだんの訳の手順ですでに試している
    for start in 0..n - 1 {
      let part = &lines[start..];
      // 空白で終わらない行が途中にあれば、別々に描かれた文（一覧の各行など）なのでつながない
      if part.windows(2).any(|w| !wrapped(w[0], w[1])) {
        continue;
      }
      let joined = join(part);
      let text = joined.trim();
      let mut found = super::lookup_term(text)
        .or_else(|| super::lookup_term(&part.iter().map(|l| l.trim()).collect::<Vec<_>>().join(" ")));
      if ends && text.len() >= 12 {
        prose = true;
        if found.is_none() && part[0].starts_with(|c: char| c.is_ascii_uppercase()) {
          found = crate::sentence::SENTENCES.translate_text(text).filter(|ja| super::fully_translated(ja));
        }
      }
      if let Some(ja) = found {
        result = Some((start, ja));
        break;
      }
    }
    // 文で終わる行の並びを描く呼び出し元は、以後、訳がキャッシュ済みの行も流れに入れる
    // （別の文章と同じ行があっても、行の並びで追えるようにするため）
    if prose {
      self.armed = true;
    }
    if let Some((start, ja)) = result {
      self.remember(caller, start, &ja, false);
    }
  }

  /// 行の並びが終わったとき（描画の終わり、文章の続きでない行、覚えた段落の始まり）に呼ぶ。
  /// 全部は訳せなかった文章を、文の単位で訳せるところだけ訳して覚える（訳せない文は英語のまま残す）
  fn finish(&mut self, caller: &str) {
    let key = self.state ^ FINISH;
    if !self.armed || self.open.len() < 2 || !self.untried(key) {
      return;
    }
    let lines: Vec<&str> = self.open.iter().map(|(_, l)| l.as_str()).collect();
    let n = lines.len();
    if !ends_sentence(lines[n - 1]) {
      return;
    }
    for start in 0..n - 1 {
      let part = &lines[start..];
      if !part[0].starts_with(|c: char| c.is_ascii_uppercase())
        || part.windows(2).any(|w| !wrapped(w[0], w[1]))
        || !greedy(part)
      {
        continue;
      }
      let joined = join(part);
      let text = joined.trim();
      let found = if text.len() >= 12 { crate::sentence::SENTENCES.translate_sentences(text) } else { None };
      if let Some(ja) = found {
        self.remember(caller, start, &ja, true);
      }
      return;
    }
  }

  /// open の start 行目から後ろを、訳 ja の段落として覚える
  fn remember(&mut self, caller: &str, start: usize, ja: &str, partial: bool) {
    let en: Vec<String> = self.open[start..].iter().map(|(_, l)| l.clone()).collect();
    let width = en.iter().map(|l| l.chars().count()).max().unwrap_or(1) as i32;
    let mut ja_lines = crate::wrap::wrap_mixed(ja, width + 1);
    if ja_lines.len() > en.len() {
      let rest = ja_lines.split_off(en.len() - 1).concat();
      ja_lines.push(rest);
    }
    ja_lines.resize(en.len(), String::new());
    if partial {
      log::info!("折り返された文章 {} 行を、訳せる文だけ訳して組み立て直しました @{caller}: {:?}", en.len(), en.concat());
    } else {
      log::info!("折り返された文章 {} 行を訳で組み立て直しました @{caller}: {:?}", en.len(), en.concat());
    }
    if self.known.len() >= MAX_KNOWN {
      self.known.clear();
      self.index.clear();
      self.seq.clear();
      self.last_seq.clear();
      self.follow = None;
    }
    // 同じ並びをすでに覚えていれば、訳だけ入れ替える
    let same = self
      .index
      .get(&line_hash(&en[0]))
      .and_then(|list| list.iter().copied().find(|&(q, j)| j == 0 && self.known[q].en == en));
    let id = match same {
      Some((q, _)) => {
        self.known[q].ja = ja_lines;
        q
      }
      None => {
        let id = self.known.len();
        for (i, l) in en.iter().enumerate() {
          self.index.entry(line_hash(l)).or_default().push((id, i));
        }
        self.known.push(Paragraph { en, ja: ja_lines });
        id
      }
    };
    self.seq.push(id);
    self.clear_open();
    self.armed = true;
  }

  /// 描画が1回終わった。行の並びをここで区切る
  pub fn end_pass(&mut self, caller: &str) {
    self.finish(caller);
    self.touched = false;
    self.follow = None;
    self.clear_open();
    self.last_seq = std::mem::take(&mut self.seq);
  }
}
