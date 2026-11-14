//! 翻訳の抜けを探すための検査用コマンド。
//!
//! ゲームを起動せずに翻訳器だけを動かす。標準入力の1行を1つの文字列として訳し、
//! 「英語<TAB>訳」をタブ区切りで出す。訳せなかった行は訳の欄が英語のままになる。
//!
//! 使い方（ゲームフォルダで実行する。dfint-data を読むため）:
//!   engine で cargo build --release --features offline --bin dfint-check
//!   ゲームフォルダで dfint-ja/engine/target/release/dfint-check.exe < names.txt
//!
//! 第1引数で呼び出し元の種類（addst / wrap_lines など）を変えられる。既定は addst。
//! 呼び出し元の番地（bt）はゲームの中のものなので空にしてある。
//! そのため「訳さない呼び出し元」と中央揃えはここでは再現しない

use std::io::{Read, Write};

fn main() {
  let func: &'static str = match std::env::args().nth(1).as_deref() {
    Some(f) => Box::leak(f.to_owned().into_boxed_str()),
    None => "addst",
  };
  // 1行でも壊れた文字があると止まらないように、まとめて読む
  let mut buf = Vec::new();
  let _ = std::io::stdin().read_to_end(&mut buf);
  let input = String::from_utf8_lossy(&buf).into_owned();
  let stdout = std::io::stdout();
  let mut out = std::io::BufWriter::new(stdout.lock());
  let mut translator = dfint_hook::translator::Translator::default();
  // 「文章」（ゲームが単語ごとに折り返して描くテキスト。ヘルプやチュートリアル）は
  // 単語辞書を通らないので、別の経路で引く
  let as_paragraph = func == "paragraph";
  for line in input.lines() {
    let line = line.trim_end_matches('\r');
    if line.is_empty() {
      continue;
    }
    let text: String = if as_paragraph {
      dfint_hook::paragraph::PARAGRAPHS
        .read()
        .translate_only(line)
        .unwrap_or_else(|| line.to_owned())
    } else {
      translator.translate(func, line, "").0.to_owned()
    };
    let _ = writeln!(out, "{line}\t{text}");
  }
}
