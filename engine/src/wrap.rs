//! ゲームが文字列を幅で折り返して行の一覧（std::string* の vector）にする処理の日本語化。
//!
//! ユニット画面の台詞などは、関数 WRAP_LINES(out, src, width) で行に分けてから1行ずつ addst で描く。
//! 英語の空白でしか折り返さないので、訳文（空白の無い日本語）をそのまま渡すと1行になってしまう。
//!
//! 1. WRAP_LINES: src に訳があれば、訳文を画素幅で折り返して行を決める。ゲームには
//!    「行ごとに幅いっぱいの仮の単語（x の並び）」を空白でつないだ文字列を渡し、同じ数の行を作らせる。
//!    作られた行の string を記録する。
//! 2. addst: 渡された string が記録した行なら、その行の日本語を描く。
//!
//! ゲーム側の構造（53.17 Windows）: out は std::string* の vector（begin/end/cap）。元の関数は out に行を追加する

use std::collections::HashMap;

use crate::{encodings, paragraph};

const TILE_PX: u32 = encodings::CURSES_FONT_WIDTH;

struct Line {
  bytes: Vec<u8>,
  text: String,
  data: usize,
}

#[derive(Default)]
pub struct WrappedLines {
  lines: HashMap<usize, Line>,
  // 行の一覧（out）ごとに、記録した行の string のアドレス
  owners: HashMap<usize, Vec<usize>>,
  // 文字列の中身のアドレス → string のアドレス（addcoloredst は char* で受け取るため）
  data: HashMap<usize, usize>,
  // 仮の行の中身 → 日本語（ゲームが行を写してから描く場合に使う）
  // （行の末尾4文字の通し番号で引く。ゲームが行の頭を削ったり足したりして写しても見つかるように）
  by_bytes: HashMap<Vec<u8>, String>,
}

#[static_init::dynamic]
pub static mut WRAPPED: WrappedLines = WrappedLines::default();

/// 日本語を画素幅で折り返す。行頭に来てはいけない記号は前の行の末尾に付ける
pub fn wrap_japanese(text: &str, width: i32) -> Vec<String> {
  // 日本語の字は1.5マス幅で描くので、右端に1マス余裕を残す
  let limit = ((width.max(2) - 1) as u32) * TILE_PX;
  let mut lines: Vec<String> = Vec::new();
  let mut cur = String::new();
  let mut cur_px = 0;
  for ch in text.chars() {
    let w = encodings::char_width_in_pixels(ch);
    if cur_px + w > limit && !cur.is_empty() && !paragraph::is_closing_punct(ch) {
      lines.push(std::mem::take(&mut cur));
      cur_px = 0;
    }
    cur.push(ch);
    cur_px += w;
  }
  if !cur.is_empty() {
    lines.push(cur);
  }
  lines
}

/// 行ごとに1語になる仮の文字列（width - 1 文字の語を空白でつなぐ。2語は1行に入らない）。
/// 語は 0xFF（CP437 で空白に見える文字）で埋め、末尾の4文字に通し番号を 0x80〜0xBF で入れる。
/// ゲームが行を別の string に写してから描いても、中身でどの行か分かるようにするため（会話の選択肢など）
pub fn placeholder(n: usize, width: i32) -> Vec<u8> {
  static SERIAL: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);
  let len = (width - 1).max(1) as usize;
  let mut out = Vec::new();
  for i in 0..n {
    if i > 0 {
      out.push(b' ');
    }
    let mut word = vec![0xffu8; len];
    if len >= 6 {
      let id = SERIAL.fetch_add(1, std::sync::atomic::Ordering::Relaxed) & 0xff_ffff;
      for k in 0..4 {
        word[len - 4 + k] = 0x80 | ((id >> (6 * (3 - k))) & 0x3f) as u8;
      }
    }
    out.extend_from_slice(&word);
  }
  out
}

/// 仮の行の中身か（0x80 以上の文字だけでできていて、末尾の通し番号の手前に 0xFF がある）。
/// ゲームが行の頭に空白などを足して写すことがあるので、先頭の文字は問わない
pub fn is_placeholder(bytes: &[u8]) -> bool {
  let t = trim_ascii(bytes);
  t.len() >= 6 && t[t.len() - 5] == 0xff && t.iter().all(|&b| b >= 0x80)
}

fn trim_ascii(bytes: &[u8]) -> &[u8] {
  let start = bytes.iter().position(|&b| b >= 0x80).unwrap_or(bytes.len());
  let end = bytes.iter().rposition(|&b| b >= 0x80).map(|i| i + 1).unwrap_or(start);
  &bytes[start..end.max(start)]
}

/// 仮の行の通し番号（末尾4文字）
fn serial_of(bytes: &[u8]) -> Vec<u8> {
  let t = trim_ascii(bytes);
  t[t.len().saturating_sub(4)..].to_vec()
}

fn read<T: Copy>(addr: usize) -> T {
  unsafe { (addr as *const T).read_unaligned() }
}

impl WrappedLines {
  /// 元の関数が out に追加した行（old_len 番目以降）に、日本語の行を対応させる
  pub fn record(&mut self, out: usize, old_len: usize, texts: &[String]) {
    // 空の一覧に作り直すときだけ古い記録を消す。続けて追加するとき（段落を2つ続けて折り返す画面など）は残す
    let mut owned = if old_len == 0 { Vec::new() } else { self.owners.remove(&out).unwrap_or_default() };
    if old_len == 0 {
      if let Some(old) = self.owners.remove(&out) {
        for addr in old {
          if let Some(line) = self.lines.remove(&addr) {
            self.data.remove(&line.data);
          }
        }
      }
    }
    let begin: usize = read(out);
    let end: usize = read(out + 8);
    if begin == 0 || end < begin {
      return;
    }
    let len = (end - begin) / 8;
    for (i, text) in (old_len..len).zip(texts.iter()) {
      let addr: usize = read(begin + i * 8);
      if addr == 0 {
        continue;
      }
      let slice = raw::cxxstring_as_bytes(addr);
      let data = slice.as_ptr() as usize;
      self.data.insert(data, addr);
      if is_placeholder(slice) {
        if self.by_bytes.len() > 20000 {
          self.by_bytes.clear();
        }
        self.by_bytes.insert(serial_of(slice), text.clone());
      }
      self.lines.insert(addr, Line { bytes: slice.to_vec(), text: text.clone(), data });
      owned.push(addr);
    }
    self.owners.insert(out, owned);
  }

  /// addst から呼ぶ。記録した行なら表示する日本語を返す
  pub fn display(&self, addr: usize) -> Option<String> {
    let bytes = raw::cxxstring_as_bytes(addr);
    if let Some(line) = self.lines.get(&addr) {
      if bytes == line.bytes.as_slice() {
        return Some(line.text.clone());
      }
    }
    // 写された行（中身が仮の行と同じ）
    if is_placeholder(bytes) {
      return self.by_bytes.get(&serial_of(bytes)).cloned();
    }
    None
  }
}

impl WrappedLines {
  /// addcoloredst から呼ぶ。文字列の中身のアドレスが記録した行のものなら日本語を返す
  pub fn display_cstr(&self, data: usize) -> Option<String> {
    if let Some(&addr) = self.data.get(&data) {
      return self.display(addr);
    }
    let bytes = unsafe { std::ffi::CStr::from_ptr(data as *const std::ffi::c_char) }.to_bytes();
    if is_placeholder(bytes) {
      return self.by_bytes.get(&serial_of(bytes)).cloned();
    }
    None
  }
}

/// ゲーム起動時に作られる説明文（ボタンのツールチップなど 600 件余り）は、日本語化のフックが付く前に
/// TOOLTIP_INIT が WRAP_LINES で行に分けて保存している。フックを付けた後に1回だけ、保存先の行の一覧を空にして
/// TOOLTIP_INIT を呼び直し、訳文で作り直させる。保存先は関数の中の「lea rcx, [rip+X]; …; call WRAP_LINES」の X
pub unsafe fn rewrap_static_tooltips() {
  let (Some(init), Some(wrap)) = (crate::offsets::FUNCTIONS.get("tooltip_init"), crate::offsets::FUNCTIONS.get("wrap_lines"))
  else {
    log::warn!("説明文の初期化関数が見つからないため、起動時の説明文は英語のままです");
    return;
  };
  let init = crate::utils::OFFSETS.get(init);
  let wrap = crate::utils::OFFSETS.get(wrap);
  let code = std::slice::from_raw_parts(init as *const u8, 0x10000);
  let mut vectors = Vec::new();
  let mut i = 0;
  while i + 7 < code.len() {
    // 関数の終わり（ret の後の int3 の詰め物）で止める
    if code[i] == 0xc3 && code.get(i + 1) == Some(&0xcc) && code.get(i + 2) == Some(&0xcc) {
      break;
    }
    if code[i..i + 3] == [0x48, 0x8d, 0x0d] {
      let disp = i32::from_le_bytes(code[i + 3..i + 7].try_into().unwrap());
      let target = (init as isize + i as isize + 7 + disp as isize) as usize;
      for j in i + 7..(i + 24).min(code.len() - 5) {
        if code[j] == 0xe8 {
          let rel = i32::from_le_bytes(code[j + 1..j + 5].try_into().unwrap());
          if (init as isize + j as isize + 5 + rel as isize) as usize == wrap {
            vectors.push(target);
          }
          break;
        }
      }
    }
    i += 1;
  }
  if vectors.is_empty() {
    log::warn!("説明文の保存先が見つかりません");
    return;
  }
  for v in &vectors {
    // end = begin（行の string は解放しない。数百件なので漏れても小さい）
    let begin = (*v as *const usize).read();
    ((*v + 8) as *mut usize).write(begin);
  }
  let f: extern "C" fn() = std::mem::transmute(init);
  f();
  log::info!("起動時の説明文 {} 件を訳文で作り直しました", vectors.len());
}

pub fn vector_len(out: usize) -> usize {
  let begin: usize = read(out);
  let end: usize = read(out + 8);
  if begin == 0 || end < begin {
    0
  } else {
    (end - begin) / 8
  }
}
