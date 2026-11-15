//! ゲームが読む `dfhooks.dll`。自分では何もせず、同じフォルダの `dfhooks_*.dll` を
//! すべて読み込んで、ゲームからの呼び出しをそのまま渡すだけの「橋渡し役」。
//!
//! なぜ要るか: ゲームは起動時に `dfhooks.dll` を**1つだけ**読む。DFHack はここに自前の
//! 橋渡し役を置くので、日本語化が同じ名前を名乗ると取り合いになる。日本語化も橋渡し役を
//! 持てば、どちらが先に入っても成り立つ。
//!
//! - 日本語化だけ … この DLL が `dfhooks_dfint_ja.dll` を読む
//! - あとから DFHack … DFHack が `dfhooks.dll` を自分のものに置き換えても、
//!   DFHack の橋渡し役が `dfhooks_dfint_ja.dll` を読む
//! - DFHack が先で、あとからファイルを置いた … この DLL が `dfhooks_dfhack.ini` を読んで DFHack を起こす
//!
//! 仕様は DFHack の橋渡し役（https://github.com/DFHack/dfhooks 、MIT）に合わせてある。
//! 探すのはカレントディレクトリ（ゲームフォルダ）の `dfhooks_` で始まる `.dll` と `.ini`。
//! `.ini` は1行目を DLL のパスとして読む。`dfhooks.dll`（自分）は `dfhooks_` で始まらないので対象外。

use std::{
  ffi::{c_void, CString, OsStr},
  fs,
  io::Write,
  os::windows::ffi::{OsStrExt, OsStringExt},
  path::{Path, PathBuf},
  sync::OnceLock,
};

use winapi::{
  shared::minwindef::HMODULE,
  um::libloaderapi::{
    GetModuleFileNameW, GetModuleHandleExW, GetProcAddress, LoadLibraryExW, GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, LOAD_WITH_ALTERED_SEARCH_PATH,
  },
};

/// この DLL が置いてあるフォルダ（= ゲームフォルダ）。
///
/// 以前はカレントディレクトリを見ていたが、起動のしかたによってはゲームフォルダとは
/// 限らない。その場合 `dfhooks_*.dll` が1つも見つからず、日本語化が黙って効かないまま
/// 英語で立ち上がっていた（記録も書けないので何も残らない）。
fn base_dir() -> &'static Path {
  static BASE: OnceLock<PathBuf> = OnceLock::new();
  BASE.get_or_init(|| {
    let mut handle = std::ptr::null_mut();
    let ok = unsafe {
      GetModuleHandleExW(
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        base_dir as *const u16,
        &mut handle,
      )
    };
    if ok != 0 && !handle.is_null() {
      let mut buf = [0u16; 32768];
      let len = unsafe { GetModuleFileNameW(handle, buf.as_mut_ptr(), buf.len() as u32) } as usize;
      if len > 0 && len < buf.len() {
        let path = PathBuf::from(std::ffi::OsString::from_wide(&buf[..len]));
        if let Some(dir) = path.parent() {
          return dir.to_path_buf();
        }
      }
    }
    PathBuf::from(".")
  })
}

type VoidFn = unsafe extern "C" fn();
type EventFn = unsafe extern "C" fn(*mut c_void) -> bool;
type KeyFn = unsafe extern "C" fn(i32) -> bool;

struct Lib {
  name: String,
  /// 大きいものから先に呼ぶ（DFHack の橋渡し役の実装に合わせる）。`dfhooks_priority` が
  /// 無ければ 0。DFHack 本体は 100
  priority: i32,
  init: Option<VoidFn>,
  shutdown: Option<VoidFn>,
  update: Option<VoidFn>,
  prerender: Option<VoidFn>,
  sdl_loop: Option<VoidFn>,
  sdl_event: Option<EventFn>,
  ncurses_key: Option<KeyFn>,
}

// Send/Sync: 読み込んだ後は変えないので、ゲームの各スレッドから読むだけ
unsafe impl Send for Lib {}
unsafe impl Sync for Lib {}

static LIBS: OnceLock<Vec<Lib>> = OnceLock::new();

fn libs() -> &'static Vec<Lib> {
  LIBS.get_or_init(load_all)
}

/// 調べもの用の記録。書けなくても黙って続ける
fn log(line: &str) {
  for dir in [base_dir().join("dfint-data"), base_dir().to_path_buf()] {
    let path = dir.join("dfhooks-chain.log");
    if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(&path) {
      let _ = writeln!(f, "{line}");
      return;
    }
  }
}

fn wide(path: &Path) -> Vec<u16> {
  OsStr::new(path).encode_wide().chain(std::iter::once(0)).collect()
}

fn sym(handle: HMODULE, name: &str) -> Option<*const c_void> {
  let c = CString::new(name).ok()?;
  let p = unsafe { GetProcAddress(handle, c.as_ptr()) };
  if p.is_null() {
    None
  } else {
    Some(p as *const c_void)
  }
}

/// 関数の記号を関数ポインタとして取り出す。無ければ None
unsafe fn fn_sym<T: Copy>(handle: HMODULE, name: &str) -> Option<T> {
  assert_eq!(std::mem::size_of::<T>(), std::mem::size_of::<*const c_void>());
  sym(handle, name).map(|p| std::mem::transmute_copy(&p))
}

/// カレントディレクトリから読み込む DLL のパスを集める。
/// `dfhooks_*.dll` はそのまま、`dfhooks_*.ini` は1行目に書かれたパス
fn candidates() -> Vec<PathBuf> {
  let mut out: Vec<PathBuf> = Vec::new();
  let entries = match fs::read_dir(base_dir()) {
    Ok(entries) => entries,
    Err(err) => {
      log(&format!("フォルダを読めません: {err}"));
      return out;
    }
  };
  let mut files: Vec<PathBuf> = entries.flatten().map(|e| e.path()).collect();
  files.sort();
  for path in files {
    let stem = match path.file_stem().and_then(|s| s.to_str()) {
      Some(stem) => stem.to_lowercase(),
      None => continue,
    };
    if !stem.starts_with("dfhooks_") && !stem.starts_with("libdfhooks_") {
      continue;
    }
    match path.extension().and_then(|e| e.to_str()).map(|e| e.to_lowercase()).as_deref() {
      Some("dll") => out.push(path),
      Some("ini") => match fs::read_to_string(&path) {
        Ok(text) => match text.lines().map(str::trim).find(|l| !l.is_empty()) {
          Some(target) => out.push(PathBuf::from(target)),
          None => log(&format!("{} が空です", path.display())),
        },
        Err(err) => log(&format!("{} を読めません: {err}", path.display())),
      },
      _ => {}
    }
  }
  // 同じ DLL を .dll と .ini の両方から拾ったときに二重に読まないようにする
  let mut seen: Vec<String> = Vec::new();
  out.retain(|path| {
    let key = fs::canonicalize(path).unwrap_or_else(|_| path.clone()).to_string_lossy().to_lowercase();
    if seen.contains(&key) {
      log(&format!("{} は読み込み済みなので飛ばします", path.display()));
      false
    } else {
      seen.push(key);
      true
    }
  });
  out
}

/// DFHack 本体の橋渡し役（`…\DFHack\dfhooks.dll`）を探す。
///
/// DFHack は読み込んだ直後に `dfhooks_preinit(std::filesystem::path)` を呼んでもらう前提で、
/// そこで自分の置き場所を知る。この引数は C++ の型なので、ほかの言語からは安全に渡せない
/// （呼ばないと「symbols.xml が開けない」と出て DFHack が止まる）。
/// なので DFHack が居るときは**自分で読み込まず、DFHack の橋渡し役に丸ごと任せる**。
/// 向こうは今のフォルダを見て DFHack 本体も `dfhooks_dfint_ja.dll` も読んでくれる。
fn dfhack_chainloader() -> Option<PathBuf> {
  let entries = fs::read_dir(base_dir()).ok()?;
  for entry in entries.flatten() {
    let path = entry.path();
    let stem = path.file_stem()?.to_str()?.to_lowercase();
    if !stem.starts_with("dfhooks_") || path.extension().and_then(|e| e.to_str()) != Some("ini") {
      continue;
    }
    let text = fs::read_to_string(&path).ok()?;
    let target = PathBuf::from(text.lines().map(str::trim).find(|l| !l.is_empty())?);
    // …\DFHack\hack\dfhooks_dfhack.dll → …\DFHack\dfhooks.dll
    let loader = target.parent()?.parent()?.join("dfhooks.dll");
    if loader.is_file() {
      return Some(loader);
    }
  }
  None
}

/// install.ps1 が「この dfhooks.dll は dfint-ja のものか」を判別するための目印。
/// 文字列として実行ファイルに残るように、記録にも書き出す
const MARKER: &str = "dfint-ja chainloader";

fn load_all() -> Vec<Lib> {
  log(MARKER);
  let mut libs: Vec<Lib> = Vec::new();
  let paths = match dfhack_chainloader() {
    Some(loader) => {
      log(&format!("DFHack の橋渡し役に任せます: {}", loader.display()));
      vec![loader]
    }
    None => candidates(),
  };
  for path in paths {
    let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    // DFHack 本体のように、自分と同じフォルダの DLL に頼っているものがある。
    // LOAD_WITH_ALTERED_SEARCH_PATH を付けると、その DLL のあるフォルダを基点に探してくれる
    // （付けないと「依存先が見つからない」= エラー 126 で読み込めない）。絶対パスが要る
    let full = fs::canonicalize(&path).unwrap_or_else(|_| path.clone());
    let handle = unsafe { LoadLibraryExW(wide(&full).as_ptr(), std::ptr::null_mut(), LOAD_WITH_ALTERED_SEARCH_PATH) };
    if handle.is_null() {
      log(&format!("{name} を読み込めません（エラー {}）", unsafe {
        winapi::um::errhandlingapi::GetLastError()
      }));
      continue;
    }
    // dfhooks_priority は関数ではなく i32 の変数。無ければ 0
    let priority = sym(handle, "dfhooks_priority").map(|p| unsafe { *(p as *const i32) }).unwrap_or(0);
    // DFHack の橋渡し役は読み込んだ直後に dfhooks_preinit(std::filesystem::path) を呼ぶが、
    // これは C の形をしておらず（C++ の型を渡す）、別の言語から安全に呼べない。
    // 呼ばないと困る DLL があれば、ここの記録で分かるようにしておく
    if sym(handle, "dfhooks_preinit").is_some() {
      log(&format!("{name} は dfhooks_preinit を持っていますが、呼んでいません"));
    }
    libs.push(Lib {
      name: name.clone(),
      priority,
      init: unsafe { fn_sym(handle, "dfhooks_init") },
      shutdown: unsafe { fn_sym(handle, "dfhooks_shutdown") },
      update: unsafe { fn_sym(handle, "dfhooks_update") },
      prerender: unsafe { fn_sym(handle, "dfhooks_prerender") },
      sdl_loop: unsafe { fn_sym(handle, "dfhooks_sdl_loop") },
      sdl_event: unsafe { fn_sym(handle, "dfhooks_sdl_event") },
      ncurses_key: unsafe { fn_sym(handle, "dfhooks_ncurses_key") },
    });
    log(&format!("{name} を読み込みました（priority {priority}）"));
  }
  // 大きいものから先に呼ぶ
  libs.sort_by(|a, b| b.priority.cmp(&a.priority));
  log(&format!("読み込み順: {}", libs.iter().map(|l| l.name.as_str()).collect::<Vec<_>>().join(" → ")));
  libs
}

#[no_mangle]
pub extern "C" fn dfhooks_init() {
  for lib in libs() {
    if let Some(f) = lib.init {
      unsafe { f() };
    }
  }
}

#[no_mangle]
pub extern "C" fn dfhooks_shutdown() {
  // 片付けは読み込んだ順の逆
  for lib in libs().iter().rev() {
    if let Some(f) = lib.shutdown {
      unsafe { f() };
    }
  }
}

#[no_mangle]
pub extern "C" fn dfhooks_update() {
  for lib in libs() {
    if let Some(f) = lib.update {
      unsafe { f() };
    }
  }
}

#[no_mangle]
pub extern "C" fn dfhooks_prerender() {
  for lib in libs() {
    if let Some(f) = lib.prerender {
      unsafe { f() };
    }
  }
}

#[no_mangle]
pub extern "C" fn dfhooks_sdl_loop() {
  for lib in libs() {
    if let Some(f) = lib.sdl_loop {
      unsafe { f() };
    }
  }
}

/// 「その操作は自分が処理した」と返した DLL があれば、そこで止めて後ろには渡さない
#[no_mangle]
pub extern "C" fn dfhooks_sdl_event(event: *mut c_void) -> bool {
  for lib in libs() {
    if let Some(f) = lib.sdl_event {
      if unsafe { f(event) } {
        return true;
      }
    }
  }
  false
}

#[no_mangle]
pub extern "C" fn dfhooks_ncurses_key(key: i32) -> bool {
  for lib in libs() {
    if let Some(f) = lib.ncurses_key {
      if unsafe { f(key) } {
        return true;
      }
    }
  }
  false
}
