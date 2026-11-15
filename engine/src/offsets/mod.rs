mod types;

mod functions;
pub use functions::*;

mod globals;
pub use globals::*;

mod fields;
pub use fields::*;

mod game;

#[cfg(target_os = "linux")]
pub const EXE_NAME: &'static str = "dwarfort";

#[cfg(target_os = "windows")]
pub const EXE_NAME: &'static str = "Dwarf Fortress.exe";

#[static_init::dynamic]
pub static PATH_EXE: String = crate::utils::game_path(EXE_NAME).to_string_lossy().into_owned();

#[static_init::dynamic]
pub static GAME: game::Game = match game::Game::new(&*PATH_EXE) {
  Ok(game) => game,
  Err(err) => {
    // ここで落ちるとゲームごと巻き込むうえ、記録も残らず原因が分からない。
    // せめて何を探して駄目だったかを出す
    let message = format!("ゲームの実行ファイルを読めません：{}\n{err}", *PATH_EXE);
    crate::utils::show_error_dialog(&message);
    panic!("{}", message);
  }
};

#[static_init::dynamic]
pub static VERSION: String = GAME.version().to_owned();

#[static_init::dynamic]
pub static PLATFORM: String = format!("{}-{}", GAME.os(), GAME.platform());
