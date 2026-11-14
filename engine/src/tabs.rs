//! 入植の準備画面（入念に旅の準備をする）のタブの見出しだけは、文字列を描く関数（addst 系）を通らない。
//! 1文字ずつ `init` の「文字コード → タイル番号」の表を引いて、テクスチャのタイルとして描いている（add_tile）。
//! そのままではフックから文字列が見えないので、ここでタイル番号から文字を戻し、続けて描かれた1語ぶんを
//! まとめて訳し、自前のフォントで描き直す（ゲームには空白のタイルを渡して元の英字を消す）。

use std::collections::HashMap;

use crate::{df, offsets, screen, translator, utils};

#[static_init::dynamic]
pub static mut TABS: Tabs = Tabs::default();

#[derive(Default)]
pub struct Tabs {
  glyphs: Option<Glyphs>,
  run: Option<Run>,
}

/// init の中の「文字コード → タイル番号」の表（通常・強調）を逆に引けるようにしたもの
struct Glyphs {
  /// タイル番号 → (文字, 表の番号)
  chars: HashMap<u32, (u8, usize)>,
  min: u32,
  max: u32,
  /// 表ごとの空白のタイル番号
  space: [u32; 2],
}

/// 続けて描かれた1語
struct Run {
  y: i32,
  x0: i32,
  next_x: i32,
  text: String,
  bt: String,
  fg: df::common::Color,
  bg: df::common::Color,
}

const TABLES: [&str; 2] = ["init.texpos", "init.texpos_selected"];

impl Glyphs {
  fn build() -> Option<Self> {
    let init = *df::globals::INIT;
    if init == 0 {
      return None;
    }
    let mut chars = HashMap::new();
    let mut space = [0u32; 2];
    let (mut min, mut max) = (u32::MAX, 0u32);
    for (table, name) in TABLES.iter().enumerate() {
      let offset = *offsets::FIELDS.get(*name)?;
      if offset == 0 {
        return None;
      }
      let base = init + offset;
      // テクスチャが読み込まれる前は表が 0 のままなので、次の描画でやり直す
      let blank: u32 = unsafe { *((base + (b' ' as usize) * 4) as *const u32) };
      if blank == 0 {
        return None;
      }
      space[table] = blank;
      for code in 0x20u32..0x7f {
        let id: u32 = unsafe { *((base + (code as usize) * 4) as *const u32) };
        if id == 0 {
          continue;
        }
        chars.entry(id).or_insert((code as u8, table));
        min = min.min(id);
        max = max.max(id);
      }
    }
    if chars.len() < 90 {
      return None;
    }
    log::debug!("タブの見出し用の文字のタイルを {} 個読みました（{min}〜{max}）", chars.len());
    Some(Self { chars, min, max, space })
  }
}

impl Tabs {
  /// 画面の作り直し（表示設定の変更など）でタイル番号が変わるので、表を読み直させる
  pub fn reset(&mut self) {
    self.glyphs = None;
    self.run = None;
  }

  /// add_tile から呼ぶ。文字のタイルなら、代わりに描かせる空白のタイル番号を返す
  pub fn on_tile(&mut self, gps: usize, tile: u32) -> Option<u32> {
    if self.glyphs.is_none() {
      self.glyphs = Glyphs::build();
    }
    let found = match self.glyphs.as_ref() {
      Some(glyphs) if tile >= glyphs.min && tile <= glyphs.max => {
        glyphs.chars.get(&tile).map(|&(ch, table)| (ch, glyphs.space[table]))
      }
      _ => None,
    };
    // 文字でないタイルが来たら、そこで1語が終わる
    let Some((ch, space)) = found else {
      self.flush();
      return None;
    };
    let coord = df::gps::read_coord(gps);
    let continued = matches!(&self.run, Some(run) if run.y == coord.y && run.next_x == coord.x);
    if !continued {
      self.flush();
      let (fg, bg) = df::gps::read_colors(gps);
      self.run = Some(Run {
        y: coord.y,
        x0: coord.x,
        next_x: coord.x,
        text: String::new(),
        bt: utils::backtrace(),
        fg,
        bg,
      });
    }
    if let Some(run) = self.run.as_mut() {
      run.text.push(ch as char);
      run.next_x = coord.x + 1;
    }
    Some(space)
  }

  /// たまっている1語を訳して描く。訳が無ければ英語のまま自前のフォントで描く（消したままにしないため）
  pub fn flush(&mut self) {
    let Some(run) = self.run.take() else {
      return;
    };
    if run.text.trim().is_empty() {
      return;
    }
    let translated = {
      let mut translator = translator::TRANSLATOR.write();
      translator.translate("add_tile", &run.text, &run.bt).0.to_owned()
    };
    // 英語と同じ場所の中ほどに置く
    let cells = (run.next_x - run.x0).max(1);
    let width: i32 = translated
      .chars()
      .map(|ch| if ch.is_ascii() { screen::CANVAS_FONT_WIDTH } else { screen::CANVAS_FONT_WIDTH * 2 })
      .sum();
    let mut text = screen::Text::new((&translated, 0));
    text.data = text.data.with_fg_color(run.fg).with_bg_color(run.bg);
    text.coord = df::common::Coord {
      x: run.x0 * screen::CANVAS_FONT_WIDTH + (cells * screen::CANVAS_FONT_WIDTH - width) / 2,
      // 1文字が2行ぶんの高さで描かれるので、半行ぶん下げて真ん中に合わせる
      y: run.y * screen::CANVAS_FONT_HEIGHT + screen::CANVAS_FONT_HEIGHT / 2,
    };
    screen::SCREEN.write().add_text(text);
  }
}
