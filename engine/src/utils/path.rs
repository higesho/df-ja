use std::path::{Path, PathBuf};

const DATA_DIR: &str = "dfint-data";

/// この DLL が置いてあるフォルダ。無ければ空（= カレントディレクトリ基準のまま）
#[cfg(all(target_os = "windows", not(feature = "offline")))]
fn module_dir() -> Option<PathBuf> {
  use std::os::windows::ffi::OsStringExt;
  use winapi::um::libloaderapi::{GetModuleFileNameW, GetModuleHandleExW, GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT};

  let mut handle = std::ptr::null_mut();
  let ok = unsafe {
    GetModuleHandleExW(
      GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
      module_dir as *const u16,
      &mut handle,
    )
  };
  if ok == 0 || handle.is_null() {
    return None;
  }
  let mut buf = [0u16; 32768];
  let len = unsafe { GetModuleFileNameW(handle, buf.as_mut_ptr(), buf.len() as u32) } as usize;
  if len == 0 || len >= buf.len() {
    return None;
  }
  // 連鎖読み込みが canonicalize したパスで読むため `\\?\L:\…` の形で返ることがある。
  // この形は `..` を解かないので、ワークショップの検索（`../../workshop/…`）が通らなくなる。
  // 先頭の印を外して普通のパスに戻す
  let text = std::ffi::OsString::from_wide(&buf[..len]);
  let text = text.to_string_lossy();
  let path = PathBuf::from(text.strip_prefix(r"\\?\").unwrap_or(&text).to_string());
  path.parent().map(|p| p.to_path_buf())
}

#[cfg(not(all(target_os = "windows", not(feature = "offline"))))]
fn module_dir() -> Option<PathBuf> {
  None
}

/// ゲームフォルダ。
///
/// 以前はすべてカレントディレクトリ基準で、起動のしかたによっては `dfint-data` も
/// 実行ファイルも見つからず、読み込みの時点で落ちていた（記録も残らない）。
/// この DLL はゲームフォルダに置かれるので、まず自分の置き場所を見て、
/// そこに `dfint-data` があればそちらを使う。無ければ今までどおりカレントディレクトリ。
pub fn base_dir() -> &'static Path {
  static BASE: std::sync::OnceLock<PathBuf> = std::sync::OnceLock::new();
  BASE.get_or_init(|| match module_dir() {
    Some(dir) if dir.join(DATA_DIR).is_dir() => dir,
    _ => PathBuf::from("."),
  })
}

/// ゲームフォルダの中のパス
pub fn game_path(subpath: &str) -> PathBuf {
  base_dir().join(subpath)
}

pub fn data_path(subpath: &str) -> PathBuf {
  let mut ret = game_path(DATA_DIR);
  ret.push(subpath);
  ret
}

/// MOD に同梱された日本語訳のファイル（name は "dictionary.csv" など）を探す。
///
/// 探す場所（docs/mod-translation.md）:
///   data/installed_mods/<MOD>/dfint-ja/<name>     ゲームが使用中の MOD のコピー
///   mods/<MOD>/dfint-ja/<name>                    手で入れた MOD
///   ../../workshop/content/975370/<ID>/dfint-ja/<name>   Steam ワークショップ
///   dfint-data/mods/<パック名>/<name>              MOD 作者以外が作った翻訳パック
pub fn mod_translation_files(name: &str) -> Vec<PathBuf> {
  let mut ret = Vec::new();
  let mut scan = |base: PathBuf, sub: Option<&str>| {
    let Ok(entries) = std::fs::read_dir(&base) else { return };
    let mut dirs: Vec<PathBuf> = entries.filter_map(|e| e.ok()).map(|e| e.path()).filter(|p| p.is_dir()).collect();
    dirs.sort();
    for dir in dirs {
      let mut p = dir.clone();
      if let Some(sub) = sub {
        p.push(sub);
      }
      p.push(name);
      if p.is_file() {
        ret.push(p);
      }
    }
  };
  scan(game_path("data/installed_mods"), Some("dfint-ja"));
  scan(game_path("mods"), Some("dfint-ja"));
  scan(game_path("../../workshop/content/975370"), Some("dfint-ja"));
  scan(data_path("mods"), None);
  ret
}
