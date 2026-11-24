// DLL にバージョン情報（右クリック →「プロパティ」→「詳細」に出るもの）を入れる。
//
// version.rc を Windows SDK の rc.exe で .res にして、DLL のリンクに足す。
// 版番号は環境変数 HOOK_VERSION（tools/package.ps1 が付ける）、なければ Cargo.toml の version。
// 版番号は OUT_DIR に書く version.h で version.rc に渡す。
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
  println!("cargo:rerun-if-changed=version.rc");
  println!("cargo:rerun-if-env-changed=HOOK_VERSION");
  if env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("windows") {
    return;
  }
  let version = env::var("HOOK_VERSION").unwrap_or_else(|_| env::var("CARGO_PKG_VERSION").unwrap());
  let mut nums: Vec<u16> = version.split('.').map(|s| s.parse().unwrap_or(0)).collect();
  nums.resize(4, 0);
  let out = PathBuf::from(env::var("OUT_DIR").unwrap());
  fs::write(
    out.join("version.h"),
    format!(
      "#define VER_NUM {},{},{},{}\n#define VER_STR \"{}\"\n",
      nums[0], nums[1], nums[2], nums[3], version
    ),
  )
  .unwrap();
  let res = out.join("version.res");
  let ok = Command::new(find_rc())
    .args(["/nologo", "/i"])
    .arg(&out)
    .arg("/fo")
    .arg(&res)
    .arg("version.rc")
    .status()
    .map(|s| s.success())
    .unwrap_or(false);
  if !ok {
    panic!("version.rc を rc.exe でコンパイルできませんでした");
  }
  println!("cargo:rustc-link-arg-cdylib={}", res.display());
}

/// rc.exe を探す。PATH にあればそれ（vcvars の中）、なければ Windows SDK の新しい版から
fn find_rc() -> PathBuf {
  if let Ok(p) = env::var("RC") {
    return PathBuf::from(p);
  }
  let kits = PathBuf::from(r"C:\Program Files (x86)\Windows Kits\10\bin");
  let mut vers: Vec<PathBuf> = fs::read_dir(&kits)
    .map(|d| d.filter_map(|e| e.ok()).map(|e| e.path().join(r"x64\rc.exe")).filter(|p| p.exists()).collect())
    .unwrap_or_default();
  vers.sort();
  vers.pop().unwrap_or_else(|| PathBuf::from("rc.exe"))
}
