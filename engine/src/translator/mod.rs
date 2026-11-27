use std::collections::HashMap;
use std::hash::{DefaultHasher, Hash, Hasher};

use crate::offsets::VERSION;

mod data;
mod lookup;
mod flow;
mod wrapper;

mod default;
mod version;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
struct StringWithContext<'a> {
  pub func: &'static str,
  pub bt: &'a str,
  pub string: &'a str,
}

impl<'a> StringWithContext<'a> {
  pub fn key(&self) -> u64 {
    let mut hasher = DefaultHasher::new();
    self.hash(&mut hasher);
    hasher.finish()
  }
}

#[derive(Default)]
pub struct TranslatedText {
  pub text: String,
  pub horizontal_shift: i32,
}

#[derive(Default)]
pub struct Translator {
  cache: HashMap<u64, TranslatedText>,
  // 文章を単語ごとに描いていると判定した呼び出し元
  paragraph_callers: std::collections::HashSet<String>,
  // 呼び出し元ごとに、文章の中でしか現れない語を何種類描いたか
  paragraph_hits: HashMap<String, std::collections::HashSet<&'static str>>,
  // 訳さない呼び出し元で描かれた単語（ログに1回だけ出すため）
  skipped: std::collections::HashSet<u64>,
  // 「, 」で区切って訳している最中の深さ（区切った部品は行の組み立てに使わない）
  depth: usize,
  // 呼び出し元ごとの、行の流れ（ゲームが自分で折り返して1行ずつ描く文章を組み立て直すため）
  flows: HashMap<String, flow::Flow>,
  // この描画で行が来た呼び出し元（描画の終わりに行の並びを区切る）
  live: Vec<String>,
}

/// 訳に英語の文が残っていないか（小文字の英単語が3文字以上で残っていれば、訳せていない文があるとみなす）
pub(crate) fn fully_translated(ja: &str) -> bool {
  static TAG: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
  let tag = TAG.get_or_init(|| regex::Regex::new(r"\[[^\]]*\]").unwrap());
  let plain = tag.replace_all(ja, "");
  // 空白で区切った語ごとに見る。大文字を含む語は名前や記号とみなして英語と数えない
  // （"God-forsaken"、"Mörulamud"、乱数の種 "vfd2yXTsQMe110XewUMP" など）
  !plain.split_whitespace().any(|word| {
    // 大文字を含む語、アクセント付きのラテン文字を含む語は名前とみなす（"ìmimi"、"Mörulamud"）
    let name_like = word
      .chars()
      .any(|c| c.is_uppercase() || (c.is_alphabetic() && !c.is_ascii() && (c as u32) < 0x0250));
    if name_like {
      return false;
    }
    // 名前の中に挟まる小さな語は許す（"Wings of the Dawn"）
    if matches!(word.trim_matches(|c: char| !c.is_alphabetic()), "the" | "of" | "and" | "in" | "a") {
      return false;
    }
    // 小文字の英字が3つ以上続けば、訳されていない英語とみなす
    let mut run = 0;
    for c in word.chars() {
      if c.is_ascii_lowercase() {
        run += 1;
        if run >= 3 {
          return true;
        }
      } else {
        run = 0;
      }
    }
    false
  })
}

/// 人名・地名のように、英語のまま残してよい部品か（"Kel Urdimtâmol", "\"The Plane of Destiny\""）
fn looks_like_name(s: &str) -> bool {
  let t = s.trim().trim_matches('"');
  !t.is_empty()
    && t.split_whitespace().all(|w| {
      !w.starts_with(|c: char| c.is_ascii_lowercase()) || matches!(w, "of" | "the" | "and" | "in")
    })
}

/// 文章の中でしか単独で現れない語。呼び出し元がこれを1語だけで描いたら、文章を単語ごとに描いているとみなす
const PARAGRAPH_WORDS: &[&str] = &[
  "the", "to", "a", "an", "of", "and", "in", "is", "are", "you", "your", "for", "with", "it", "its", "this", "that",
  "be", "will", "can", "as", "at", "by", "on", "or", "from", "has", "have", "was", "if", "but", "into", "their",
];

impl Translator {
  pub fn translate<'a>(&'a mut self, func: &'static str, string: &'a str, bt: &str) -> (&'a str, i32) {
    if string.starts_with("FPS: ") {
      return (string, 0);
    }
    if string != VERSION.as_str() && string.chars().find(|ch| ch.is_alphabetic()).is_none() {
      return (string, 0);
    }
    // 文章を単語ごとに描く箇所は、単語だけ訳すと英語と日本語が混ざって読めなくなるので訳さない。
    // DFHack は呼び出し元の代わりに描き始めの列を使っているので、この判定からは外す
    // （DFHack が "or" のような語を1つだけ描くと、その列ごと訳されなくなってしまう）
    if let Some(caller) = bt.split('/').next().filter(|caller| !caller.is_empty() && func != "dfhack") {
      if crate::config::CONFIG.settings.no_translate_callers.contains(caller) || self.paragraph_callers.contains(caller) {
        if self.skipped.insert(StringWithContext { func, bt, string }.key()) {
          log::debug!("skip word {func} {bt}: {string:?}");
        }
        return (string, 0);
      }
      if let Some(word) = PARAGRAPH_WORDS.iter().find(|w| **w == string) {
        // 1語だけで決めつけない。説明文中のキー名（"a" など）が紛れ込むため、
        // 同じ呼び出し元が3種類以上描いてから「文章を単語ごとに描いている」とみなす
        let hits = self.paragraph_hits.entry(caller.to_owned()).or_default();
        hits.insert(word);
        if hits.len() >= 3 {
          log::info!("文章を単語ごとに描く呼び出し元を検出（以後は訳さない）: {func} {caller}");
          self.paragraph_callers.insert(caller.to_owned());
        }
        return (string, 0);
      }
    }

    // ゲームが自分で折り返して1行ずつ描く文章は、組み立て直した訳の行を返す。
    // 折り返した文章を描くと分かった呼び出し元では、訳がキャッシュ済みの行も含めて、すべての行を順に流れへ入れる
    // （「, 」で区切った部品と、日本語などを含む行は対象にしない）
    let mut fed = false;
    if self.depth == 0 && string.is_ascii() {
      let caller = bt.split('/').next().unwrap_or("");
      let mut hit = None;
      if let Some(flow) = self.flows.get_mut(caller).filter(|flow| flow.armed) {
        fed = true;
        if !flow.touched {
          flow.touched = true;
          self.live.push(caller.to_owned());
        }
        hit = flow.feed(caller, string);
      }
      if let Some((p, i)) = hit {
        return (self.flows[caller].ja(p, i), 0);
      }
    }

    // 検索キーワード: 訳があれば「訳(英語)」にする（入力欄は英語しか打てないので、英語も見えるようにする）
    if let Some(caller) = bt.split('/').next() {
      if crate::config::CONFIG.settings.keyword_callers.contains(caller) {
        let key = StringWithContext { func, bt, string }.key();
        if !self.cache.contains_key(&key) {
          let text = match lookup_term(string.trim()) {
            Some(ja) if !ja.is_ascii() && ja != string => format!("{ja}({})", string.trim()),
            _ => string.to_owned(),
          };
          self.cache.insert(key, TranslatedText { text, horizontal_shift: 0 });
        }
        let t = self.cache.get(&key).unwrap();
        return (t.text.as_str(), 0);
      }
    }

    let key = StringWithContext { func, bt, string }.key();

    let mut is_legacy = false;
    if !self.cache.contains_key(&key) {
      log::debug!("### {string:?} @{}", bt.split('/').next().unwrap_or(""));

      let lower_string = &string.to_lowercase();

      let caller = bt.split('/').next().unwrap_or("");
      let (text, horizontal_shift) = if let Some(translated) = version::translate_version(string) {
        (translated, 0)
      } else if let Some(translated) = data::CONTEXT.get(caller, lower_string) {
        (translated.to_owned(), 0)
      } else if let Some(translated) = data::USER.get(lower_string) {
        (translated.to_owned(), 0)
      } else if let Some(translated) = default::get(string) {
        (translated, 0)
      } else if let Some(translated) = data::LEGACY.get(lower_string) {
        is_legacy = true;
        (translated.to_owned(), 0)
      } else if let Some(translated) = self.translate_numbers(func, string, bt) {
        (translated, 0)
      } else if let Some(translated) = translate_padded(string) {
        (translated, 0)
      } else if let Some(translated) = translate_speaker(string) {
        (translated, 0)
      } else if let Some(translated) = translate_label(string) {
        (translated, 0)
      } else if let Some(translated) = crate::sentence::SENTENCES.translate_text(string) {
        (translated, 0)
      } else if let Some(translated) = translate_truncated(string) {
        (translated, 0)
      } else if let Some(translated) = translate_cut_name(string) {
        (translated, 0)
      } else if let Some(translated) = translate_titled_name(string) {
        (translated, 0)
      } else if let Some(translated) = translate_counted(string) {
        (translated, 0)
      } else if let Some(translated) = translate_leading_count(string) {
        (translated, 0)
      } else if let Some(translated) = translate_slashed(string) {
        (translated, 0)
      } else if let Some(translated) = translate_possessive(string) {
        (translated, 0)
      } else if let Some(translated) = self.translate_designated(func, string, bt) {
        (translated, 0)
      } else if let Some(translated) = translate_parenthesized(string) {
        (translated, 0)
      } else {
        if string.contains(", ") {
          // 区切りごとに訳す。英語のまま残る部品が人名などでなければ、英語と日本語が混ざるので使わない
          self.depth += 1;
          let parts: Vec<(String, String)> = string
            .split(", ")
            .map(|part| (part.to_owned(), self.translate(func, part, bt).0.to_owned()))
            .collect();
          self.depth -= 1;
          let usable = parts.iter().any(|(en, ja)| en != ja) && parts.iter().all(|(en, ja)| en != ja || looks_like_name(en));
          if usable {
            (parts.into_iter().map(|(_, ja)| ja).collect::<Vec<String>>().join(", "), 0)
          } else {
            (string.to_owned(), 0)
          }
        } else {
          (string.to_owned(), 0)
        }
      };

      // 折り返された行は、一部の語だけ訳せてしまうこともある（"freedom.  All " → "freedom.すべて"）ので、訳せた行も含めてつなぎ直す。
      // ただし日本語などを含む行は対象にしない
      if self.depth == 0 && string.is_ascii() && !fed && !caller.is_empty() {
        let flow = self.flows.entry(caller.to_owned()).or_default();
        flow.push_new(caller, string);
        // ここで折り返した文章を描くと分かったら、この描画の終わりから行の並びを区切り始める
        if flow.armed && !flow.touched {
          flow.touched = true;
          self.live.push(caller.to_owned());
          log::debug!("折り返した文章を描く呼び出し元として、以後すべての行を順に追います @{caller}: {string:?}");
        }
      }
      if string == &text {
        log::debug!("missing translation for {func}:\n{bt}:\n{string:?}\n");
      } else {
        if is_legacy {
          log::warn!("use legacy translation for {func}:\n{bt}:\n- {string:?}\n+ {text:?}\n");
        } else {
          log::trace!("found translation for {func}:\n{bt}:\n- {string:?}\n+ {text:?}\n");
        }
      }
      self.cache.insert(key, TranslatedText { text, horizontal_shift });
    }

    let TranslatedText { text, horizontal_shift } = self.cache.get(&key).unwrap();
    (text, *horizontal_shift)
  }

  /// 画面の組み立て直しが1回終わった。折り返された文章の行の並びを、ここで区切る
  /// （次の描画の1行目を、前の描画の最後の行の続きとみなさないため）
  pub fn end_pass(&mut self) {
    for caller in std::mem::take(&mut self.live) {
      if let Some(flow) = self.flows.get_mut(&caller) {
        flow.end_pass(&caller);
      }
    }
  }

  /// 数字を含む文字列の訳。
  /// 1. 数字を %d に置き換えた形が辞書にあれば、その訳に数字を順に戻す（"Year %d" → "%d年"）
  /// 2. 無ければ「ラベル + 数字」とみなしてラベルだけ訳す（"Elevation 46" → "標高 46"）
  /// 品物に付く印（持ち出し不可の "(…)"、装飾の "«…»"、出来栄えの "-…-"、所有者なしの "{…}"）を
  /// 外して中身だけ訳し、印を戻す。中身が「中身 容れ物（材質）」のような組み立て型でも訳せるようにするため
  fn translate_designated(&mut self, func: &'static str, string: &str, bt: &str) -> Option<String> {
    let (inner, wrapper) = wrapper::unwrap_designation(string);
    if inner.len() == string.len() || inner.is_empty() {
      return None;
    }
    let (inner, prefix, suffix) = (inner.to_owned(), wrapper.prefix.to_owned(), wrapper.suffix.to_owned());
    self.depth += 1;
    let ja = self.translate(func, &inner, bt).0.to_owned();
    self.depth -= 1;
    if ja == inner {
      return None;
    }
    Some(format!("{prefix}{ja}{suffix}"))
  }

  fn translate_numbers(&mut self, func: &'static str, string: &str, bt: &str) -> Option<String> {
    if !string.bytes().any(|b| b.is_ascii_digit()) {
      return None;
    }
    static LABEL_NUM: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    let label_num = LABEL_NUM.get_or_init(|| regex::Regex::new(r"^([A-Za-z][A-Za-z' -]*?)(: ?| )(\d+)$").unwrap());

    if let Some(out) = lookup_numbered(string) {
      return Some(out);
    }

    let caps = label_num.captures(string)?;
    let label = caps[1].to_owned();
    let translated = self.translate(func, &label, bt).0.to_owned();
    if translated == label {
      return None;
    }
    Some(format!("{translated}{}{}", &caps[2], &caps[3]))
  }
}

#[static_init::dynamic]
pub static mut TRANSLATOR: Translator = Translator::default();

/// 「The 職業名 名前」（会話の相手の見出し "The Animal Dissector Cerol Dallithtobul"）→「動物解剖者のCerol Dallithtobul」。
/// 先頭から長い順に職業名を辞書で探し、残りが2語以上の大文字始まり（名前）のときだけ使う
fn translate_titled_name(string: &str) -> Option<String> {
  // 小文字の職業・種族 + 名前（"the farmer Kogan Lelumingish" → "農家のKogan Lelumingish"。攻撃の確認など）
  if let Some(rest) = string.strip_prefix("the ").or_else(|| string.strip_prefix("The ")) {
    let words: Vec<&str> = rest.split(' ').collect();
    let k = words.iter().position(|w| !w.chars().next().map(|c| c.is_ascii_lowercase()).unwrap_or(false));
    if let Some(k) = k.filter(|&k| k > 0) {
      let name_like = |w: &&str| w.chars().next().map(|c| c.is_uppercase() || !c.is_ascii()).unwrap_or(false);
      if words[k..].iter().all(name_like) {
        if let Some(kind) = lookup_term(&words[..k].join(" ")).filter(|ja| !ja.is_ascii()) {
          return Some(format!("{kind}の{}", words[k..].join(" ")));
        }
      }
    }
  }
  let rest = string.strip_prefix("The ")?;
  let words: Vec<&str> = rest.split(' ').collect();
  if words.len() < 3 {
    return None;
  }
  let name_like = |w: &&str| w.chars().next().map(|c| c.is_uppercase() || !c.is_ascii()).unwrap_or(false);
  for k in (1..=words.len() - 2).rev() {
    if !words[k..].iter().all(name_like) {
      continue;
    }
    if let Some(title) = lookup_term(&words[..k].join(" ")) {
      if !title.is_ascii() {
        return Some(format!("{title}の{}", words[k..].join(" ")));
      }
    }
  }
  None
}

/// 個数の付いた品物 "prepared albatross intestines [5]" → 「調理済みのアホウドリの腸 [5]」。
/// 文明の名前の付いた硬貨 "Iclopesor gold coins" → 「Iclopesorの金の硬貨」
fn translate_counted(string: &str) -> Option<String> {
  let (body, count) = match string.rfind(" [") {
    Some(p) if string.ends_with(']') && string[p + 2..string.len() - 1].bytes().all(|b| b.is_ascii_digit()) => {
      (&string[..p], &string[p..])
    }
    _ => (string, ""),
  };
  let translate_body = |b: &str| -> Option<String> {
    if let Some(ja) = lookup_term(b).filter(|ja| !ja.is_ascii()) {
      return Some(ja);
    }
    // 先頭の大文字の語（文明の名前）+ 品物
    let (owner, rest) = b.split_once(' ')?;
    if owner.chars().next()?.is_uppercase() && rest.chars().next()?.is_ascii_lowercase() {
      let ja = lookup_term(rest).filter(|ja| !ja.is_ascii())?;
      return Some(format!("{owner}の{ja}"));
    }
    None
  };
  if count.is_empty() && !string.ends_with(" coins") && !string.ends_with(" coin") {
    return None;
  }
  translate_body(body).map(|ja| format!("{ja}{count}"))
}

/// 頭に個数が付いた品物 "5 pig tail cloth" → 「5 ブタの尾の布」（入植の持ち物など）。
/// 複数形で書かれるので、辞書に無ければ単数形にして引き直す
fn translate_leading_count(string: &str) -> Option<String> {
  let (count, rest) = string.split_once(' ')?;
  if count.is_empty() || !count.bytes().all(|b| b.is_ascii_digit()) || rest.is_empty() {
    return None;
  }
  let ja = lookup_term(rest)
    .filter(|ja| !ja.is_ascii())
    .or_else(|| singular_forms(rest).into_iter().find_map(|s| lookup_term(&s).filter(|ja| !ja.is_ascii())))?;
  Some(format!("{count} {ja}"))
}

/// 複数形の候補を単数形に戻す（最後の語だけを見る）
fn singular_forms(string: &str) -> Vec<String> {
  let last = match string.rsplit(' ').next() {
    Some(l) if l.len() > 2 => l,
    _ => return Vec::new(),
  };
  let head = &string[..string.len() - last.len()];
  let mut out = Vec::new();
  if let Some(base) = last.strip_suffix('s') {
    if !base.ends_with('s') {
      out.push(format!("{head}{base}"));
    }
  }
  if let Some(base) = last.strip_suffix("es") {
    out.push(format!("{head}{base}"));
  }
  if let Some(base) = last.strip_suffix("ies") {
    out.push(format!("{head}{base}y"));
  }
  out
}

/// "/" でつないだ攻撃の名前（"hack/iron battle axe" → "切り刻む/鉄の戦斧"）。部品が全部訳せたときだけ
fn translate_slashed(string: &str) -> Option<String> {
  if !string.contains('/') || string.contains("//") || string.contains(" /") || string.contains("/ ") {
    return None;
  }
  let parts: Vec<String> = string.split('/').map(|p| lookup_term(p).filter(|ja| !ja.is_ascii())).collect::<Option<_>>()?;
  Some(parts.join("/"))
}

/// "the kea's left wing" → 「ケアの左翼」。
/// 組み技の知らせ（"… breaks the grip of the kea's left wing on …"）に差し込まれる形
fn translate_possessive(string: &str) -> Option<String> {
  let pos = string.find("'s ")?;
  let (owner, part) = (&string[..pos], &string[pos + 3..]);
  if owner.is_empty() || part.is_empty() || part.contains("'s ") {
    return None;
  }
  let owner = ["The ", "the ", "A ", "a "].iter().find_map(|a| owner.strip_prefix(a)).unwrap_or(owner);
  let owner_ja = lookup_term(owner).filter(|ja| !ja.is_ascii())?;
  let part_ja = lookup_term(part).filter(|ja| !ja.is_ascii())?;
  Some(format!("{owner_ja}の{part_ja}"))
}

/// "Dodge (Adequate)" → "回避（十分）"。括弧の外と中が両方とも訳せたときだけ
fn translate_parenthesized(string: &str) -> Option<String> {
  let inner_start = string.rfind(" (")?;
  let inner = string[inner_start + 2..].strip_suffix(')')?;
  if inner.contains('(') {
    return None;
  }
  let head_src = &string[..inner_start];
  let head = match lookup_term(head_src).filter(|ja| !ja.is_ascii()) {
    Some(ja) => ja,
    // 記号だけの見出し（家畜の一覧の "♂ (Tame)"）は訳す必要がないのでそのまま残す
    None if !head_src.is_empty() && !head_src.chars().any(|c| c.is_ascii_alphabetic()) => head_src.to_owned(),
    None => return None,
  };
  let inner = lookup_term(inner).filter(|ja| !ja.is_ascii())?;
  Some(format!("{head}（{inner}）"))
}

/// 幅に合わせて "..." で切られた文字列（タブの見出し "Civilizations and o..."、"Nish Zasitnakas, expedition..."）。
/// 切られる前の見出し語が辞書に1種類だけ見つかればその訳、見つからなければ切られた部分の語の訳に「…」を付ける。
/// 「名前, 職業...」の形は名前を残して後ろだけ訳す
fn translate_truncated(string: &str) -> Option<String> {
  let stem = string.strip_suffix("...")?;
  if let Some(ja) = data::USER.complete_prefix(&stem.to_lowercase()) {
    return Some(ja.to_owned());
  }
  // 名前の途中で切れた行動（"Start new conversation with Agêk the Olive..."）は、切れた部分を名前として文テンプレートで訳す
  if stem.contains(' ') {
    if let Some(ja) = crate::sentence::SENTENCES.translate_text(stem).filter(|ja| fully_translated(ja)) {
      return Some(format!("{}…", ja.trim_end_matches('。')));
    }
  }
  let (head, tail) = match stem.rfind(", ") {
    Some(pos) => (Some(&stem[..pos]), &stem[pos + 2..]),
    None => (None, stem),
  };
  let tail_ja = data::USER
    .complete_prefix(&tail.to_lowercase())
    .cloned()
    .or_else(|| lookup_term(tail.trim()).map(|ja| format!("{ja}…")))?;
  Some(match head {
    Some(head) => format!("{}, {tail_ja}", lookup_term(head).unwrap_or_else(|| head.to_owned())),
    None => tail_ja,
  })
}

/// 幅に合わせて切られた品物の名前（"(trillion cut yellow grossu..."）。
/// 切れた末尾の語を落としながら引き直し、引けたところまでを「…」付きで返す
fn translate_cut_name(string: &str) -> Option<String> {
  let stem = string.strip_suffix("...")?.trim_end();
  // 先頭に付いた品物の印（"("、"«"、"-" など）は残して、中身だけ引く
  let body = stem.trim_start_matches(|ch: char| !ch.is_alphanumeric() && ch != ' ');
  let prefix = &stem[..stem.len() - body.len()];
  let mut words: Vec<&str> = body.split(' ').filter(|w| !w.is_empty()).collect();
  if words.len() < 2 {
    return None;
  }
  // 最後の語は途中で切れているので必ず落とす。
  // 残りは2語以上あるものだけ引く（1語まで削ると "large cushion cut kunz..." が
  // 「大…」になってしまい、かえって分からなくなるため）
  words.pop();
  while words.len() >= 2 {
    let head = words.join(" ");
    if let Some(ja) = lookup_term(&head).filter(|ja| !ja.is_ascii()) {
      return Some(format!("{prefix}{ja}…"));
    }
    // 着る者の体の大きさが頭に付く形（"small emu leather low ..."）は、
    // 大きさを外した残り（"emu leather"）で引き直す
    for (size, size_ja) in [("small ", "小型の"), ("large ", "大型の"), ("giant ", "巨大な")] {
      if let Some(rest) = head.strip_prefix(size) {
        if let Some(ja) = lookup_term(rest).filter(|ja| !ja.is_ascii()) {
          return Some(format!("{prefix}{size_ja}{ja}…"));
        }
      }
    }
    words.pop();
  }
  None
}

/// 人の呼び名（"The farmer Urist McDwarf" / "Urist McDwarf, Woodworker"）。
/// 住民の発言は「呼び名: 本文」の形で来るので、呼び名だけを訳すのに使う
fn translate_person_label(string: &str) -> Option<String> {
  if let Some(ja) = lookup_term(string).filter(|ja| !ja.is_ascii()) {
    return Some(ja);
  }
  if let Some(ja) = translate_titled_name(string) {
    return Some(ja);
  }
  let (name, profession) = string.rsplit_once(", ")?;
  if !looks_like_name(name) {
    return None;
  }
  let profession_ja = lookup_term(profession).filter(|ja| !ja.is_ascii())?;
  Some(format!("{name}、{profession_ja}"))
}

/// 住民の発言「呼び名: 本文」（"The farmer Urist McDwarf: It was raining on me.  It's annoying."）。
/// 呼び名と本文を別々に訳し、本文を「」で囲む。本文が全部訳せたときだけ使う
fn translate_speaker(string: &str) -> Option<String> {
  let pos = string.find(": ")?;
  let (label, value) = (&string[..pos], &string[pos + 2..]);
  if value.is_empty() || label.is_empty() || label.len() > 64 || !label.starts_with(|c: char| c.is_alphabetic()) {
    return None;
  }
  let label_ja = translate_person_label(label)?;
  let value_ja = lookup_term(value)
    .filter(|ja| !ja.is_ascii())
    .or_else(|| crate::sentence::SENTENCES.translate_text(value).filter(|ja| fully_translated(ja)))?;
  Some(format!("{label_ja}「{}」", value_ja.trim_end_matches('。')))
}

/// 語句1つの訳を辞書とルックアップから引く（文章のテンプレートに埋め込む語句用）
/// "Lover: Olon Bouldermoisten" のような「ラベル: 値」は、辞書にあるラベルだけ訳す（値も辞書にあれば訳す）
fn translate_label(string: &str) -> Option<String> {
  let pos = string.find(": ")?;
  let (label, value) = (&string[..pos + 2], &string[pos + 2..]);
  if value.is_empty() || label.len() > 64 || !label.starts_with(|c: char| c.is_ascii_uppercase()) {
    return None;
  }
  let label_ja = lookup_term(label)?;
  let value_ja = lookup_term(value)
    .or_else(|| crate::sentence::SENTENCES.translate_text(value).filter(|ja| fully_translated(ja)))
    .unwrap_or_else(|| value.to_owned());
  Some(format!("{label_ja}{value_ja}"))
}

/// 前後に空白が付いた文字列（設定画面の子項目など）は、空白を残して中身だけ訳す
fn translate_padded(string: &str) -> Option<String> {
  let trimmed = string.trim();
  if trimmed.is_empty() || trimmed == string || !string.starts_with(' ') {
    return None;
  }
  let head = &string[..string.len() - string.trim_start().len()];
  let tail = &string[string.trim_end().len()..];
  let ja = lookup_term(trimmed)?;
  Some(format!("{head}{ja}{tail}"))
}

/// 文章（折り返して描くテキスト）から単語辞書を引く。前後の空白は無視し、末尾に空白のある見出し語も引く
pub fn lookup_plain(text: &str) -> Option<String> {
  let trimmed = text.trim();
  lookup_term(trimmed).or_else(|| data::USER.get(&format!("{} ", trimmed.to_lowercase())).cloned())
}

/// その語が辞書のどこかの見出し語に出てくるか（文テンプレートの名前判定に使う）
pub fn knows_word(word: &str) -> bool {
  data::USER.knows_word(word)
}

pub fn lookup_term(string: &str) -> Option<String> {
  let lower = string.to_lowercase();
  if let Some(translated) = data::USER.get(&lower) {
    return Some(translated.to_owned());
  }
  // 組み立て型の表は小文字で書いてあるので、"sandstone Cavern Floor" のような大文字混じりは小文字にしても引く
  default::get(string)
    .or_else(|| if lower != string { default::get(&lower) } else { None })
    .or_else(|| lookup_numbered(string))
}

/// 数字を %d に置き換えた形を辞書で引き、訳に数字を順に戻す（"1st Granite" → "%dst granite" → "花崗岩の月1日"）
fn lookup_numbered(string: &str) -> Option<String> {
  if !string.bytes().any(|b| b.is_ascii_digit()) {
    return None;
  }
  static NUM: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
  let num = NUM.get_or_init(|| regex::Regex::new(r"\d+").unwrap());
  let template = num.replace_all(string, "%d").to_lowercase();
  let translated = data::USER.get(&template)?;
  let mut numbers = num.find_iter(string).map(|m| m.as_str());
  let mut out = String::new();
  let mut rest = translated.as_str();
  while let Some(pos) = rest.find("%d") {
    out.push_str(&rest[..pos]);
    out.push_str(numbers.next().unwrap_or(""));
    rest = &rest[pos + 2..];
  }
  out.push_str(rest);
  Some(out)
}
