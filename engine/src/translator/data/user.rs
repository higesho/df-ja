use std::collections::HashMap;

use crate::utils;

#[derive(Debug, serde::Deserialize)]
struct Entry {
  text: String,
  translation: String,
}

#[derive(Debug, Default)]
pub struct User {
  dict: HashMap<String, String>,
}

impl User {
  pub fn get(&self, key: &String) -> Option<&String> {
    self.dict.get(key)
  }

  /// 途中で切られた英語（"civilizations and o"）で始まる見出し語が、訳の違うものを含めて1種類だけなら、その訳を返す。
  /// 見出し語そのもの（切られる前と同じ長さ）は数えない
  pub fn complete_prefix(&self, prefix_lower: &str) -> Option<&String> {
    static SORTED: std::sync::OnceLock<Vec<String>> = std::sync::OnceLock::new();
    let sorted = SORTED.get_or_init(|| {
      let mut keys: Vec<String> = self.dict.keys().cloned().collect();
      keys.sort();
      keys
    });
    if prefix_lower.chars().count() < 6 {
      return None;
    }
    let start = sorted.partition_point(|k| k.as_str() < prefix_lower);
    let mut found: Option<&String> = None;
    for key in sorted[start..].iter().take_while(|k| k.starts_with(prefix_lower)) {
      if key.len() == prefix_lower.len() {
        continue;
      }
      let tr = self.dict.get(key)?;
      match found {
        None => found = Some(tr),
        Some(prev) if prev == tr => {}
        Some(_) => return None,
      }
    }
    found
  }
}

#[static_init::dynamic]
pub static USER: User = {
  let mut ret = User::default();
  utils::load_csv(
    utils::data_path("simple-dictionary.csv"),
    |Entry { text, translation }| {
      ret.dict.insert(text.to_lowercase(), translation);
    },
  );
  let file = utils::data_path("user-dictionary.csv");
  if file.exists() {
    utils::load_csv(file, |Entry { text, translation }| {
      ret.dict.insert(text.to_lowercase(), translation);
    });
  }
  // MOD に同梱された訳。dfint-ja 本体の訳がある語は上書きしない（MOD 独自の語を足すためのもの）
  for file in utils::mod_translation_files("dictionary.csv") {
    let mut added = 0;
    utils::load_csv(&file, |Entry { text, translation }| {
      if !translation.is_empty() {
        if let std::collections::hash_map::Entry::Vacant(e) = ret.dict.entry(text.to_lowercase()) {
          e.insert(translation);
          added += 1;
        }
      }
    });
    log::info!("MOD の訳を読み込みました: {} 件 {:?}", added, file);
  }
  ret
};
