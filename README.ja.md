# Dwarf Fortress 日本語化プロジェクト

*[English](README.md)*

Dwarf Fortress を日本語で遊べるようにする、非公式のファンメイド日本語化プロジェクトです。
Steam 版（Premium・Windows・**53.17**）を対象にしています。開発元・販売元とは関係ありません。

- サイト（紹介・入れ方）: https://higesho.github.io/df-ja/
- ダウンロード: [DwarfFortress_JP.zip](https://github.com/higesho/df-ja/releases/latest/download/DwarfFortress_JP.zip)（[リリース一覧](https://github.com/higesho/df-ja/releases)）
- ウルティマ シリーズの日本語化: https://higesho.github.io/ultima-ja/
- マイト・アンド・マジック シリーズの日本語化: https://higesho.github.io/mm-ja/

**ゲームのファイルは書き換えません。** `Dwarf Fortress.exe` にも `data\` の中身にも手を加えず、
DLL とデータを置くだけです。外せば英語に戻ります。

## 日本語化の範囲

| 画面 | 状態 |
|---|---|
| タイトル・設定・世界生成・闘技場 | 公開中 |
| 要塞モード（建設・在庫・労働・貴族・交易・知らせ・戦闘の記録） | 公開中 |
| 冒険モード（キャラクター作成・会話・戦闘） | 公開中 |
| 伝説モード（歴史・人物・芸術品） | 公開中 |
| 生き物・品物・材質・建物の名前 | 公開中（組み立てて訳します） |
| 世界生成で作られる怪物・悪魔・天使の名前 | 公開中 |
| DFHack の表示（操作パネル・建設の計画・隊商の取引） | 公開中 |
| 人名・地名・世界で作られた固有名詞 | 英語のまま（訳す対象がありません） |

## 入れかた

[DwarfFortress_JP.zip](https://github.com/higesho/df-ja/releases/latest/download/DwarfFortress_JP.zip) をダウンロードし、中身を
**Dwarf Fortress のフォルダにそのまま重ねてコピー**するだけです。置く順番は関係ありません。

```
Dwarf Fortress\
  dfhooks.dll           … 橋渡し役
  dfhooks_dfint_ja.dll  … 日本語化の本体
  dfint-data\           … 辞書・フォント・設定
```

**DFHack を使っている場合**は `dfhooks.dll` がすでにあります。**それだけは上書きしないでください。**
残りの2つをコピーすれば動きます。あとから DFHack を入れた場合も、そのまま動きます。

外すときは、置いた3つを消すだけです（DFHack を使っている場合は `dfhooks.dll` を残してください）。

ゲーム中に **Ctrl+F2** で日本語化のオン／オフを切り替えられます。

## ご意見・誤訳の報告

誤訳や不自然な訳、英語のまま残っているところに気づいたら、[Issues](https://github.com/higesho/df-ja/issues) で教えてください。

`dfint-data\config.txt` の `[LOG_LEVEL:Warn]` を `[LOG_LEVEL:Debug]` に変えて遊ぶと、
訳されていない文字列が `dfint-data\dfint-log.log` に残ります。それを貼っていただけると助かります
（ログはゲームを起動するたびに書き直されるので、終える前に取ってください）。

## 翻訳を直したい・別の言語を作りたい

辞書は `translations/` のタブ区切りファイルです。英語と訳を並べて書き、`python tools/build.py`
で組み立て直すだけで反映できます。フォントと辞書を入れ替えれば**日本語以外の言語にも使えます**。

手順は **[docs/translating.md](docs/translating.md)** にまとめてあります。
ゲームを起動せずに訳を確かめる道具も入っています。

## 仕組み

ゲームが文字を描く関数に割り込み、英語の文字列を辞書で引いて日本語に差し替え、
自前のフォントで描き直しています。詳しくは **[docs/architecture.md](docs/architecture.md)**。

```
engine/        描画エンジン（Rust）。ビルドすると dfint_hook.dll
chainloader/   dfhooks.dll を取り合わないための橋渡し役
translations/  翻訳のもと（英語<TAB>日本語）
data/          エンジンが読むデータ（tools/build.py が作る）
tools/         取り出し・組み立て・検査のスクリプト
docs/          仕組みの説明、翻訳版の作り方、紹介ページ
```

### ビルドと配布物

Rust（rustup）、Visual Studio の C++ ビルドツール、Python 3.10 以上が必要です。

```powershell
python -I -X utf8 tools/build.py                                  # translations/ -> data/
cd engine; cargo build --release; cd ..                           # 本体
cd chainloader; cargo build --release; cd ..                      # 橋渡し役
powershell -ExecutionPolicy Bypass -File .\install.ps1            # ゲームフォルダへ
powershell -ExecutionPolicy Bypass -File .\tools\package.ps1 -Build   # 配布用 zip
```

## クレジット・権利

- 描画エンジンは [dfint/df-steam-hook-rs](https://github.com/dfint/df-steam-hook-rs)（MIT）と、
  その簡体字中国語版 [dfint-rust-cjk](https://gitee.com/vizv/dfint-rust-cjk)（MIT）を元に、
  日本語向けに作り替えたものです。
- フォントは [Noto Sans Mono CJK JP Bold](https://github.com/notofonts/noto-cjk)（SIL Open Font License 1.1）。
- UI の原文は [dfint/translations-backup](https://github.com/dfint/translations-backup) が公開している一覧を参照しています。
- 用語は [Dwarf Fortress 日本語Wiki](https://wikiwiki.jp/dwarffort/) の訳語に合わせています。
- このリポジトリは MIT ライセンスです（[LICENSE](LICENSE)）。
- Dwarf Fortress の原文および画面に写っている内容の権利は Bay 12 Games / Kitfox Games に帰属します。

非公式のMODです。セーブデータのバックアップを取ってからお使いください。
