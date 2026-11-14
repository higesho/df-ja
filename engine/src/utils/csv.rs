pub fn load_csv<T: serde::de::DeserializeOwned, P: AsRef<std::path::Path>, F>(path: P, f: F)
where
  F: FnMut(T),
{
  let path = path.as_ref();
  let file = match std::fs::File::open(path) {
    Ok(file) => file,
    Err(err) => {
      log::warn!("CSVを開けません {path:?}: {err}");
      return;
    }
  };
  csv::Reader::from_reader(file)
    .deserialize::<T>()
    .filter_map(|it| match it {
      Ok(entry) => Some(entry),
      Err(err) => {
        log::warn!("CSVの行を読み飛ばしました {path:?}: {err}");
        None
      }
    })
    .for_each(f);
}
