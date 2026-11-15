#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]

mod config;
mod df;
mod dfhack;
mod encodings;
mod font;
mod hooks;
mod offsets;
pub mod paragraph;
mod screen;
mod shadow;
pub mod sentence;
mod tabs;
pub mod translator;
mod utils;
mod watchdog;
mod wrap;

use crate::config::CONFIG;

// offline の印を付けてビルドしたときは、ゲームに割り込む仕掛けを丸ごと外して
// 翻訳器だけを使えるようにする（検査用の dfint-check 向け）
#[cfg(not(feature = "offline"))]
#[static_init::constructor]
#[no_mangle]
extern "C" fn attach() {
  std::env::set_var("RUST_BACKTRACE", "1");

  log::info!("dfint-ja バージョン: {}", CONFIG.version);
  log::info!("dfint-ja プラットフォーム: {}", *offsets::PLATFORM);
  log::info!("フォントファイル: {:?}", CONFIG.settings.font_file);

  match unsafe { hooks::attach_all() } {
    Ok(_) => log::debug!("日本語化を有効にしました"),
    Err(err) => {
      log::error!("unable to attach hooks, {:?}", err);
      utils::show_error_dialog("日本語化を有効にできませんでした");
      return;
    }
  };
  watchdog::install();

  log::info!("{:#?}", offsets::FIELDS.clone());
}

#[cfg(not(feature = "offline"))]
#[static_init::destructor]
#[no_mangle]
extern "C" fn detach() {
  unsafe {
    watchdog::uninstall();
    let _ = hooks::disable_all();
    log::debug!("日本語化を無効にしました");
  }
}

#[no_mangle]
extern "C" fn super_secret_dfint_sign() -> u8 {
  69
}
