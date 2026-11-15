//! 文テンプレートによる翻訳。
//!
//! ゲームは英文を「書き出し + 本体 + 後ろの句」の部品をつなげて作る（例: "In 125, " + "{1} struck down {2}" + " in {1}."）。
//! sentence-templates.csv に、部品ごとの英語と日本語を持つ。
//!   group,kind,text,translation
//!   kind = prefix（書き出し）/ core（本体）/ suffix（後ろの句）。同じ group の部品どうしを組み合わせる
//!   {1} {2} … は差し込まれる語句。core の訳では {REST} の位置に suffix の訳が入る（無ければ末尾）
//! 文末の . ! ? は照合の前に外し、訳の最後に 。！？ を付ける。

use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

use aho_corasick::AhoCorasick;
use regex::Regex;

use crate::utils;

struct Part {
  src: String,
  ja: String,
  slots: usize,
  // 照合の捕捉の並び。true = 差し込み {N}、false = 色の変更 [C:..]（どの色でも一致させ、訳文の色を置き換える）
  kinds: Vec<bool>,
  // 差し込みと色の変更の間にある英語の固定部分（kinds.len() + 1 個。空のこともある）
  segs: Vec<String>,
}

impl Part {
  fn new(src: String, ja: String) -> Self {
    let kinds: Vec<bool> = token_regex().find_iter(&src).map(|m| m.as_str().starts_with('{')).collect();
    let slots = kinds.iter().filter(|k| **k).count();
    let segs = token_regex().split(&src).map(|s| s.to_owned()).collect();
    Self { src, ja, slots, kinds, segs }
  }

  /// 固定部分がすべて、この順で body[from..to] に現れるか（正規表現を作る前の安い絞り込み）
  fn segs_in_order(&self, body: &str, skip: usize, from: usize, to: usize) -> bool {
    let mut pos = from;
    for seg in self.segs.iter().skip(skip) {
      if seg.is_empty() {
        continue;
      }
      match body.get(pos..to).and_then(|b| b.find(seg.as_str())) {
        Some(i) => pos += i + seg.len(),
        None => return false,
      }
    }
    true
  }

  /// 書き出しとして使えるか: 文の先頭が一致し、残りの固定部分も順に現れる
  fn fits_start(&self, body: &str) -> bool {
    body.starts_with(self.segs[0].as_str()) && self.segs_in_order(body, 1, self.segs[0].len(), body.len())
  }

  /// 後ろの句として使えるか: 文の末尾が一致し、残りの固定部分も（後ろから）順に現れる
  fn fits_end(&self, body: &str) -> bool {
    let last = self.segs.last().map(|s| s.as_str()).unwrap_or("");
    if !body.ends_with(last) {
      return false;
    }
    let mut end = body.len() - last.len();
    for seg in self.segs.iter().rev().skip(1) {
      if seg.is_empty() {
        continue;
      }
      match body[..end].rfind(seg.as_str()) {
        Some(i) => end = i,
        None => return false,
      }
    }
    true
  }

  fn literal_len(&self) -> usize {
    token_regex().replace_all(&self.src, "").len()
  }

  /// 捕捉した値（この部品の分）から訳を作る
  fn render(&self, caps: &[&str], tr: &dyn Fn(&str) -> String) -> String {
    let mut slot_vals = Vec::new();
    let mut colors = Vec::new();
    for (v, is_slot) in caps.iter().zip(self.kinds.iter()) {
      if *is_slot {
        slot_vals.push(tr(v));
      } else {
        colors.push(*v);
      }
    }
    recolor(&fill(&self.ja, &slot_vals), &colors)
  }
}

fn token_regex() -> &'static Regex {
  static R: OnceLock<Regex> = OnceLock::new();
  R.get_or_init(|| Regex::new(r"\{\d+\}|\[C:\d+:\d+:\d+\]").unwrap())
}

/// 訳文の色の変更を、英文で実際に使われた色に順に置き換える
fn recolor(ja: &str, colors: &[&str]) -> String {
  if colors.is_empty() {
    return ja.to_owned();
  }
  static C: OnceLock<Regex> = OnceLock::new();
  let c = C.get_or_init(|| Regex::new(r"\[C:\d+:\d+:\d+\]").unwrap());
  let mut i = 0;
  c.replace_all(ja, |m: &regex::Captures| {
    let r = colors.get(i).map(|s| s.to_string()).unwrap_or_else(|| m[0].to_owned());
    i += 1;
    r
  })
  .into_owned()
}

struct Group {
  // 手で書いたテンプレート（sentences-fix.tsv の group "manual"）。固定部分の量の制限をかけない
  trusted: bool,
  // 英語の固定部分が長い順（具体的なものから試す）
  prefixes: Vec<Part>,
  suffixes: Vec<Part>,
}

struct Core {
  group: usize,
  part: Part,
}

#[derive(Default)]
pub struct Sentences {
  groups: Vec<Group>,
  cores: Vec<Core>,
  keywords: Vec<usize>, // AhoCorasick のパターン番号 -> core 番号
  matcher: Option<AhoCorasick>,
  // (本体, 書き出し, 後ろの句) ごとの正規表現。絞り込みを通った組み合わせだけ作る
  regexes: Mutex<HashMap<(usize, usize, usize), Option<Regex>>>,
}

#[derive(Debug, serde::Deserialize)]
struct Entry {
  group: String,
  kind: String,
  text: String,
  translation: String,
}

fn slot_regex() -> &'static Regex {
  static R: OnceLock<Regex> = OnceLock::new();
  R.get_or_init(|| Regex::new(r"\{(\d+)\}").unwrap())
}

/// 程度を表す語（辞書に無いときに使う）
const DEGREES: &[(&str, &str)] = &[
  ("very", "とても"), ("quite", "かなり"), ("somewhat", "やや"), ("slightly", "わずかに"), ("extremely", "非常に"),
  ("incredibly", "信じられないほど"), ("extraordinarily", "並外れて"), ("nearly", "ほとんど"), ("sharply", "鋭く"),
  ("deeply", "深く"), ("a little", "少し"), ("fairly", "わりと"),
];

/// 小文字の語句を、辞書にある語句を左から長い順に当ててつなぐ（"very long beard" → "とても長い" + "あごひげ"）。
/// 全部の語が訳せたときだけ。名詞どうしの間には「の」を入れる（"amethyst eyes" → "アメジストの目"）
fn compose_words(t: &str) -> Option<String> {
  if !t.contains(' ') || !t.chars().all(|c| c.is_ascii_lowercase() || c == ' ' || c == '-' || c == '\'') {
    return None;
  }
  let words: Vec<&str> = t.split(' ').filter(|w| !w.is_empty()).collect();
  if words.len() < 2 || words.len() > 8 {
    return None;
  }
  let mut out = String::new();
  let mut i = 0;
  while i < words.len() {
    let mut found = None;
    for j in (i + 1..=words.len()).rev() {
      if i == 0 && j == words.len() {
        continue; // 全体はすでに辞書で引いている
      }
      let phrase = words[i..j].join(" ");
      let ja = crate::translator::lookup_term(&phrase)
        .or_else(|| DEGREES.iter().find(|(en, _)| *en == phrase).map(|(_, ja)| (*ja).to_owned()));
      if let Some(ja) = ja {
        found = Some((j, ja));
        break;
      }
    }
    let (j, ja) = found?;
    let is_noun_end = |s: &str| {
      s.chars().last().map(|c| ('\u{30A0}'..='\u{30FF}').contains(&c) || ('\u{4E00}'..='\u{9FFF}').contains(&c)).unwrap_or(false)
        && !s.ends_with('的')
    };
    let starts_noun = ja.chars().next().map(|c| ('\u{30A0}'..='\u{30FF}').contains(&c) || ('\u{4E00}'..='\u{9FFF}').contains(&c)).unwrap_or(false);
    if is_noun_end(&out) && starts_noun {
      out.push('の');
    }
    out.push_str(&ja);
    i = j;
  }
  Some(out)
}

/// 種族名の訳。辞書に無い悪魔・夜の生き物（"lizard fiend", "moon creature"）は「動物名＋種類」として訳す
fn creature_kind(s: &str) -> Option<String> {
  if let Some(ja) = crate::translator::lookup_term(s) {
    return Some(ja);
  }
  const KINDS: &[(&str, &str)] = &[
    (" fiend", "の悪鬼"), (" demon", "の悪魔"), (" devil", "の魔物"), (" spirit", "の霊"), (" monster", "の怪物"),
    (" brute", "の獣鬼"), (" creature", "の生き物"), (" titan", "のタイタン"),
  ];
  for (en, ja) in KINDS {
    if let Some(rest) = s.strip_suffix(en) {
      if let Some(base) = crate::translator::lookup_term(rest) {
        return Some(format!("{base}{ja}"));
      }
      // 形容詞 + monster（忘れられた獣・夜の生き物 "shrieking monster"、"bleak monster"）は語を組み立てる
      if let Some(base) = compose_words(rest) {
        return Some(format!("{base}{ja}"));
      }
    }
  }
  None
}

/// 差し込み1つにあたる正規表現。リンク全体・ほかのトークン・'[' 以外の1文字の並び
const SLOT_PATTERN: &str = r"((?:\[LPAGE:[^\]]*\][^\[]*\[/LPAGE\]|\[[^L/\]][^\]]*\]|[^\[])+?)";

/// 部品の英語を正規表現にする（{N} は任意の語句、[C:..] は任意の色）
fn pattern(src: &str) -> String {
  let mut out = String::new();
  let mut last = 0;
  for m in token_regex().find_iter(src) {
    out.push_str(&regex::escape(&src[last..m.start()]));
    // 差し込みは、リンク [LPAGE:..]…[/LPAGE] を1かたまりとして扱う（"The Town of Entrancing" の " of " で切らない）
    out.push_str(if m.as_str().starts_with('{') { SLOT_PATTERN } else { r"(\[C:\d+:\d+:\d+\])" });
    last = m.end();
  }
  out.push_str(&regex::escape(&src[last..]));
  out
}

/// 照合の手がかりにする、いちばん長い英語の部分
fn keyword(src: &str) -> Option<String> {
  token_regex()
    .split(src)
    .map(|s| s.to_owned())
    .filter(|s| s.trim().len() >= 3 && s.chars().any(|c| c.is_ascii_alphabetic()))
    .max_by_key(|s| s.len())
}

#[static_init::dynamic]
pub static SENTENCES: Sentences = Sentences::load(&utils::data_path("sentence-templates.csv"));

impl Sentences {
fn load(path: &std::path::Path) -> Sentences {
  let mut ret = Sentences::default();
  let mut group_ids: HashMap<String, usize> = HashMap::new();
  let mut kw_list: Vec<String> = Vec::new();
  if path.exists() {
    utils::load_csv(path, |Entry { group, kind, text, translation }| {
      let trusted = group == "manual";
      let gi = *group_ids.entry(group).or_insert_with(|| {
        ret.groups.push(Group { trusted, prefixes: Vec::new(), suffixes: Vec::new() });
        ret.groups.len() - 1
      });
      // 書き出し（"He "、"In {1}, "）は後ろの空白も照合に使うので削らない。本体と後ろの句は文末の記号と空白を外す
      let text = if kind == "prefix" { text } else { strip_end(&text).0.to_owned() };
      let translation = strip_end_ja(&translation).to_owned();
      match kind.as_str() {
        "prefix" => ret.groups[gi].prefixes.push(Part::new(text, translation)),
        "suffix" => ret.groups[gi].suffixes.push(Part::new(text, translation)),
        _ => {
          if let Some(kw) = keyword(&text) {
            kw_list.push(kw);
            ret.keywords.push(ret.cores.len());
            ret.cores.push(Core { group: gi, part: Part::new(text, translation) });
          }
        }
      }
    });
  }
  for g in ret.groups.iter_mut() {
    g.prefixes.sort_by_key(|p| std::cmp::Reverse(p.literal_len()));
    g.suffixes.sort_by_key(|p| std::cmp::Reverse(p.literal_len()));
  }
  ret.matcher = AhoCorasick::new(&kw_list).ok();
  log::info!("文テンプレート: 本体 {} 件 / {} グループ", ret.cores.len(), ret.groups.len());
  ret
}
}

/// [..] のトークンを除いた英字の数
fn alpha_count(s: &str) -> usize {
  let mut n = 0;
  let mut in_tok = false;
  for c in s.chars() {
    match c {
      '[' => in_tok = true,
      ']' => in_tok = false,
      _ if !in_tok && c.is_ascii_alphabetic() => n += 1,
      _ => {}
    }
  }
  n
}

/// 2文字以上の英単語の数（トークンを除く）
fn word_count(s: &str) -> usize {
  token_regex()
    .replace_all(s, " ")
    .split(|c: char| !c.is_ascii_alphabetic())
    .filter(|w| w.len() >= 2)
    .count()
}

/// 固定部分が文のごく一部しかない当てはめは使わない（"the {1} The {2} {3}" が名前に当たるなど）
fn enough_literal(parts: &[&Part], body: &str) -> bool {
  let lit: String = parts.iter().map(|p| p.segs.join(" ")).collect::<Vec<_>>().join(" ");
  has_content_word(&lit) && (word_count(&lit) >= 2 || alpha_count(&lit) * 10 >= alpha_count(body) * 3)
}

/// 冠詞・前置詞などではない英単語（3文字以上）を含むか。"It was {1}" や "the {1} of the {2}" だけでは当てはめない
fn has_content_word(s: &str) -> bool {
  const STOP: &[&str] = &[
    "the", "and", "was", "were", "are", "his", "her", "its", "for", "with", "from", "into", "this", "that", "has", "had", "have",
    "not", "but", "who", "him", "she", "they", "them", "their", "then", "than", "there", "one", "all", "some",
  ];
  token_regex()
    .replace_all(s, " ")
    .split(|c: char| !c.is_ascii_alphabetic())
    .any(|w| w.len() >= 3 && !STOP.contains(&w.to_ascii_lowercase().as_str()))
}

/// 差し込みの値が単語の途中で切れていないか
fn on_word_boundary(body: &str, start: usize, end: usize) -> bool {
  let is_w = |c: Option<char>| c.map(|c| c.is_ascii_alphanumeric()).unwrap_or(false);
  let before = body[..start].chars().next_back();
  let first = body[start..end].chars().next();
  let last = body[start..end].chars().next_back();
  let after = body[end..].chars().next();
  !(is_w(before) && is_w(first)) && !(is_w(last) && is_w(after))
}

/// 部品の中で差し込みどうしが隣り合っているか（区切りが決まらない）
fn has_adjacent_slots(src: &str) -> bool {
  src.contains("}{")
}

/// 伝説の年の言い方 "In the late autumn of 2, " の季節
const SEASONS: &[(&str, &str)] = &[
  ("early spring", "初春"),
  ("midspring", "仲春"),
  ("late spring", "晩春"),
  ("early summer", "初夏"),
  ("midsummer", "仲夏"),
  ("late summer", "晩夏"),
  ("early autumn", "初秋"),
  ("midautumn", "仲秋"),
  ("late autumn", "晩秋"),
  ("early winter", "初冬"),
  ("midwinter", "仲冬"),
  ("late winter", "晩冬"),
];

/// "In the late autumn of 2, ..." を "In 2, ..." にして照合し、訳の "2年、" を "2年の晩秋、" に戻すための情報
fn split_season(sentence: &str) -> Option<(String, String, &'static str)> {
  let rest = sentence.strip_prefix("In the ")?;
  for (en, ja) in SEASONS {
    if let Some(r) = rest.strip_prefix(en).and_then(|r| r.strip_prefix(" of ")) {
      let year: String = r.chars().take_while(|c| c.is_ascii_digit()).collect();
      if !year.is_empty() && r[year.len()..].starts_with(", ") {
        return Some((format!("In {year}{}", &r[year.len()..]), year, ja));
      }
    }
  }
  None
}

/// 文末の . ! ? を外し、日本語の句点を返す
fn strip_end(s: &str) -> (&str, &'static str) {
  let t = s.trim_end();
  // 幅に合わせて途中で切った文字列（"Start new conversation with Agêk the Olive..."）は句点ではなく省略
  if let Some(x) = t.strip_suffix("...") {
    return (x, "…");
  }
  if let Some(x) = t.strip_suffix('.') {
    (x, "。")
  } else if let Some(x) = t.strip_suffix('!') {
    (x, "！")
  } else if let Some(x) = t.strip_suffix('?') {
    (x, "？")
  } else {
    (t, "")
  }
}

fn strip_end_ja(s: &str) -> &str {
  s.trim_end().trim_end_matches(|c| c == '。' || c == '！' || c == '？')
}

/// left の末尾と right の先頭がどちらも差し込みか（間が空白だけでも同じ）
fn adjacent(left: &str, right: &str) -> bool {
  left.trim_end().ends_with('}') && right.trim_start().starts_with('{')
}

fn fill(ja: &str, values: &[String]) -> String {
  slot_regex()
    .replace_all(ja, |c: &regex::Captures| {
      let i: usize = c[1].parse().unwrap_or(0);
      values.get(i.wrapping_sub(1)).cloned().unwrap_or_default()
    })
    .into_owned()
}

impl Sentences {
  /// 差し込まれた語句の訳（さらにテンプレートや辞書で訳せれば訳す。名前などはそのまま）
  fn value(&self, v: &str, depth: usize) -> String {
    let t = v.trim();
    if t.is_empty() {
      return v.to_owned();
    }
    // リンク [LPAGE:..]語句[/LPAGE] は中身だけ訳して包み直す
    if let Some(rest) = t.strip_prefix("[LPAGE:") {
      if let (Some(close), true) = (rest.find(']'), t.ends_with("[/LPAGE]")) {
        let open = &t[..7 + close + 1];
        let inner = &t[open.len()..t.len() - 8];
        if !inner.contains("[LPAGE") {
          return format!("{open}{}[/LPAGE]", self.value(inner, depth));
        }
      }
    }
    // 冠詞がリンクの外にある "the [LPAGE:HF:1]roc Piral[/LPAGE]" は、冠詞を外してリンクの中身を訳す
    for art in ["the ", "a ", "an "] {
      if let Some(rest) = t.strip_prefix(art) {
        if rest.starts_with("[LPAGE:") && rest.ends_with("[/LPAGE]") && rest.matches("[LPAGE").count() == 1 {
          return self.value(rest, depth);
        }
      }
    }
    // 1. 辞書の完全一致（"a foot race" が文テンプレート「徒競走を行った」に当たるのを防ぐため先に引く）
    if let Some(ja) = crate::translator::lookup_term(t) {
      return ja;
    }
    // 冠詞を外した形が辞書にそのままあれば使う（"the Gem Setter" が職業名の部品のテンプレートに当たって「the宝石はめ込み師」になっていた）
    for art in ["the ", "The ", "a ", "an ", "A ", "An "] {
      if let Some(ja) = t.strip_prefix(art).and_then(crate::translator::lookup_term) {
        return ja;
      }
    }
    // 2. 列挙（"hunting, the wind and the sky" → "狩猟、風、空"）。項目ごとに訳し、訳せない項目が名前（大文字始まり）だけのときに使う。
    //    "a telling of the story of …, a performance of …, incense burning" の全体が「a telling of the story of {1}」に当たるのを防ぐため、テンプレートより先に試す
    if depth < 3 && (t.contains(", ") || t.contains(" and ")) {
      if let Some(ja) = self.value_list(t, depth) {
        return ja;
      }
    }
    if depth < 3 {
      if let Some(ja) = self.translate_one(t, depth + 1, false) {
        // 語句の訳に、英語に無い文末の記号が付いたら、別の文のテンプレートに当たったとみなして使わない
        let adds_punct = ja.contains(['。', '！', '？']) && !t.contains(['.', '!', '?']);
        if !adds_punct {
          return ja;
        }
      }
    }
    // "the kobold Drabapaymer" / "The dwarf Logem" → "コボルドのDrabapaymer"（種族や職業 + 名前）
    let bare = ["a ", "an ", "the ", "A ", "An ", "The "].iter().find_map(|a| t.strip_prefix(a)).unwrap_or(t);
    let words: Vec<&str> = bare.split(' ').collect();
    for k in (1..words.len()).rev() {
      // 名前は大文字始まり。ゲームは ì などの非 ASCII 文字を大文字にしないので、それも名前の始まりとみなす
      if words[k].chars().next().map(|c| c.is_uppercase() || !c.is_ascii()).unwrap_or(false)
        && words[..k].iter().all(|w| w.chars().next().map(|c| c.is_ascii_lowercase()).unwrap_or(false))
      {
        if let Some(ja) = creature_kind(&words[..k].join(" ")) {
          return format!("{ja}の{}", words[k..].join(" "));
        }
      }
    }
    // "Farmer Kogan Lelumingish"（大文字の職業名 + 2語以上の名前）→ "農家のKogan Lelumingish"。
    // 冠詞付きの "the Farmer Momu"（会話相手の一覧で幅に合わせて切られたもの）は名前が1語でもよい
    // 職業名が2語（"the Gem Setter Kosoth"）のときは長い方から試す
    let cap = |w: &&str| w.chars().next().map(|c| c.is_uppercase() || !c.is_ascii()).unwrap_or(false);
    if words.iter().all(cap) {
      let min_names = if t.starts_with("the ") { 1 } else { 2 };
      for k in (1..=2.min(words.len().saturating_sub(min_names))).rev() {
        if let Some(ja) = crate::translator::lookup_term(&words[..k].join(" ")).filter(|ja| !ja.is_ascii()) {
          return format!("{ja}の{}", words[k..].join(" "));
        }
      }
    }
    // 冠詞を外して辞書を引く（"a steel battle axe" → "steel battle axe"）
    for art in ["a ", "an ", "the ", "some ", "The ", "A ", "An "] {
      if let Some(rest) = t.strip_prefix(art) {
        if let Some(ja) = crate::translator::lookup_term(rest) {
          return ja;
        }
      }
    }
    // 「名詞's 名詞」（"the goblin's iron breastplate" → 「ゴブリンの鉄の胸当て」）。両方訳せたときだけ
    if let Some(p) = t.rfind("'s ") {
      if depth < 3 {
        let (owner, thing) = (&t[..p], &t[p + 3..]);
        let (oj, tj) = (self.value(owner, depth + 1), self.value(thing, depth + 1));
        if oj != owner && tj != thing {
          return format!("{oj}の{tj}");
        }
      }
    }
    // 所有の代名詞を外して訳す（戦闘の文 "with his iron mace" → 「鉄のメイス」、"your right hand" → 「あなたの右手」）
    for (pos, pre) in [("his ", ""), ("her ", ""), ("its ", ""), ("their ", ""), ("your ", "あなたの")] {
      if let Some(rest) = t.strip_prefix(pos) {
        if depth < 3 {
          let ja = self.value(rest, depth + 1);
          if ja != rest {
            return format!("{pre}{ja}");
          }
        }
      }
    }
    // 外見の語句（"very long beard"、"nearly fuse-lobed ears"）は、辞書にある語句を左から長い順につないで組み立てる
    if let Some(ja) = compose_words(t) {
      return ja;
    }
    t.to_owned()
  }

  /// 列挙を項目ごとに訳して「、」でつなぐ。1つも訳せないとき、名前らしくない項目が訳せないとき、
  /// リンク [LPAGE] の途中で切れるときは None。
  /// 項目の中にも " and " がある（"celebrates talented artisans and their masterworks"）ので、まず ", " で分け、
  /// 訳せない項目だけを " and " の位置で分けてみる
  fn value_list(&self, t: &str, depth: usize) -> Option<String> {
    if t.split(", ").any(|s| s.matches("[LPAGE").count() != s.matches("[/LPAGE]").count()) {
      return None;
    }
    static TAG: OnceLock<Regex> = OnceLock::new();
    let tag = TAG.get_or_init(|| Regex::new(r"\[[^\]]*\]").unwrap());
    let name_like = |s: &str| tag.replace_all(s, "").trim().starts_with(|c: char| c.is_uppercase());
    let ok = |en: &str, ja: &str| en != ja || name_like(en);
    let mut out: Vec<String> = Vec::new();
    let mut any = false;
    let raw: Vec<&str> = t.split(", ").map(str::trim).filter(|s| !s.is_empty()).collect();
    if raw.len() < 2 && !t.contains(" and ") {
      return None;
    }
    // 句そのものに ", " を含むもの（"values decorum, dignity and proper behavior"、"prefers a noisy, bustling life to …"）は、
    // 辞書にある最も長いつながりを1項目にする
    let mut pieces: Vec<String> = Vec::new();
    let mut i = 0;
    while i < raw.len() {
      let mut j = raw.len();
      while j > i + 1 {
        let joined = raw[i..j].join(", ");
        let key = joined.strip_prefix("and ").unwrap_or(&joined);
        // 末尾の項目は " and 次の句" を含むことがあるので、" and " より前で切った形も試す。
        // ただし切る位置は最後の ", " より後ろに限る。手前で切れると、ひとつ前の項目の一部
        // （"values tranquility and a peaceful day" の "values tranquility"）が辞書にあるだけで
        // 次の項目まで1つにまとめてしまい、まとめた全体が訳せずに列ごと英語のまま残る
        let last_comma = key.rfind(", ").map_or(0, |p| p + 1);
        let found = crate::translator::lookup_term(key).is_some()
          || key
            .match_indices(" and ")
            .any(|(k, _)| k > last_comma && crate::translator::lookup_term(&key[..k]).is_some());
        if found {
          break;
        }
        j -= 1;
      }
      pieces.push(raw[i..j].join(", "));
      i = j;
    }
    for piece in &pieces {
      let piece = piece.as_str();
      let piece = piece.strip_prefix("and ").unwrap_or(piece);
      // 辞書の完全一致 → " and " で分ける → 1項目として訳す、の順。
      // 分ける前にテンプレートで訳すと、"respects power and does not …" が「respects power」に後ろごと飲み込まれる
      if let Some(ja) = crate::translator::lookup_term(piece) {
        any = true;
        out.push(ja);
        continue;
      }
      let mut done = false;
      let idx: Vec<usize> = piece.match_indices(" and ").map(|(i, _)| i).collect();
      for &i in idx.iter().rev() {
        let (l, r) = (&piece[..i], &piece[i + 5..]);
        let (lj, rj) = (self.value(l, depth + 1), self.value(r, depth + 1));
        // 片方に英語が残る分け方は採らない。"A and B and A and B" のように同じ句が繰り返される傷の列挙では、
        // 後ろから分けると「A and B and A」が丸ごと1つの傷として飲み込まれて語順が崩れるため、
        // 英語が残らない分かれ目が見つかるまで試す
        if lj != l && rj != r && crate::translator::fully_translated(&lj) && crate::translator::fully_translated(&rj) {
          any = true;
          out.push(lj);
          out.push(rj);
          done = true;
          break;
        }
      }
      if done {
        continue;
      }
      let ja = self.value(piece, depth + 1);
      if ja != piece {
        any = true;
        out.push(ja);
        continue;
      }
      // " and " の位置で2つに分け、片方が名前でもよい分け方を探す（後ろから）
      let idx: Vec<usize> = piece.match_indices(" and ").map(|(i, _)| i).collect();
      for &i in idx.iter().rev() {
        let (l, r) = (&piece[..i], &piece[i + 5..]);
        let (lj, rj) = (self.value(l, depth + 1), self.value(r, depth + 1));
        if ok(l, &lj) && ok(r, &rj) && (lj != l || rj != r) {
          any = true;
          out.push(lj);
          out.push(rj);
          done = true;
          break;
        }
      }
      if !done {
        if !name_like(piece) {
          return None;
        }
        out.push(piece.to_owned());
      }
    }
    (any && out.len() >= 2).then(|| out.join("、"))
  }

  /// テンプレートでも完全一致でも訳せない文の、最後の手当て
  /// - 色の指定で囲まれた見出し（"[C:1:0:1]Related Entities[C:7:0:0]"）は、中身を辞書で引く
  /// - 「何か (関係)」（"[LPAGE:ENT:16]Jrilmus[/LPAGE] (enemy)"）は、括弧の中を辞書で引き、前を差し込み値として訳す
  fn translate_fallback(&self, s: &str) -> Option<String> {
    static COLORED: OnceLock<Regex> = OnceLock::new();
    static PAREN: OnceLock<Regex> = OnceLock::new();
    let colored = COLORED.get_or_init(|| Regex::new(r"^(\[C:\d+:\d+:\d+\])([^\[]+?)(\[C:\d+:\d+:\d+\])$").unwrap());
    let paren = PAREN.get_or_init(|| Regex::new(r"^(.*\S) \(([a-z][a-z ]*)\)$").unwrap());
    let t = s.trim();
    // 先頭に色の指定だけが付いた語（健康画面の ".[C:4:0:1]Overlapping fracture"）。
    // 色の番号は程度ごとに変わるので、色を外した語で引く
    static LEADING: OnceLock<Regex> = OnceLock::new();
    let leading = LEADING.get_or_init(|| Regex::new(r"^(\.?)(\[C:\d+:\d+:\d+\])(\.?)([^\[]+)$").unwrap());
    if let Some(c) = leading.captures(t) {
      if let Some(ja) = crate::translator::lookup_term(c[4].trim()) {
        let dot = if c[1].is_empty() { "" } else { "。" };
        return Some(format!("{dot}{}{}{ja}", &c[2], &c[3]));
      }
    }
    if let Some(c) = colored.captures(t) {
      let ja = crate::translator::lookup_term(c[2].trim())?;
      return Some(format!("{}{ja}{}", &c[1], &c[3]));
    }
    if let Some(c) = paren.captures(t) {
      let rel = crate::translator::lookup_term(&c[2])?;
      return Some(format!("{}（{rel}）", self.value(&c[1], 0)));
    }
    // 傷の報告は1文に「〜, 〜 and 〜!」と並ぶことがあるが、テンプレートは1つずつしか持っていない
    // （"An artery in the left wing has been opened by the attack, many nerves have been severed and a tendon has been torn!"）。
    // 区切って1つずつ訳し、全部訳せたときだけ「、」でつなぎ直す
    let (body, end) = strip_end(t);
    let mut clauses: Vec<&str> = Vec::new();
    for part in body.split(", ") {
      match part.split_once(" and ") {
        Some((left, right)) => {
          clauses.push(left);
          clauses.push(right);
        }
        None => clauses.push(part),
      }
    }
    if clauses.len() < 2 {
      return None;
    }
    let mut out: Vec<String> = Vec::new();
    for clause in clauses {
      let clause = clause.trim();
      if clause.is_empty() || !clause.is_char_boundary(1) {
        return None;
      }
      // テンプレートの文は大文字で始まるので、頭を大文字にしてから引く
      let upper = format!("{}{}", clause[..1].to_uppercase(), &clause[1..]);
      let ja = self
        .translate_one(&upper, 0, false)
        .filter(|ja| crate::translator::fully_translated(ja))?;
      out.push(ja.trim_end_matches(['。', '！']).to_owned());
    }
    Some(format!("{}{end}", out.join("、")))
  }

  /// 1つの文を訳す。書き出し・本体・後ろの句を1つの正規表現でまとめて照合する（区切りの取り違えを防ぐ）
  fn translate_one(&self, sentence: &str, depth: usize, punct: bool) -> Option<String> {
    let matcher = self.matcher.as_ref()?;
    let (body, end) = if punct { strip_end(sentence) } else { (sentence, "") };
    let mut cands: Vec<usize> = matcher.find_overlapping_iter(body).map(|m| self.keywords[m.pattern().as_usize()]).collect();
    cands.sort_unstable();
    cands.dedup();
    // 文頭が固定の語で始まるテンプレートを先に、その中で固定部分の長い順に試す。
    // 差し込みで始まるもの（"{1} telling of the story of {2}"）は前の文ごと飲み込みやすいので後回し
    // 同じ条件なら手直し（manual）のテンプレートを先に
    // 書き出しが差し込みで始まるグループ（"{1}, " + "early autumn"）の本体も、差し込みで始まるものとして扱う
    cands.sort_by_key(|&i| {
      let core = &self.cores[i];
      let group = &self.groups[core.group];
      let slot_start = core.part.src.starts_with('{') || group.prefixes.iter().any(|p| p.src.starts_with('{'));
      (slot_start, std::cmp::Reverse(core.part.literal_len()), !group.trusted)
    });
    // グループごとに、この文に合いうる書き出し・後ろの句の番号（0 = 無し）
    let mut fits: HashMap<usize, (Vec<usize>, Vec<usize>)> = HashMap::new();
    for ci in cands {
      let core = &self.cores[ci];
      if has_adjacent_slots(&core.part.src) || !core.part.segs_in_order(body, 0, 0, body.len()) {
        continue;
      }
      let group = &self.groups[core.group];
      let (pres, sufs) = fits.entry(core.group).or_insert_with(|| {
        let mut p: Vec<usize> = (0..group.prefixes.len())
          .filter(|&i| !has_adjacent_slots(&group.prefixes[i].src) && group.prefixes[i].fits_start(body))
          .map(|i| i + 1)
          .collect();
        let mut s: Vec<usize> = (0..group.suffixes.len())
          .filter(|&i| !has_adjacent_slots(&group.suffixes[i].src) && group.suffixes[i].fits_end(body))
          .map(|i| i + 1)
          .collect();
        p.push(0);
        s.push(0);
        (p, s)
      });
      // 番号の小さい順 = 固定部分の長い順。最後に「無し」
      for &pi in pres.iter() {
        let pre = (pi > 0).then(|| &group.prefixes[pi - 1]);
        if pre.is_none() && !body.starts_with(core.part.segs[0].as_str()) {
          continue;
        }
        if pre.map(|p| adjacent(&p.src, &core.part.src)).unwrap_or(false) {
          continue;
        }
        for &si in sufs.iter() {
          let suf = (si > 0).then(|| &group.suffixes[si - 1]);
          if suf.is_none() && !body.ends_with(core.part.segs.last().map(|s| s.as_str()).unwrap_or("")) {
            continue;
          }
          // 差し込み同士が隣り合うと区切りが決まらないので、その組み合わせは使わない
          if suf.map(|s| adjacent(&core.part.src, &s.src)).unwrap_or(false) {
            continue;
          }
          let parts: Vec<&Part> = pre.into_iter().chain(std::iter::once(&core.part)).chain(suf).collect();
          if !group.trusted && !enough_literal(&parts, body) {
            continue;
          }
          let rx = {
            let mut cache = self.regexes.lock().unwrap();
            if cache.len() > 50_000 {
              cache.clear();
            }
            cache
              .entry((ci, pi, si))
              .or_insert_with(|| {
                let p = pre.map(|p| pattern(&p.src)).unwrap_or_default();
                let s = suf.map(|s| pattern(&s.src)).unwrap_or_default();
                Regex::new(&format!("^(?s){p}{}{s}$", pattern(&core.part.src))).ok()
              })
              .clone()
          };
          let Some(c) = rx.as_ref().and_then(|r| r.captures(body)) else { continue };
          // 差し込みの値が単語の途中で切れる当てはめは使わない（"{1}{2}" が "T" と "hepani" に分かれるなど）
          // リンク [LPAGE:..]..[/LPAGE] の途中で切れる値も使わない
          if c.iter().skip(1).flatten().any(|m| {
            !on_word_boundary(body, m.start(), m.end()) || m.as_str().matches("[LPAGE").count() != m.as_str().matches("[/LPAGE]").count()
          }) {
            continue;
          }
          let vals: Vec<&str> = c.iter().skip(1).map(|m| m.map(|m| m.as_str()).unwrap_or("")).collect();
          let n_pre = pre.map(|p| p.kinds.len()).unwrap_or(0);
          let n_core = core.part.kinds.len();
          let tr = |v: &str| self.value(v, depth);
          let pre_ja = pre.map(|p| p.render(&vals[0..n_pre], &tr)).unwrap_or_default();
          let suf_ja = suf.map(|s| s.render(&vals[n_pre + n_core..], &tr)).unwrap_or_default();
          let mut main = core.part.render(&vals[n_pre..n_pre + n_core], &tr);
          if main.contains("{REST}") {
            main = main.replace("{REST}", &suf_ja);
          } else {
            main.push_str(&suf_ja);
          }
          // 訳が {REST} の前に文末の記号を持つ（"流れは変わったか？{REST}"）と記号が重なるので、付ける前に外す
          let main = if end.is_empty() { main.as_str() } else { strip_end_ja(&main) };
          return Some(format!("{pre_ja}{main}{end}"));
        }
      }
    }
    None
  }

  /// 文章（複数の文、[B] などのトークンを含んでよい）を訳す。1文でも訳せたら Some
  pub fn translate_text(&self, text: &str) -> Option<String> {
    if self.cores.is_empty() || !text.contains(' ') {
      return None;
    }
    // 戦闘の文の " and the injured part …" / " and the severed part …" は ", the …" に直す。
    // 武器の後ろが ", 傷の列挙" の形だけになり、文テンプレートの差し込みが " and " の位置を取り違えない
    if text.contains(" and the injured part ") || text.contains(" and the severed part ") {
      let fixed = text.replace(" and the injured part ", ", the injured part ").replace(" and the severed part ", ", the severed part ");
      return self.translate_text(&fixed);
    }
    // 戦闘の文の "in the 部位 from behind" / "from the side" は外して訳し、主語の「は」の後ろに「背後から」「横から」を入れる
    for (en, ja) in [(" from behind", "背後から"), (" from the side", "横から")] {
      if text.contains(" in the ") && text.contains(en) {
        let plain = text.replacen(en, "", 1);
        let out = self.translate_text(&plain)?;
        return Some(match out.find('は') {
          Some(p) => format!("{}{ja}{}", &out[..p + 'は'.len_utf8()], &out[p + 'は'.len_utf8()..]),
          None => format!("{ja}{out}"),
        });
      }
    }
    // 会話の記録「話し手: 台詞」（"The farmer Nomal Koganusen: Hello.  It is good to see you."）は、
    // 話し手と台詞を分けて訳し「話し手「台詞」」にする
    if let Some(pos) = text.find(": ") {
      let (who, line) = (&text[..pos], text[pos + 2..].trim());
      // 「話し手 (to 相手)」→「話し手（相手へ）」
      let (speaker, to) = match who.find(" (to ") {
        Some(p) if who.ends_with(')') => (&who[..p], Some(&who[p + 5..who.len() - 1])),
        _ => (who, None),
      };
      // 仕事の取り消し（"Lorbam Bomrekmostib, Stonecrafter cancels Give water: No water source."）は
      // 会話ではないので、話し手として扱わない（文テンプレート `{1} cancels {2}: ` に任せる）
      let name_ok = |s: &str| {
        !s.is_empty() && s.len() <= 60 && !s.contains(['.', '!', '?', '[', '(']) && s.split(' ').count() <= 6 && !s.contains(" cancels ")
      };
      let who_ok = name_ok(speaker) && to.map(name_ok).unwrap_or(true);
      if who_ok && !line.is_empty() && line.contains(' ') {
        let line_ja = self.translate_text(line).or_else(|| crate::translator::lookup_term(line));
        if let Some(line_ja) = line_ja {
          let person = |s: &str| if s == "You" || s == "you" { "あなた".to_owned() } else { self.value(s, 0) };
          let who_ja = match to {
            Some(t) => format!("{}（{}へ）", person(speaker), person(t)),
            None => person(speaker),
          };
          return Some(format!("{who_ja}「{}」", line_ja.trim().trim_end_matches('。')));
        }
      }
    }
    // 全体が "..." で囲まれた台詞は、中身を訳して「」で囲む
    let t = text.trim();
    if t.len() > 2 && t.starts_with('"') && t.ends_with('"') && !t[1..t.len() - 1].contains('"') {
      return self.translate_text(&t[1..t.len() - 1]).map(|ja| format!("「{}」", ja.trim()));
    }
    self.translate_pieces(text, false)
  }

  /// 文章を文ごとに訳す。訳せない文は英語のまま残し、1文も訳せなければ None。
  /// translate_text と違って、訳に英語が残る文は訳さなかったものとして扱う（英語と日本語を文の単位でしか混ぜない）。
  /// ゲームが折り返して1行ずつ描く文章（性格の説明など）で、訳の無い文が1つあっても残りを訳すために使う
  pub fn translate_sentences(&self, text: &str) -> Option<String> {
    if self.cores.is_empty() || !text.contains(' ') {
      return None;
    }
    self.translate_pieces(text, true)
  }

  fn translate_pieces(&self, text: &str, strict: bool) -> Option<String> {
    static TOKEN: OnceLock<Regex> = OnceLock::new();
    static SENT: OnceLock<Regex> = OnceLock::new();
    // 段落・改行などの区切りトークンで分ける。色の変更 [C:..]、リンク [LPAGE:..]、キー表示 [KEY:..] は文の一部として残す
    let token = TOKEN.get_or_init(|| Regex::new(r"\[(?:B|P|R|/?CHAR[^\]]*)\]").unwrap());
    // 文末の記号の直後の閉じ引用符も文に含める（"... said, "Are you going to eat that?""）
    let sent = SENT.get_or_init(|| Regex::new(r#"[^.!?]+(?:[.!?]+[")]*|$)\s*"#).unwrap());
    let mut out = String::new();
    let mut any = false;
    let mut last = 0;
    let mut pieces: Vec<(bool, &str)> = Vec::new();
    for m in token.find_iter(text) {
      pieces.push((false, &text[last..m.start()]));
      pieces.push((true, m.as_str()));
      last = m.end();
    }
    pieces.push((false, &text[last..]));
    for (is_token, piece) in pieces {
      if is_token {
        out.push_str(piece);
        continue;
      }
      // "etc." の後ろでは文を区切らない（"When flying, use [KEY:..] etc. and[KEY:..] etc. to change altitude."）
      //   後ろが小文字（文の続き）のときだけ。"etc.  If you want …" のように大文字で始まれば次の文
      static ETC: OnceLock<Regex> = OnceLock::new();
      let etc = ETC.get_or_init(|| Regex::new(r"etc\. ([a-z])").unwrap());
      let protected = etc.replace_all(piece, "etc\u{1} $1");
      for m in sent.find_iter(&protected) {
        let s_owned = m.as_str().replace('\u{1}', ".");
        let s = s_owned.as_str();
        let found = match split_season(s.trim()) {
          Some((plain, year, season)) => self
            .translate_one(&plain, 0, true)
            .map(|ja| ja.replacen(&format!("{year}年、"), &format!("{year}年の{season}、"), 1)),
          None => self.translate_one(s.trim(), 0, true),
        };
        // テンプレートの訳に英語が残るとき（"I am {1}." が "I am not feeling sad right now." を
        // 飲み込むような場合）は、辞書の完全一致のほうを使う。
        // 辞書にも無ければ、訳をあきらめて英文のまま残す。中途半端に訳すと語が元の位置から外れ、
        // 色の指定だけが残った読めない行になるため（ヘルプの途中で切れた文で起きていた）
        let found = match found {
          Some(ja) if !crate::translator::fully_translated(&ja) => {
            crate::translator::lookup_term(s.trim()).filter(|dict| crate::translator::fully_translated(dict))
          }
          other => other,
        };
        // テンプレートで訳せない文は、辞書の完全一致も引く（"I'm very fond." など）。
        // 辞書を先にすると、ゲーム内ガイドで文脈つきのテンプレートより UI 用の訳が優先されてしまう
        let found = found.or_else(|| crate::translator::lookup_term(s.trim())).or_else(|| self.translate_fallback(s));
        let found = found.filter(|ja| !strict || (ja.trim() != s.trim() && crate::translator::fully_translated(ja)));
        match found {
          Some(ja) => {
            out.push_str(&ja);
            any = true;
          }
          None => out.push_str(s),
        }
      }
    }
    // 「〔述〕」は手直しテンプレートで述語の位置に置く印。連体形の訳（「凹状の」）を「凹状だ」にする
    any.then(|| out.replace("の〔述〕", "だ").replace("な〔述〕", "だ").replace("〔述〕", ""))
  }
}

