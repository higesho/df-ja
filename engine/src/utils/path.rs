use std::path::PathBuf;

const DATA_DIR: &str = "dfint-data";

pub fn data_path(subpath: &str) -> PathBuf {
  let mut ret = PathBuf::new();
  ret.push(DATA_DIR);
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
  scan(PathBuf::from("data/installed_mods"), Some("dfint-ja"));
  scan(PathBuf::from("mods"), Some("dfint-ja"));
  scan(PathBuf::from("../../workshop/content/975370"), Some("dfint-ja"));
  scan(data_path("mods"), None);
  ret
}
