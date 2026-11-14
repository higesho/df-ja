# dfint-ja — Dwarf Fortress 日本語化MOD

Steam 版 Dwarf Fortress（Premium, Windows, **53.17** 向け）の画面表示を日本語にするMODです。
ゲームが文字を描画する関数をフックし、英語の文字列を辞書で日本語に置き換え、漢字・かなを TrueType/OpenType フォントから描画します。

- 描画エンジン: [dfint-rust-cjk](https://gitee.com/vizv/dfint-rust-cjk)（Viz 氏による簡体字中国語化。MIT）をフォークし、日本語向けに調整
  - 元は [dfint/df-steam-hook-rs](https://github.com/dfint/df-steam-hook-rs)（MIT）
- フォント: [Noto Sans Mono CJK JP Bold](https://github.com/notofonts/noto-cjk)（SIL OFL 1.1）
- 翻訳: このリポジトリで新規に作成（`translations/`）

> **注意**: 実行ファイルに DLL を読み込ませる非公式MODです。セーブデータは必ずバックアップしてください。ゲームの更新で動かなくなることがあります。

## 構成

```
dfint-ja/
  engine/          描画エンジン（Rust）。ビルドすると target/release/dfint_hook.dll
  translations/    翻訳ソース（英語<TAB>日本語）
    ui.tsv           実行ファイル内の UI 文字列
    terms.tsv        raw ファイル由来の名前（生物・植物・素材・アイテムなど）
    harvested.tsv    プレイ中にログから集めた未翻訳文字列の訳
    overrides.tsv    手で直した訳（最優先）
    paragraphs.tsv   文章（ポップアップや説明文）の訳。英文全体<TAB>訳文
    wiki-terms.tsv   日本語Wiki（wikiwiki.jp/dwarffort）の訳語。用語単体の訳として2番目に優先
    term-rules.tsv   既存の訳をWikiの訳語に置き換える規則（tools/apply_terms.py が使う）
    procgen-names.tsv 世界生成で組み立てられる名前の部品（夜の生き物・悪魔・天使・神話の材質）
    dfhack.tsv       DFHack が出す文字列（tools/dfhack_extract.py で集める）
  data/            エンジンが読むデータ（tools/build.py が生成。config.txt と offsets.txt は手書き）
  fonts/           日本語フォント
  tools/           抽出・生成用スクリプト（Python 3.10+）
  docs/glossary.md 用語集と翻訳方針
  docs/architecture.md 日本語化の仕組みと、ゲーム更新時の追随手順
  docs/mod-translation.md MOD に日本語訳を同梱する方法（MOD 作者・翻訳者向け）
  tools/re/        実行ファイルの解析スクリプト（文の部品の取り出し、パターン作成）
  tools/sentences/ 文テンプレートの準備・検査・引き継ぎ・確認
  install.ps1      ゲームフォルダへのインストール／アンインストール
```

ゲームフォルダに置かれるのは次の3つだけです。ゲームのファイル（`Dwarf Fortress.exe`、`data\` の中身）には一切手を加えません。

```
dfhooks.dll           橋渡し役（同じフォルダの dfhooks_*.dll をすべて読み込む）
dfhooks_dfint_ja.dll  日本語化の本体
dfint-data\           辞書・フォント・設定
```

## インストール

配布物（zip）をゲームフォルダに**そのまま重ねてコピー**するだけです。置く順番も、DFHack の有無も関係ありません。

DFHack を使っている場合は `dfhooks.dll` がすでにあるので、**それだけは上書きしない**でください（残り2つで動きます）。

開発中は `install.ps1` がビルド結果を同じ形に並べ直します（必須ではありません）。

```powershell
cd "L:\SteamLibrary\steamapps\common\Dwarf Fortress\dfint-ja"
powershell -ExecutionPolicy Bypass -File .\install.ps1            # インストール／更新
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Uninstall # アンインストール
```

- ゲーム中に **Ctrl+F2** で日本語化のオン／オフを切り替えられます。
- **DFHack と併用できます**。DFHack 自身の画面もほとんど日本語になります（操作パネル、建設の計画、隊商の取引など）。タブの見出しとツール名は英語のままです。詳しくは `docs/architecture.md` の「DFHack との併用」。

## 配布物を作る

```powershell
powershell -ExecutionPolicy Bypass -File .	ools\package.ps1 -Build
```

`dist\dfint-ja-<版>.zip` ができます（`-Build` を付けると engine・chainloader・`tools/build.py` も走ります）。
版は `engine/Cargo.toml` の `version`。`-Version` で上書きできます。

## 訳せているか確かめる

ゲームを起動せずに、実エンジンで翻訳を確かめられます。

```powershell
cd engine; cargo build --release --features offline --bin dfint-check   # 検査用の実行ファイル
cd "L:\SteamLibrary\steamapps\common\Dwarf Fortress"                  # dfint-data を読むのでゲームフォルダで
dfint-ja\engine	argetelease\dfint-check.exe < names.txt            # 英語<TAB>訳 が返る
```

```powershell
python -I -X utf8 tools/check.py            # work/check/*.txt を訳して前回と比べる（回帰テスト）
python -I -X utf8 tools/check.py --update   # 比較用の控えを更新
python -I -X utf8 tools/check.py --miss     # 訳せなかった行を並べる
```

`tools/sentences/test.py` は文テンプレートだけを Python で再現したものなので、品物名のように組み立て型のルックアップを使うものは測れません。網羅を見るのは `check.py` のほうです。

## 翻訳を増やす流れ

1. `dfint-data/config.txt` の `LOG_LEVEL` を `Debug` にしてゲームを遊ぶ（未翻訳の文字列がログに残ります）
2. `python tools/harvest_missing.py` → `work/missing.tsv` に未翻訳の一覧ができる（多く出たものから順に並ぶ）
3. 2列目に訳を書き、その行を `translations/harvested.tsv` に追記する
4. `python tools/build.py` で `data/` を作り直し、`install.ps1` で反映

訳の直しは `translations/overrides.tsv` に書くと、他より優先されます。トークン（`[C:7:0:0]` `%s` など）が原文と一致しない訳は、ビルド時に除外されて `work/rejected.tsv` に出ます。

## 開発

### エンジンのビルド

- Rust（rustup, nightly。`engine/rust-toolchain.toml` で自動選択）
- Visual Studio の C++ ビルドツール（MSVC）
- SDL2 のインポートライブラリ `engine/lib/SDL2.lib` は、ゲーム同梱の `SDL2.dll` から生成済み（`dumpbin /exports` → `lib /def`）

```powershell
cd engine
cargo build --release
```

### 原文の取得

- raw ファイルの名前: `python tools/extract_raws.py` → `work/raw_terms.csv`
- UI 文字列: dfint プロジェクトが公開している実行ファイルの文字列一覧（[dfint/translations-backup](https://github.com/dfint/translations-backup) の `hardcoded_steam` の英語原文）から、画面に出そうな完全な文を選んだもの

### 本家からの変更点（engine/）

- メッセージ・ログを日本語化、既定フォントを Noto Sans Mono CJK JP に変更
- 辞書 CSV が無い／壊れた行があってもクラッシュせず読み飛ばすよう修正
- `user-lookup.csv` のパスの不具合を修正し、ルックアップを名前順に読み込むよう変更
- `data/no-translate-callers.txt` に書いた呼び出し元からの文字列は訳さない（文章を単語ごとに描く箇所で、英語と日本語が混ざるのを防ぐ。`config.txt` の `[NO_TRANSLATE_CALLER:...]` でも追加できる）
- **文章の日本語化**（`src/paragraph.rs`）: ゲームは長い文章を単語の配列に分け（markup_process_string）、幅に合わせて並べ（markup_format）、単語ごとに描く。この2つの関数をフックして、
  - 英文全体に訳があれば（`translations/paragraphs.tsv`）、訳文を1文字ずつの単語に分けてゲームに渡す
  - 並べ終わった後、日本語の字幅（1.5マス）で並べ直し、同じ行・同じ色の字を1つにまとめて描く
  - 名前などが変わる部分は `{1}` `{2}` … で書く（辞書にある語は訳して埋め込む）
  - 訳の無い文章は、ログに「missing paragraph translation」と出る（`tools/harvest_missing.py` が `work/missing-paragraphs.tsv` に集める）
- 呼び出し元が "the" "to" "you" などを1語だけで描いたら、文章を単語ごとに描いている箇所と判定して、以後その呼び出し元は単語単位の訳をしない（ログに「検出」と出る。訳の無い文章が英語と日本語の混ざった状態になるのを防ぐ）
- 数字を含む文字列は、数字を `%d` に置き換えた形で辞書を引く（`Year %d` → `%d年`）。無ければ「ラベル + 数字」のラベルだけを訳す
- `data/context-dictionary.csv`（caller,text,translation）で、同じ英語を呼び出し元ごとに訳し分けられる（並べ替えの見出し "Cat" は「分類」、動物の "Cat" は「猫」）

## ライセンス

- エンジン（`engine/`）: MIT（Copyright shevernitskiy, Viz。`engine/LICENSE`）
- フォント（`fonts/`）: SIL Open Font License 1.1（`fonts/OFL-LICENSE.txt`）
- 翻訳データ・スクリプト: このMODで新規に作成。Dwarf Fortress の原文の権利は Bay 12 Games / Kitfox Games に帰属します。
