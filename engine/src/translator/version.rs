use crate::{config, offsets};

pub fn translate_version(string: &str) -> Option<String> {
  if string == offsets::VERSION.as_str() {
    return Some(format!(
      "{string} + dfint-ja/{}-{}",
      *offsets::PLATFORM,
      config::CONFIG.version
    ));
  }

  None
}
