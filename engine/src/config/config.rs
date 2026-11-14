use anyhow::Result;

use crate::utils;

use super::offsets;
use super::settings;

#[static_init::dynamic]
pub static CONFIG: Config = Config::new();

pub struct Config {
  pub settings: settings::Settings,
  pub offsets: offsets::Offsets,
  pub version: &'static str,
}

impl Config {
  pub fn new() -> Self {
    match Self::load() {
      Ok(config) => config,
      Err(message) => {
        let message = format!("設定ファイルの読み込みに失敗しました：{message}");
        utils::show_error_dialog(&message);
        panic!("{}", message);
      }
    }
  }

  pub fn load() -> Result<Self> {
    let settings = settings::Settings::load()?;
    let offsets = offsets::Offsets::load()?;
    let version = match option_env!("HOOK_VERSION") {
      Some(version) => version,
      None => "開発版",
    };

    Ok(Self {
      settings,
      offsets,
      version,
    })
  }
}
