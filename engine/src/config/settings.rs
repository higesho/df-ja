use anyhow::{anyhow, Result};
use std::io::Read;

pub struct Settings {
  pub log_level: log::LevelFilter,
  pub log_file: String,
  pub font_file: String,
  pub use_legacy_dictionary: bool,
  // 文章を単語ごとに描く呼び出し元（バックトレースの先頭、例 "^eb7a1"）。ここからの文字列は訳さない
  pub no_translate_callers: std::collections::HashSet<String>,
  // 検索に使うキーワードを描く呼び出し元。訳に英語を括弧で添える（"挨拶する(greet)"）
  pub keyword_callers: std::collections::HashSet<String>,
  // 見出しを枠の中央に寄せて描く呼び出し元。訳の中心を英語の中心に合わせる
  pub center_callers: std::collections::HashSet<String>,
  // 枠の幅が英語の文字数で決まっている呼び出し元（品物の一覧など）。訳が溢れないよう切り詰める
  pub clamp_callers: std::collections::HashSet<String>,
}

impl Default for Settings {
  fn default() -> Self {
    Self {
      log_level: log::LevelFilter::Debug,
      // 検査用（offline）は、ゲームの記録を上書きしないよう別のファイルに書く
      log_file: if cfg!(feature = "offline") {
        "./dfint-data/dfint-check.log".into()
      } else {
        "./dfint-data/dfint-log.log".into()
      },
      font_file: "./dfint-data/fonts/NotoSansMonoCJKjp-Bold.otf".into(),
      use_legacy_dictionary: false,
      no_translate_callers: Default::default(),
      keyword_callers: Default::default(),
      center_callers: Default::default(),
      clamp_callers: Default::default(),
    }
  }
}

impl Settings {
  pub fn load() -> Result<Self> {
    let mut settings = Self::default();
    simple_logging::log_to_file(&settings.log_file, settings.log_level).unwrap();

    let mut file = std::fs::File::open("./dfint-data/config.txt")?;
    let mut contents: Vec<u8> = Vec::new();
    file.read_to_end(&mut contents)?;

    for cap in regex::bytes::Regex::new(r"\[([^\]:]+):([^\]]+)\]")?.captures_iter(&contents) {
      let key = String::from_utf8_lossy(&cap[1]).into_owned();
      let value = String::from_utf8_lossy(&cap[2]).into_owned();
      match key.as_str() {
        "LOG_LEVEL" => match value.as_str() {
          "Trace" => settings.log_level = log::LevelFilter::Trace,
          "Debug" => settings.log_level = log::LevelFilter::Debug,
          "Info" => settings.log_level = log::LevelFilter::Info,
          "Warn" => settings.log_level = log::LevelFilter::Warn,
          "Error" => settings.log_level = log::LevelFilter::Error,
          "Off" => settings.log_level = log::LevelFilter::Off,
          _ => return Err(anyhow!("無効なログレベル：{value:?}")),
        },
        "LOG_FILE" => {
          if !cfg!(feature = "offline") {
            settings.log_file = value;
          }
        }
        "FONT_FILE" => settings.font_file = value,
        "USE_LEGACY_DICTIONARY" => settings.use_legacy_dictionary = value.to_uppercase() == "YES",
        "NO_TRANSLATE_CALLER" => {
          settings.no_translate_callers.insert(value.trim().to_owned());
        }
        _ => return Err(anyhow!("無効な設定項目：{key:?}")),
      }
    }
    simple_logging::log_to_file(&settings.log_file, settings.log_level).unwrap();

    // 訳さない呼び出し元の一覧（MOD のデータとして毎回入れ替わる。1行に1つ、"#" 以降はコメント）
    if let Ok(list) = std::fs::read_to_string("./dfint-data/no-translate-callers.txt") {
      for line in list.lines() {
        // "^886f7b keyword" のように "keyword" を付けた呼び出し元は、訳に英語を括弧で添える
        let mut fields = line.split('#').next().unwrap_or("").split_whitespace();
        if let Some(caller) = fields.next() {
          match fields.next() {
            // "^886f7b keyword" は訳に英語を括弧で添える、"^1e4f2a center" は中央に寄せ直す
            Some("keyword") => {
              settings.keyword_callers.insert(caller.to_owned());
            }
            Some("center") => {
              settings.center_callers.insert(caller.to_owned());
            }
            // "^390bb7 clamp" は、英語の文字数ぶんの幅に収まるよう訳を切り詰める
            Some("clamp") => {
              settings.clamp_callers.insert(caller.to_owned());
            }
            _ => {
              settings.no_translate_callers.insert(caller.to_owned());
            }
          }
        }
      }
    }

    Ok(settings)
  }
}
