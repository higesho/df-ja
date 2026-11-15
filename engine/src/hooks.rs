use anyhow::Result;
use raw::{delete_cxxstring, new_cxxstring_n_chars};
use retour::static_detour;

use super::{df, encodings, offsets, paragraph, screen, tabs, translator, utils, wrap};

use r#macro::hook;

pub unsafe fn attach_all() -> Result<()> {
  attach_addst()?;
  attach_top_addst()?;
  attach_addst_flag()?;
  attach_gps_allocate()?;
  attach_update_all()?;
  attach_update_tile()?;
  attach_draw_horizontal_nineslice()?;
  attach_draw_nineslice()?;
  attach_markup_process_string()?;
  attach_markup_format()?;
  attach_addcoloredst()?;
  attach_wrap_lines()?;
  attach_add_tile()?;

  Ok(())
}

pub unsafe fn enable_all() -> Result<()> {
  enable_addst()?;
  enable_top_addst()?;
  enable_addst_flag()?;
  enable_gps_allocate()?;
  enable_update_all()?;
  enable_update_tile()?;
  enable_draw_horizontal_nineslice()?;
  enable_draw_nineslice()?;
  enable_markup_process_string()?;
  enable_markup_format()?;
  enable_addcoloredst()?;
  enable_wrap_lines()?;
  enable_add_tile()?;

  Ok(())
}

pub unsafe fn disable_all() -> Result<()> {
  disable_addst()?;
  disable_top_addst()?;
  disable_addst_flag()?;
  disable_gps_allocate()?;
  disable_update_all()?;
  disable_update_tile()?;
  disable_draw_horizontal_nineslice()?;
  disable_draw_nineslice()?;
  disable_markup_process_string()?;
  disable_markup_format()?;
  disable_addcoloredst()?;
  disable_wrap_lines()?;
  disable_add_tile()?;

  Ok(())
}

/// 文章の単語なら、決めておいた表示文字列を描いて幅を返す
fn draw_paragraph_word(gps: usize, string_address: usize, top: bool) -> Option<usize> {
  let text = match paragraph::PARAGRAPHS.read().display(string_address) {
    Some(text) => text,
    None => wrap::WRAPPED.read().display(string_address)?,
  };
  if text.is_empty() {
    return Some(0);
  }
  let text = screen::Text::new((&text, 0)).by_gps(gps);
  Some(if top {
    screen::SCREEN_TOP.write().add_text(text)
  } else {
    screen::SCREEN.write().add_text(text)
  })
}

#[hook]
fn markup_process_string(box_: usize, src: usize) {
  let old_len = paragraph::word_count(box_);
  let replaced = paragraph::PARAGRAPHS.write().prepare(box_, old_len, raw::cxxstring_as_bytes(src));
  match replaced {
    Some(bytes) => {
      let new_src = raw::new_cxxstring_from_bytes(&bytes);
      unsafe { original!(box_, new_src) };
      delete_cxxstring(new_src);
      paragraph::PARAGRAPHS.write().record(box_, old_len);
    }
    None => unsafe { original!(box_, src) },
  }
}

#[hook]
fn markup_format(box_: usize, width: i32) {
  unsafe { original!(box_, width) };
  paragraph::PARAGRAPHS.write().relayout(box_);
}

/// addcoloredst の英文の色を訳文に移す。最も多い色を地の色とし、ほかの色の語は辞書の訳が訳文にあればその色にする
fn colored_segments(en: &[u8], colors: &[u8], ja: &str) -> Vec<(String, u8)> {
  let mut count = std::collections::HashMap::new();
  for (b, c) in en.iter().zip(colors) {
    if *b != b' ' {
      *count.entry(*c).or_insert(0) += 1;
    }
  }
  let base = count.into_iter().max_by_key(|(_, n)| *n).map(|(c, _)| c).unwrap_or(colors[0]);
  // 地の色と違う色の語のまとまり
  let mut marks: Vec<(usize, usize, u8)> = Vec::new();
  let mut i = 0;
  while i < en.len() {
    if colors[i] == base || en[i] == b' ' {
      i += 1;
      continue;
    }
    let c = colors[i];
    let s = i;
    while i < en.len() && colors[i] == c {
      i += 1;
    }
    let word = encodings::bytes_to_string(&en[s..i]);
    let word = word.trim_matches(|ch: char| !ch.is_alphanumeric());
    if word.is_empty() {
      continue;
    }
    if let Some(tr) = translator::lookup_term(word) {
      if let Some(pos) = ja.find(tr.as_str()) {
        marks.push((pos, pos + tr.len(), c));
      }
    }
  }
  marks.sort();
  let mut out = Vec::new();
  let mut last = 0;
  for (s, e, c) in marks {
    if s < last {
      continue;
    }
    if s > last {
      out.push((ja[last..s].to_owned(), base));
    }
    out.push((ja[s..e].to_owned(), c));
    last = e;
  }
  if last < ja.len() {
    out.push((ja[last..].to_owned(), base));
  }
  out
}

/// 文字列を幅で折り返して行の一覧にする関数（ユニット画面の台詞など）。訳があれば日本語で折り返す（wrap.rs）
#[hook]
fn wrap_lines(out: usize, src: usize, width: i32) {
  if width <= 1 {
    unsafe { original!(out, src, width) };
    return;
  }
  let bt = utils::backtrace();
  let string = encodings::read_raw_string(src);
  let translated = {
    let mut tr = translator::TRANSLATOR.write();
    tr.translate("wrap_lines", &string, &bt).0.to_owned()
  };
  // 色の指定などのトークンを含む文は、元の処理に任せる
  if translated == string || translated.is_ascii() || translated.contains('[') {
    unsafe { original!(out, src, width) };
    return;
  }
  let lines = wrap::wrap_japanese(&translated, width);
  let old_len = wrap::vector_len(out);
  let fake = raw::new_cxxstring_from_bytes(&wrap::placeholder(lines.len(), width));
  unsafe { original!(out, fake, width) };
  delete_cxxstring(fake);
  wrap::WRAPPED.write().record(out, old_len, &lines);
}

/// graphicst::addcoloredst(str, colorstr): 1文字ごとに色を変えて描く（ユニット画面の性格・思考の行など）。
/// 訳せたら、先頭の文字の色で訳文を描き、元の関数には同じ幅の空白を渡してカーソルを進める
#[hook]
fn addcoloredst(gps: usize, str_address: usize, color_address: usize) {
  let bytes = unsafe { std::ffi::CStr::from_ptr(str_address as *const std::ffi::c_char) }.to_bytes();
  if bytes.is_empty() || color_address == 0 {
    unsafe { original!(gps, str_address, color_address) };
    return;
  }
  // 折り返しで作った日本語の行（wrap.rs）
  let wrapped = wrap::WRAPPED.read().display_cstr(str_address);
  let bt = utils::backtrace();
  let string = encodings::bytes_to_string(bytes);
  let (translated, shift) = if let Some(text) = wrapped {
    (text, 0)
  } else {
    let mut tr = translator::TRANSLATOR.write();
    let (t, s) = tr.translate("addcoloredst", &string, &bt);
    (t.to_owned(), s)
  };
  if translated == string {
    unsafe { original!(gps, str_address, color_address) };
    return;
  }
  // 英文で色の違う語（感情の語など）を、訳文の中の同じ語の訳に同じ色で付ける
  let colors_en = unsafe { std::slice::from_raw_parts(color_address as *const u8, bytes.len()) };
  let segments = colored_segments(bytes, colors_en, &translated);
  let color = segments.first().map(|s| s.1).unwrap_or(colors_en[0]);
  let start = df::gps::read_coord(gps);
  let mut x_px: i32 = 0;
  for (seg, c) in &segments {
    // 元の関数と同じく、色のバイト（下位3ビット 前景、次の3ビット 背景、6ビット目 明るさ）を gps に設定する
    unsafe {
      *((gps + 0x8c) as *mut u8) = c & 7;
      *((gps + 0x8d) as *mut u8) = (c >> 3) & 7;
      *((gps + 0x8e) as *mut u8) = (c >> 6) & 1;
      *((gps + 0x8f) as *mut u8) = 1;
    }
    let mut text = screen::Text::new((seg.as_str(), shift)).by_gps(gps);
    text.coord.x = start.x * screen::CANVAS_FONT_WIDTH + x_px;
    x_px += screen::SCREEN.write().add_text_px(text) as i32;
  }
  let width = ((x_px + screen::CANVAS_FONT_WIDTH - 1) / screen::CANVAS_FONT_WIDTH).max(0) as usize;
  let mut spaces = vec![b' '; width];
  spaces.push(0);
  let mut colors = vec![color; width];
  colors.push(0);
  unsafe { original!(gps, spaces.as_ptr() as usize, colors.as_ptr() as usize) };
}

/// ゲームは幅 space タイルの枠の中に文字を寄せて描く（ボタンの見出しは中央寄せ）。
/// 枠の幅は英語の文字数で決まっているので、訳を同じ左端から描くと中央からずれる。
/// 訳の幅に合わせて描き始めの位置をずらす（画素）
fn justify_shift(gps: usize, bt: &str, just: u8, space: i32, en: &str, text_px: u32) -> i32 {
  // addst 自身の寄せ（space が 0 より大きいとき）
  if space > 0 {
    let slack = space * screen::CANVAS_FONT_WIDTH - text_px as i32;
    if slack > 0 {
      match just {
        JUSTIFY_CENTER => return slack / 2,
        JUSTIFY_RIGHT => return slack,
        _ => {}
      }
    }
    return 0;
  }
  // ボタンの見出しなどは、ゲームが枠の幅と英語の文字数から描き始めを決めてから addst を呼ぶ。
  // そういう呼び出し元（no-translate-callers.txt に "center" と書いたもの）では、
  // 英語の中心に訳の中心を合わせる
  let caller = bt.split('/').next().unwrap_or("");
  if !crate::config::CONFIG.settings.center_callers.contains(caller) {
    // 中央寄せの見出しを見つけるための記録。ふだん（Warn）は集めない
    if !log::log_enabled!(log::Level::Debug) {
      return 0;
    }
    // 中央寄せの見出しを見つけるための記録。
    // 中央寄せの呼び出し元は「描き始め + 英語の幅の半分」（＝枠の中心）が文字列によらず一定になる。
    // 左に揃える呼び出し元は「描き始め」のほうが一定になる。ログを集めて見分ける（tools/center_scan.py）
    let coord = df::gps::read_coord(gps);
    let en_tiles = encodings::string_width_in_pixels(en) as i32 / screen::CANVAS_FONT_WIDTH;
    // 毎フレーム呼ばれるので、同じ組み合わせは1回だけ記録する
    static SEEN: std::sync::OnceLock<std::sync::Mutex<std::collections::HashSet<u64>>> = std::sync::OnceLock::new();
    let seen = SEEN.get_or_init(|| std::sync::Mutex::new(std::collections::HashSet::new()));
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    std::hash::Hash::hash(&(caller, coord.x, en_tiles), &mut hasher);
    let key = std::hash::Hasher::finish(&hasher);
    if seen.lock().map(|mut s| s.insert(key)).unwrap_or(false) {
      log::debug!("centerscan {caller} x={} y={} en={en_tiles} mid={}", coord.x, coord.y, coord.x * 2 + en_tiles);
    }
    return 0;
  }
  (encodings::string_width_in_pixels(en) as i32 - text_px as i32) / 2
}

/// 枠の幅が英語の文字数で決まっている箇所（交易画面の品物の一覧など）では、
/// 訳が長いと隣の列に重なってしまう。no-translate-callers.txt に "clamp" と書いた
/// 呼び出し元では、英語と同じ枠に収まるところまで訳を切り詰めて「…」を付ける。
///
/// 枠の幅は「英語の文字数 × 1マスの幅」。ゲームは自分でも長い名前を "..." で切っているので、
/// 切られた英語が来たときもその幅に合わせることになる
fn clamp_to_english(caller: &str, en: &str, ja: &str) -> Option<String> {
  if !crate::config::CONFIG.settings.clamp_callers.contains(caller) {
    return None;
  }
  let limit = en.chars().count() as u32 * screen::CANVAS_FONT_WIDTH as u32;
  if encodings::string_width_in_pixels(ja) <= limit {
    return None;
  }
  let ellipsis = encodings::char_width_in_pixels('…');
  let mut out = String::new();
  let mut width = 0;
  for ch in ja.chars() {
    let w = encodings::char_width_in_pixels(ch);
    if width + w + ellipsis > limit {
      break;
    }
    out.push(ch);
    width += w;
  }
  out.push('…');
  Some(out)
}

/// 訳を横にずらして描いたとき、ゲームが背景（空白）を描く位置もタイル単位で合わせる。
///
/// ゲームは addst に渡された文字列のぶんだけ背景を塗る。訳だけをずらすと、元の位置に背景が残って
/// タイトルの副題のように**黒い帯**になる。枠の幅が英語の文字数で決まっている中央寄せの
/// 呼び出し元（"center"）でだけ、描き始めの列を一時的にずらす
fn background_shift_tiles(bt: &str, space: i32, extra: i32) -> i32 {
  if space > 0 || extra == 0 {
    return 0;
  }
  let caller = bt.split('/').next().unwrap_or("");
  if !crate::config::CONFIG.settings.center_callers.contains(caller) {
    return 0;
  }
  extra / screen::CANVAS_FONT_WIDTH
}

const JUSTIFY_CENTER: u8 = 1;
const JUSTIFY_RIGHT: u8 = 2;

#[hook]
fn addst(gps: usize, string_address: usize, just: u8, space: i32) {
  if let Some(width) = draw_paragraph_word(gps, string_address, false) {
    let dummy_ptr = new_cxxstring_n_chars(width, ' ' as u8);
    unsafe { original!(gps, dummy_ptr, just, space) };
    delete_cxxstring(dummy_ptr);
    return;
  }
  let bt = utils::backtrace();
  let string = encodings::read_raw_string(string_address);

  let (text, tiles) = {
    let mut translator = translator::TRANSLATOR.write();
    let (content, shift) = translator.translate("addst", &string, &bt);
    let caller = bt.split('/').next().unwrap_or("");
    let clamped = clamp_to_english(caller, &string, content);
    let content: &str = clamped.as_deref().unwrap_or(content);
    let extra = justify_shift(gps, &bt, just, space, &string, encodings::string_width_in_pixels(content));
    (
      screen::Text::new((content, shift + extra)).by_gps(gps),
      background_shift_tiles(&bt, space, extra),
    )
  };
  let width = screen::SCREEN.write().add_text(text);

  if tiles != 0 {
    let x = df::gps::read_coord(gps).x;
    df::gps::write_x(gps, x + tiles);
  }
  let dummy_ptr = new_cxxstring_n_chars(width, ' ' as u8);
  unsafe { original!(gps, dummy_ptr, just, space) };
  delete_cxxstring(dummy_ptr);
  if tiles != 0 {
    // ゲームは描いたぶん描き始めを進めるので、進んだ先からずらしたぶんを引いて戻す
    let x = df::gps::read_coord(gps).x;
    df::gps::write_x(gps, x - tiles);
  }
}

#[hook]
fn addst_flag(gps: usize, string_address: usize, just: u8, space: i32, sflag: u32) {
  if let Some(width) = draw_paragraph_word(gps, string_address, false) {
    let dummy_ptr = new_cxxstring_n_chars(width, ' ' as u8);
    unsafe { original!(gps, dummy_ptr, just, space, sflag) };
    delete_cxxstring(dummy_ptr);
    return;
  }
  let bt = utils::backtrace();
  let string = encodings::read_raw_string(string_address);

  let text = {
    let mut translator = translator::TRANSLATOR.write();
    let (content, shift) = translator.translate("addst_flag", &string, &bt);
    let caller = bt.split('/').next().unwrap_or("");
    let clamped = clamp_to_english(caller, &string, content);
    let content: &str = clamped.as_deref().unwrap_or(content);
    let extra = justify_shift(gps, &bt, just, space, &string, encodings::string_width_in_pixels(content));
    screen::Text::new((content, shift + extra)).by_gps(gps).with_sflag(sflag)
  };
  let width = screen::SCREEN.write().add_text(text);

  let dummy_ptr = new_cxxstring_n_chars(width, ' ' as u8);
  unsafe { original!(gps, dummy_ptr, just, space, sflag) };
  delete_cxxstring(dummy_ptr);
}

#[hook]
fn top_addst(gps: usize, string_address: usize, just: u8, space: i32) {
  if let Some(width) = draw_paragraph_word(gps, string_address, true) {
    let dummy_ptr = new_cxxstring_n_chars(width, ' ' as u8);
    unsafe { original!(gps, dummy_ptr, just, space) };
    delete_cxxstring(dummy_ptr);
    return;
  }
  let bt = utils::backtrace();
  let string = encodings::read_raw_string(string_address);

  let text = {
    let mut translator = translator::TRANSLATOR.write();
    let (content, shift) = translator.translate("top_addst", &string, &bt);
    let caller = bt.split('/').next().unwrap_or("");
    let clamped = clamp_to_english(caller, &string, content);
    let content: &str = clamped.as_deref().unwrap_or(content);
    let extra = justify_shift(gps, &bt, just, space, &string, encodings::string_width_in_pixels(content));
    screen::Text::new((content, shift + extra)).by_gps(gps)
  };
  let width = screen::SCREEN_TOP.write().add_text(text);

  let dummy_ptr = new_cxxstring_n_chars(width, ' ' as u8);
  unsafe { original!(gps, dummy_ptr, just, space) };
  delete_cxxstring(dummy_ptr);
}

/// graphicst::add_tile(texpos, ...): タイル1枚を描く。入植の準備画面のタブの見出しだけは
/// 文字列ではなく1文字ずつこの関数で描かれるので、文字のタイルを空白に差し替えて訳を描く（tabs.rs）
#[hook]
fn add_tile(gps: usize, texpos: u32, a3: u32, a4: u32, width: u32, height: u32, color: u8) {
  let texpos = tabs::TABS.write().on_tile(gps, texpos).unwrap_or(texpos);
  unsafe { original!(gps, texpos, a3, a4, width, height, color) };
}

#[hook]
fn draw_nineslice(texpos: usize, sy: i32, sx: i32, ey: i32, ex: i32, flag: u8) {
  unsafe { original!(texpos, sy, sx, ey, ex, flag) };
  if flag & 1 == 1 {
    let cover = screen::Cover::new(sx, sy, ex, ey);
    screen::SCREEN.write().add_cover(cover);
  }
}

#[hook]
fn draw_horizontal_nineslice(texpos: usize, sy: i32, sx: i32, ey: i32, ex: i32, flag: u8) {
  unsafe { original!(texpos, sy, sx, ey, ex, flag) };
  if flag & 1 == 1 {
    let cover = screen::Cover::new(sx, sy, ex, ey);
    screen::SCREEN.write().add_cover(cover);
  }
}

#[hook]
fn gps_allocate(renderer: usize, x: i32, y: i32, screen_x: u32, screen_y: u32, tile_dim_x: u32, tile_dim_y: u32) {
  // graphicst::resize is inlined in Windows, hook gps_allocate instead
  unsafe { original!(renderer, x, y, screen_x, screen_y, tile_dim_x, tile_dim_y) };
  // ここが毎フレームのように呼ばれる環境があり、画面のちらつきの元になっていた。
  // 回数を残しておくと、報告をもらったときに切り分けられる
  {
    use std::sync::atomic::{AtomicU64, Ordering::Relaxed};
    static N: AtomicU64 = AtomicU64::new(0);
    let n = N.fetch_add(1, Relaxed) + 1;
    if n <= 5 || n % 100 == 0 {
      log::debug!("画面の取り直し（gps_allocate）{n}回目: {x}x{y} タイル");
    }
  }
  tabs::TABS.write().reset();
  screen::SCREEN.write().resize(x, y);
  screen::SCREEN_TOP.write().resize(x, y);
}

/// 文字の層をこの描画の回でもう描いたか。
///
/// 以前は update_tile で「右下のタイル」が描かれたときに便乗して描いていた。
/// ゲームは変化したタイルしか描き直さないことがあり、右下が描かれない回では
/// 文字だけが丸ごと消える。環境によっては半分近くの回でそれが起きて画面がちらついた。
/// いまは update_all の終わり（全タイルを描き終えた後）で必ず描き、
/// 右下のタイルのほうが先に来たときはそちらで描いて二重描きを避ける。
static SCREEN_DRAWN: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

fn render_screen(renderer: usize) {
  if SCREEN_DRAWN.swap(true, std::sync::atomic::Ordering::Relaxed) {
    return;
  }
  tabs::TABS.write().flush();
  screen::SCREEN.write().render(renderer);
  screen::SCREEN.write().clear();
}

#[hook]
fn update_all(renderer: usize) {
  SCREEN_DRAWN.store(false, std::sync::atomic::Ordering::Relaxed);
  unsafe { original!(renderer) };
  // DFHack はゲームの起動中に読み込まれるので、描画が始まってから割り込みを付ける
  crate::dfhack::try_attach();
  static REWRAPPED: std::sync::Once = std::sync::Once::new();
  REWRAPPED.call_once(|| unsafe { wrap::rewrap_static_tooltips() });

  render_screen(renderer);

  if df::gps::top_in_use(*df::globals::GPS) {
    screen::SCREEN_TOP.write().render(renderer);
    screen::SCREEN_TOP.write().clear();
  }
}

#[hook]
fn update_tile(renderer: usize, x: i32, y: i32) {
  unsafe { original!(renderer, x, y) };
  let dim = df::gps::borrow_dim(*df::globals::GPS);

  // 右下のタイルまで描けたら、そこで文字の層も描く（update_all を通らない描き方への備え）
  if x == dim.x - 1 && y == dim.y - 1 {
    render_screen(renderer);
  }
}
