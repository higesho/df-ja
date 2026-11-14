pub fn get(string: &str) -> Option<String> {
  if string.starts_with(' ') || string.ends_with(' ') || string.contains("  ") {
    return None;
  }

  let (string, designation_wrapper) = super::wrapper::unwrap_designation(string);
  let (body, item_count_wrapper) = super::wrapper::unwrap_item_count(string);

  // 記号だけの部品（家畜の一覧の "♂"、魚の "♀ [5]"）は訳す必要がないのでそのまま通す。
  // 辞書には「英語と訳が同じ行」を入れられないので、ここで受ける
  if !body.is_empty() && !body.chars().any(|ch| ch.is_ascii_alphanumeric()) && !body.is_ascii() {
    return Some(designation_wrapper.wrap(&item_count_wrapper.wrap(body)));
  }

  // まず全体で引く。"large, serrated bronze disc" のように「, 」を含む組み立て型があるので、
  // 区切って引くより先に試す
  if let Some(text) = super::lookup::TOP.get(&body.to_lowercase()) {
    return Some(designation_wrapper.wrap(&item_count_wrapper.wrap(&text)));
  }

  // 全体で引けないときだけ「, 」で区切って引く（魚の "cave fish, ♂" など）
  if string.contains(", ") {
    let parts = string.split(", ").map(get).collect::<Vec<Option<String>>>();
    // 一部だけ引けたときは確定させず、Translator の後段（数字入りの日付などを含む）で区切りごとに訳させる
    if parts.iter().any(|part| part.is_none()) {
      return None;
    }
    return Some(designation_wrapper.wrap(&parts.into_iter().flatten().collect::<Vec<String>>().join(", ")));
  }

  None
}
