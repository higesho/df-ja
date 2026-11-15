pub mod constants;
pub mod cover;
pub mod data;
pub mod text;

pub use constants::CANVAS_FONT_HEIGHT;
pub use constants::CANVAS_FONT_WIDTH;
pub use cover::Cover;
use data::Data;
pub use text::Text;

use crate::{
  df,
  font::{CJK_FONT_SIZE, FONT},
};
use sdl2::{pixels::PixelFormatEnum, rect::Rect, surface::Surface, sys as sdl};
use std::{collections::HashMap, mem, ptr};

#[static_init::dynamic]
pub static mut SCREEN: Screen = Screen::new();

#[static_init::dynamic]
pub static mut SCREEN_TOP: Screen = Screen::new();

/// ゲームがこの回に画面を組み立て直したか。
///
/// ゲームは「描画フレーム」（G_FPS_CAP）ごとに画面を出すが、画面を組み立て直す
/// （文字を描く関数を呼ぶ）のは、処理（FPS_CAP）が1回以上進んだ回だけ。
/// 組み立て直しの無い回は、前の回の内容をそのまま出さないと文字だけが消える。
/// 逆に、組み立て直したのに何も描かれなかった層は、本当に空になったので消す。
/// 描画のフックが1つでも呼ばれたら「組み立て直した」とみなす
static FRESH: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

pub fn mark_fresh() {
  FRESH.store(true, std::sync::atomic::Ordering::Relaxed);
}

pub fn take_fresh() -> bool {
  FRESH.swap(false, std::sync::atomic::Ordering::Relaxed)
}

/// 画面に描いた内容を表す数。同じならテクスチャを作り直さなくてよい
fn mix(hash: &mut u64, value: u64) {
  *hash = (*hash ^ value).wrapping_mul(0x100000001b3);
}

/// 描いた範囲（x, y, 幅, 高さ）を広げる
fn grow(area: &mut Option<(i32, i32, i32, i32)>, x: i32, y: i32, w: i32, h: i32) {
  if w <= 0 || h <= 0 {
    return;
  }
  *area = Some(match *area {
    None => (x, y, w, h),
    Some((ax, ay, aw, ah)) => {
      let (x0, y0) = (ax.min(x), ay.min(y));
      let (x1, y1) = ((ax + aw).max(x + w), (ay + ah).max(y + h));
      (x0, y0, x1 - x0, y1 - y0)
    }
  });
}

fn union(a: Option<(i32, i32, i32, i32)>, b: Option<(i32, i32, i32, i32)>) -> Option<(i32, i32, i32, i32)> {
  let mut out = a;
  if let Some((x, y, w, h)) = b {
    grow(&mut out, x, y, w, h);
  }
  out
}

#[derive(Default)]
pub struct Screen {
  dimension: df::common::Dimension<i32>,
  canvas_ptr: usize,
  // cache: hash(data) => (surface_ptr, width)
  prev: HashMap<u64, (usize, u32)>,
  next: HashMap<u64, (usize, u32)>,
  // 画布を載せておくテクスチャ。毎フレーム作り直すと非常に重いので使い回す
  texture_ptr: usize,
  texture_renderer: usize,
  // この回に描いた内容と、テクスチャに載せてある内容
  frame_hash: u64,
  uploaded_hash: u64,
  // この回に描いた範囲と、テクスチャに載せてある範囲（画素）。変わったところだけ送るために使う
  frame_rect: Option<(i32, i32, i32, i32)>,
  uploaded_rect: Option<(i32, i32, i32, i32)>,
  // 画布を消すのは「次に描き始めるとき」まで待つ。
  // ゲームが文字を描き直さない回があり、その場で消すと文字だけ1フレーム消えてちらつく
  needs_clear: bool,
  drew_this_frame: bool,
}

impl Screen {
  pub fn new() -> Self {
    Self {
      dimension: Default::default(),
      canvas_ptr: Default::default(),
      prev: Default::default(),
      next: Default::default(),
      texture_ptr: Default::default(),
      texture_renderer: Default::default(),
      frame_hash: 0,
      uploaded_hash: u64::MAX,
      frame_rect: None,
      uploaded_rect: None,
      needs_clear: false,
      drew_this_frame: false,
    }
  }

  fn drop_texture(&mut self) {
    if self.texture_ptr != 0 {
      unsafe { sdl::SDL_DestroyTexture(self.texture_ptr as *mut sdl::SDL_Texture) };
      self.texture_ptr = 0;
      self.texture_renderer = 0;
      self.uploaded_hash = u64::MAX;
      self.uploaded_rect = None;
    }
  }

  pub fn resize(&mut self, x: i32, y: i32) {
    // ゲームは同じ大きさのまま画面を取り直すことがある。そのたびに画布を作り直すと、
    // その回だけ中身が空になり、文字だけが丸ごと消えて画面がちらつく。
    // 大きさが変わっていなければ今の画布をそのまま使う
    if self.canvas_ptr != 0 && self.dimension.x == x && self.dimension.y == y {
      return;
    }

    self.dimension = df::common::Dimension { x, y };
    self.drop_texture();

    if self.canvas_ptr != 0 {
      let canvas = unsafe { Surface::from_ll(self.canvas_ptr as *mut sdl::SDL_Surface) };
      mem::drop(canvas);
    }

    let canvas = Surface::new(
      (x * CANVAS_FONT_WIDTH) as u32,
      (y * CANVAS_FONT_HEIGHT) as u32,
      PixelFormatEnum::RGBA32,
    )
    .unwrap();
    self.canvas_ptr = canvas.raw() as usize;
    mem::forget(canvas);
    self.needs_clear = false;
    self.drew_this_frame = false;
    self.frame_hash = 0;
    self.frame_rect = None;
    self.uploaded_hash = u64::MAX;
  }

  /// 描く前の後始末。ゲームが画面を組み立て直した回（fresh）なのに、この層には
  /// 何も描かれなかったなら、この層は空になった（ツールチップが消えたなど）。
  /// 前の内容を残すと消えたはずの文字が居残るので、ここで消す
  pub fn settle(&mut self, fresh: bool) {
    if !fresh || self.drew_this_frame || self.canvas_ptr == 0 {
      return;
    }
    if !self.needs_clear && self.frame_hash == 0 {
      return; // もう空
    }
    self.needs_clear = false;
    self.frame_hash = 0;
    self.frame_rect = None;
    unsafe {
      let canvas = self.canvas_ptr as *mut sdl::SDL_Surface;
      sdl::SDL_FillRect(canvas, ptr::null(), 0);
    }
    for (_, (ptr, _)) in self.prev.drain() {
      unsafe { sdl::SDL_FreeSurface(ptr as *mut sdl::SDL_Surface) };
    }
  }

  /// この回で最初に描くときに、前の回の内容を消す
  fn begin_frame(&mut self) {
    self.drew_this_frame = true;
    if !self.needs_clear {
      return;
    }
    self.needs_clear = false;
    self.frame_hash = 0;
    self.frame_rect = None;
    unsafe {
      let canvas = self.canvas_ptr as *mut sdl::SDL_Surface;
      sdl::SDL_FillRect(canvas, ptr::null(), 0);
    }
  }

  pub fn add_text(&mut self, text: Text) -> usize {
    (self.add_text_px(text) as f32 / CANVAS_FONT_WIDTH as f32).ceil() as usize
  }

  /// 文字を描き、描いた幅（画素）を返す
  pub fn add_text_px(&mut self, text: Text) -> u32 {
    let Text {
      coord: df::common::Coord { x, y },
      data,
      horizontal_shift,
      render,
    } = text;

    if !render {
      return 0;
    }
    self.begin_frame();

    // render text or get from cache
    let key = data.key();
    let (surface_ptr, width) = match self.prev.get(&key) {
      Some((ptr, width)) => (ptr.to_owned() as *mut sdl::SDL_Surface, width.to_owned()),
      None => {
        let Data { str, fg, bg } = data;
        let bg = if bg.r == 0 && bg.g == 0 && bg.b == 0 || bg.r == 160 && bg.g == 160 && bg.b == 160 {
          None
        } else {
          Some(bg)
        };

        let mut font = FONT.write();
        let (ptr, width) = font.render(str, fg, bg);
        let ptr = ptr as *mut sdl::SDL_Surface;
        mem::drop(font);

        (ptr, width)
      }
    };
    self.next.insert(key, (surface_ptr as usize, width));

    // この回に何をどこへ描いたかを足していく。前の回と同じならテクスチャはそのまま使える
    mix(&mut self.frame_hash, key);
    mix(&mut self.frame_hash, (x + horizontal_shift) as i64 as u64);
    mix(&mut self.frame_hash, y as i64 as u64);
    mix(&mut self.frame_hash, width as u64);
    grow(&mut self.frame_rect, x + horizontal_shift, y, width as i32, CJK_FONT_SIZE as i32);

    // render on canvas
    unsafe {
      let mut srcrect = Rect::new(0, 0, width, CJK_FONT_SIZE);
      let mut dstrect = Rect::new(x + horizontal_shift, y, width, CJK_FONT_SIZE);
      let canvas = self.canvas_ptr as *mut sdl::SDL_Surface;
      sdl::SDL_UpperBlit(surface_ptr, srcrect.raw_mut(), canvas, dstrect.raw_mut());
    };

    width
  }

  pub fn clear(&mut self) {
    // この回に何も描かれなかったなら、前の回の内容をそのまま残す。
    // ゲームは変化していない画面を描き直さないことがあり、消してしまうと文字だけ消える
    if !self.drew_this_frame {
      return;
    }
    self.drew_this_frame = false;
    self.needs_clear = true;

    for (k, (ptr, _)) in self.prev.iter() {
      if !self.next.contains_key(k) {
        unsafe { sdl::SDL_FreeSurface(ptr.to_owned() as *mut sdl::SDL_Surface) };
      }
    }

    self.prev = mem::take(&mut self.next);
  }

  pub fn add_cover(&mut self, cover: Cover) {
    let Cover {
      coord: df::common::Coord { x, y },
      dimension: df::common::Dimension { x: w, y: h },
    } = cover;

    self.begin_frame();
    mix(&mut self.frame_hash, 0x0c0_0000_0000 ^ (x as i64 as u64));
    mix(&mut self.frame_hash, y as i64 as u64);
    mix(&mut self.frame_hash, w as u64);
    mix(&mut self.frame_hash, h as u64);
    grow(&mut self.frame_rect, x, y, w as i32, h as i32);

    let canvas = self.canvas_ptr as *mut sdl::SDL_Surface;
    let cover_rect = Rect::new(x, y, w, h);
    unsafe { sdl::SDL_FillRect(canvas, cover_rect.raw(), 0) };
  }

  pub fn render(&mut self, renderer: usize) {
    if self.canvas_ptr == 0 {
      return;
    }

    let srcrect = Rect::new(
      0,
      0,
      (self.dimension.x * CANVAS_FONT_WIDTH) as u32,
      (self.dimension.y * CANVAS_FONT_HEIGHT) as u32,
    );

    let df::renderer::ScreenInfo {
      dispx_z,
      dispy_z,
      origin_x,
      origin_y,
    } = df::renderer::borrow_screen_info(renderer);
    let dstrect = Rect::new(
      *origin_x as i32,
      *origin_y as i32,
      (self.dimension.x * dispx_z) as u32,
      (self.dimension.y * dispy_z) as u32,
    );

    unsafe {
      let canvas = self.canvas_ptr as *mut sdl::SDL_Surface;
      let sdl_renderer = df::renderer::read_sdl_renderer(renderer);

      // 描画先が入れ替わったら、そのテクスチャはもう使えない
      if self.texture_ptr != 0 && self.texture_renderer != sdl_renderer as usize {
        self.drop_texture();
      }

      if self.texture_ptr == 0 {
        let format = (*(*canvas).format).format;
        let texture = sdl::SDL_CreateTexture(
          sdl_renderer,
          format,
          sdl::SDL_TextureAccess::SDL_TEXTUREACCESS_STATIC as i32,
          (*canvas).w,
          (*canvas).h,
        );
        if texture.is_null() {
          return;
        }
        // 文字の層は下の絵に重ねるので、透明度を活かす（作り直さない代わりにここで指定する）
        sdl::SDL_SetTextureBlendMode(texture, sdl::SDL_BlendMode::SDL_BLENDMODE_BLEND);
        sdl::SDL_SetTextureScaleMode(texture, sdl::SDL_ScaleMode::SDL_ScaleModeLinear);
        self.texture_ptr = texture as usize;
        self.texture_renderer = sdl_renderer as usize;
        self.uploaded_hash = u64::MAX;
        // 作り立てのテクスチャの中身は決まっていないので、最初の1回は全体を送る
        self.uploaded_rect = Some((0, 0, (*canvas).w, (*canvas).h));
      }

      let texture = self.texture_ptr as *mut sdl::SDL_Texture;
      // 前の回と同じ内容なら載せ直さない。静止している画面ではこれで毎フレームの転送が消える
      if self.frame_hash != self.uploaded_hash {
        // 画布は毎回まっさらにしてから描き直すので、前の回と今回に描いた範囲の外は
        // どちらも透明のまま。その和集合だけ送れば足りる（画面全体を送ると 20MB 以上になる）
        if let Some((x, y, w, h)) = union(self.frame_rect, self.uploaded_rect) {
          let (cw, ch) = ((*canvas).w, (*canvas).h);
          let x0 = x.clamp(0, cw);
          let y0 = y.clamp(0, ch);
          let x1 = (x + w).clamp(0, cw);
          let y1 = (y + h).clamp(0, ch);
          if x1 > x0 && y1 > y0 {
            let bpp = (*(*canvas).format).BytesPerPixel as i32;
            let pitch = (*canvas).pitch;
            let pixels = ((*canvas).pixels as *const u8).offset((y0 * pitch + x0 * bpp) as isize);
            let rect = Rect::new(x0, y0, (x1 - x0) as u32, (y1 - y0) as u32);
            sdl::SDL_UpdateTexture(texture, rect.raw(), pixels as *const std::ffi::c_void, pitch);
          }
        }
        self.uploaded_hash = self.frame_hash;
        self.uploaded_rect = self.frame_rect;
      }
      sdl::SDL_RenderCopy(sdl_renderer, texture, srcrect.raw(), dstrect.raw());
    }
  }
}
