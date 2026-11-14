use std::collections::HashMap;

use crate::utils;

/// 呼び出し元ごとの訳（同じ英語でも場所によって意味が違うもの。例: 並べ替えの見出し "Cat" は「分類」、動物の "Cat" は「猫」）
/// context-dictionary.csv: caller,text,translation（caller はバックトレースの先頭、例 "^3fc6c1"）
#[derive(Debug, serde::Deserialize)]
struct Entry {
  caller: String,
  text: String,
  translation: String,
}

#[derive(Debug, Default)]
pub struct Context {
  dict: HashMap<(String, String), String>,
}

impl Context {
  pub fn get(&self, caller: &str, lower_text: &str) -> Option<&String> {
    if self.dict.is_empty() {
      return None;
    }
    self.dict.get(&(caller.to_owned(), lower_text.to_owned()))
  }
}

#[static_init::dynamic]
pub static CONTEXT: Context = {
  let mut ret = Context::default();
  let file = utils::data_path("context-dictionary.csv");
  if file.exists() {
    utils::load_csv(file, |Entry { caller, text, translation }| {
      ret.dict.insert((caller.trim().to_owned(), text.to_lowercase()), translation);
    });
  }
  ret
};
