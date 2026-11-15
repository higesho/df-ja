//! ゲームの画面に書かれるはずだった元の文字（英語）の控え。
//!
//! 文字はすべて自前の字で描き、ゲームには同じ幅の空白を渡している。そのためゲームの画面の控え
//! （gps の screen）には空白しか残らない。DFHack には、画面の文字を読んで自分の位置を決める部品がある
//! （ユニット画面の Mood 表示は "Overview" の見出しを探して、その下に出る）。空白しか読めないと
//! 見出しを見つけられず、既定の位置（画面の外れ）に出てしまう。
//!
//! そこで、元の文字を位置ごとに控えておき、DFHack が画面を読む関数（Screen::readTile）に
//! 割り込んで、空白の代わりに返す（dfhack.rs）。
//!
//! 控えは画面の組み立て直し1回ぶん。次の組み立て直しで最初の文字が描かれたときに捨てる。
//! DFHack が読むのは、組み立て直しの終わり（重ねて描く部品）か、次の組み立て直しまでの間
//! （位置を決め直す処理）なので、読まれるときには1回ぶんが揃っている。

use crate::encodings;

/// 控える範囲（タイル）。4K の画面でも横 480・縦 180 タイルに収まる
const W: usize = 512;
const H: usize = 256;

#[static_init::dynamic]
pub static mut SHADOW: Shadow = Shadow::default();

#[derive(Default)]
pub struct Shadow {
  cells: Vec<u8>,
  /// 控えのあるいちばん下の行（捨てるときに、使った行だけを消すため）
  rows: usize,
  /// 前の組み立て直しの控えが残っている（次に控えるときに捨てる）
  stale: bool,
}

impl Shadow {
  /// 画面の組み立て直しが1回終わった
  pub fn end_pass(&mut self) {
    // 前の回の終わりから何も控えていなければ、画面から文字が無くなったということ。残さない
    if self.stale && self.rows > 0 {
      self.cells[..self.rows * W].fill(0);
      self.rows = 0;
    }
    self.stale = true;
  }

  fn prepare(&mut self) {
    if self.cells.is_empty() {
      self.cells = vec![0; W * H];
    }
    if self.stale {
      self.cells[..self.rows * W].fill(0);
      self.rows = 0;
      self.stale = false;
    }
  }

  /// (x, y) から右へ、元の文字列を控える
  pub fn record(&mut self, x: i32, y: i32, text: &str) {
    self.prepare();
    if y < 0 || y as usize >= H {
      return;
    }
    let row = y as usize * W;
    let mut x = x;
    for ch in text.chars() {
      if x >= 0 && (x as usize) < W {
        // ゲームの文字コード（CP437）に戻す。戻せない字は、文字があることだけ分かるようにする
        let byte = if ch.is_ascii() { ch as u8 } else { encodings::utf8_char_to_ch437_byte(ch).unwrap_or(b'?') };
        self.cells[row + x as usize] = byte;
      }
      x += 1;
    }
    self.rows = self.rows.max(y as usize + 1);
  }

  /// 枠の下地などで塗りつぶされた範囲の控えを消す（下に描かれていた文字は、もう画面に無い）
  pub fn clear_rect(&mut self, x1: i32, y1: i32, x2: i32, y2: i32) {
    if self.cells.is_empty() || self.stale {
      return;
    }
    let (x1, x2) = (x1.max(0) as usize, (x2.min(W as i32 - 1)).max(-1));
    let (y1, y2) = (y1.max(0) as usize, (y2.min(self.rows as i32 - 1)).max(-1));
    if x2 < 0 || y2 < 0 {
      return;
    }
    let (x2, y2) = (x2 as usize, y2 as usize);
    if x1 > x2 || y1 > y2 {
      return;
    }
    for y in y1..=y2 {
      self.cells[y * W + x1..=y * W + x2].fill(0);
    }
  }

  /// (x, y) に控えた文字。無ければ None
  pub fn get(&self, x: i32, y: i32) -> Option<u8> {
    if self.cells.is_empty() || x < 0 || y < 0 || x as usize >= W || y as usize >= self.rows {
      return None;
    }
    match self.cells[y as usize * W + x as usize] {
      0 => None,
      byte => Some(byte),
    }
  }
}
