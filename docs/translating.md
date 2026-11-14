# 翻訳版の作り方

このMODは「ゲームが文字を描く関数に割り込んで、英語を辞書で引いて差し替える」だけの作りです。
辞書とフォントを入れ替えれば**日本語以外の言語にも使えます**。この文書は、

- 日本語訳を直したい・増やしたい人
- 別の言語の翻訳版を作りたい人

の両方に向けた手順です。仕組みそのものは [architecture.md](architecture.md) を見てください。

---

## 1. 必要なもの

| もの | 用途 |
|---|---|
| Dwarf Fortress（Steam版・Windows・53.17） | 原文の取り出しと動作確認 |
| Rust（rustup。`engine/rust-toolchain.toml` で版が決まる） | エンジンのビルド |
| Visual Studio の C++ ビルドツール（MSVC） | 同上 |
| Python 3.10 以上 | 辞書を組み立てるスクリプト |
| 等幅の OpenType/TrueType フォント | 文字の描画 |

```powershell
git clone <このリポジトリ> dfint-ja
cd dfint-ja\engine
cargo build --release          # engine/target/release/dfint_hook.dll
cd ..\chainloader
cargo build --release          # chainloader/target/release/dfhooks.dll
```

---

## 2. 原文を取り出す

辞書の「英語」側は、ゲームから取り出します。

```powershell
# raw ファイルの名前（生き物・植物・材質・品物・反応…）
python -I -X utf8 tools/extract_raws.py      # -> work/raw_terms.csv
```

実行ファイルの中の UI 文字列は、[dfint/translations-backup](https://github.com/dfint/translations-backup)
が公開している一覧（`hardcoded_steam` の英語原文）を使っています。

ゲームが世界生成のときに**組み立てる**名前（夜の生き物、悪魔、天使、神話の材質）は、
raw には無く `data/vanilla/vanilla_procedural/scripts/generators/` の Lua に語彙があります。
`translations/procgen-names.tsv` がその語彙の訳で、組み合わせは `tools/build.py` が作ります。

DFHack の文字列は `tools/dfhack_extract.py` で集めます（DFHack の置き場所はスクリプトの先頭で指定）。

---

## 3. 辞書を書く

`translations/*.tsv` は**タブ区切りの2列**（英語 → 訳）です。`#` で始まる行はコメント。

| ファイル | 中身 |
|---|---|
| `ui.tsv` | 実行ファイル内の UI 文字列 |
| `terms.tsv` | raw 由来の名前（生き物・植物・材質・品物） |
| `overrides.tsv` | 手で直した訳（**最優先**） |
| `paragraphs.tsv` | 長い文章（ポップアップ・説明文）。英文全体 → 訳文 |
| `sentences.tsv` / `sentences-fix.tsv` | 文テンプレート（4列：group / kind / 英語 / 訳） |
| `combat.tsv` | 戦闘の文（`tools/combat_templates.py` が作る） |
| `procgen-names.tsv` | 世界生成で組み立てられる名前の部品（3列：分類 / 英語 / 訳） |
| `dfhack.tsv` | DFHack が出す文字列 |

### 守ること

- **トークンは原文と同じだけ入れる**。`[C:7:0:0]`（色）、`%s` `%d`（差し込み）、`{1}`（文テンプレートの差し込み）。
  数が合わない行はビルド時に弾かれ、`work/rejected.tsv` に出ます。
- **訳が英語と同じ行は入りません**（`build.py` が落とします）。記号だけの語（`♂` など）は
  エンジン側で素通しするようになっています。
- 画面の幅はゲームが**英語の文字数**で決めるので、訳が長いとはみ出します。短く書いてください。

### 組み立て型のルックアップ

「材質 + 品物」「生き物 + 部位 + 材質」のような組み合わせは、全部を辞書に書くと爆発するので、
`data/lookups/*.csv` という**組み立ての表**を `build.py` が作ります。

```
table,text,translation
ITEM,{:MATERIAL} {:ITEM:NOUN},{:MATERIAL}の{:ITEM:NOUN}
```

`{:XXX}` は別の表を引く場所です。表どうしは参照できますが、**自分自身は参照できません**
（止まらなくなります）。組み合わせの定義は `tools/build.py` の `write_csv(lookups / ...)` のあたり。

---

## 4. 組み立てて入れる

```powershell
python -I -X utf8 tools/build.py        # translations/ -> data/
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

`install.ps1` はゲームフォルダに次の3つを置きます（ゲームのファイルは触りません）。

```
dfhooks.dll           橋渡し役
dfhooks_dfint_ja.dll  本体
dfint-data\           辞書・フォント・設定
```

---

## 5. 訳せているか確かめる

ゲームを起動せずに、**実エンジンで**確かめられます。

```powershell
cd engine
cargo build --release --features offline --bin dfint-check
cd "<ゲームフォルダ>"
dfint-ja\engine\target\release\dfint-check.exe < names.txt    # 英語<TAB>訳 が返る
```

```powershell
python -I -X utf8 tools/check.py            # work/check/*.txt を訳して前回と比べる
python -I -X utf8 tools/check.py --update   # 控えを更新
python -I -X utf8 tools/check.py --miss     # 訳せなかった行を並べる
```

調べる文字列は DFHack で吸い出すのが早いです（`dfhack.items.getReadableDescription` などを
`dfhack.df2utf()` に通してファイルへ）。もう一つの出どころが、遊んだあとの
`dfint-data/dfint-log.log` の `missing translation` 行です（`config.txt` の `LOG_LEVEL` を
`Debug` にしておくこと）。

---

## 6. 別の言語に差し替える

このMODは日本語専用の作りにはなっていません。次を入れ替えれば他の言語でも動きます。

1. **フォント** — `dfint-data/fonts/` に置き、`config.txt` の `[FONT_FILE:...]` で指定。
   全角（2マス幅）で描くかどうかは `engine/src/encodings/cjk.rs` の判定で決まります。
   ラテン文字だけの言語なら、ここを触らなくてもそのまま描けます。
2. **辞書** — `translations/*.tsv` の訳の列を入れ替える。英語の列はそのまま使えます。
3. **折り返し** — `engine/src/wrap.rs` が日本語の禁則処理（行頭に来てはいけない字）を持っています。
   単語の途中で折れない言語では、ここを書き換えてください。
4. **文テンプレート** — `translations/sentences*.tsv` の訳は語順を自由に変えられます
   （`{1}` などの番号さえ合っていればよい）。述語の位置に `{REST}` を1つ入れる決まりは
   日本語の語順のためのものです。詳しくは `tools/sentences/INSTRUCTIONS.md`。

エンジン側で言語に依存しているのは、だいたいこの4か所だけです。

---

## 7. ゲームが更新されたら

関数の位置（`data/offsets.txt`）が変わるので、`docs/architecture.md` の
「5. ゲームが更新されたときの手順」に従って作り直します。
文字列そのものはあまり変わらないので、辞書はたいてい流用できます。
