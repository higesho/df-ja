# UI 文字列の翻訳ルール（Dwarf Fortress 日本語化）

バッチ（JSON の文字列の配列）は、ゲームの実行ファイルにある英語の文字列です。ゲームはこの文字列を**そのまま画面に表示**し、
日本語化 MOD が完全一致で日本語に置き換えます。各文字列を日本語にしてください。

## 出力の形式

1行に1件、タブ区切りで2列。見出し行や説明は書かない。

```
英語（バッチの文字列をそのまま）<TAB>日本語
```

- 英語の列は**一字一句そのまま**（大文字小文字、前後や途中の空白、記号も含めて）。変えると照合できなくなります。
- バッチの**すべての文字列**を出力する（1件も飛ばさない）。
- 次のような、プレイヤーに見せるものではない文字列は、日本語の列に `-` だけを書く（訳さない）。
  - プログラムの内部名・デバッグ用・エラーメッセージの断片（例: `exec generic`, `Failed to find machine node frontier on split`, `no ambiance layer found by ambiance`）
  - raw ファイルのタグ（例: `[REAGENT:thread:15000:THREAD:NONE:NONE:NONE]`）
  - 1〜2文字の意味のない断片（例: `st`, `nd`）

## トークン

次のトークンは、日本語にも**同じものを同じ数だけ**入れる（中身を変えない、訳さない）。位置は日本語の語順に合わせて動かしてよい。

- 色の指定 `[C:7:0:1]` など（`[C:` で始まる）。色を付けている語の訳を同じ色で囲む:
  `First you need [C:6:0:1]Wood[C:7:0:0].` → `まず[C:6:0:1]木材[C:7:0:0]が必要です。`
- 段落・改行の `[B]` `[P]` `[R]`、キー表示 `[KEY:...]` などの `[...]` 全般
- `%d` `%s` `%i` `%f` `{...}`

## 文体

- メニュー・ボタン・見出し・項目名: 短い体言止め（`Seek Patient for Diagnosis` → `診断する患者を探す`、`Woodworking` → `木工`）
- 説明文・ヘルプ・操作の案内: です・ます調（`Assign a patrol order.  The soldiers will walk a specified route repeatedly.` → `巡回命令を割り当てます。兵士は指定された経路を繰り返し歩きます。`）
- 登場人物のせりふ（引用符 `"` で囲まれたもの、会話文）: 自然な口語。ドワーフの一人称は「わし」。商人・外交官は丁寧語。敵や怪物は尊大でよい
- 性格・体格・能力の説明（`is skinny and very tall`, `has a very broad body with little fat`, `very good focus`, `tends to be very focused during conversations`）: 主語を補わず、述語だけを自然な日本語にする（`痩せていてとても背が高い`、`とても体格が良いが脂肪は少ない`、`集中力がとても高い`、`会話中はとても集中しがちだ`）。比較の `more ambitious` は `より野心的`
- `the Elements`, `the Questioning` のような固有の題名・概念名は、`the` を訳さずに名詞として訳す（`元素`、`問い`）
- 行末の `: ` や `. ` などの記号と空白は残す（`Strongest Odor: ` → `最も強い匂い: `）。文末の `.` は `。`、`!` は `！`、`?` は `？`
- 文の途中の `.  `（ピリオドと空白2つ）は文の区切り。日本語では `。` にして空白は入れない
- 半角カタカナは使わない。英数字は半角のまま

## 用語

迷ったら、既存の訳に合わせる。`translations/ui.tsv` と `data/simple-dictionary.csv`（英語,日本語）を検索してよい。
よく出る語: dwarf=ドワーフ、fortress=要塞、outpost=前哨地、caravan=キャラバン、stockpile=備蓄庫、workshop=工房、
squad=小隊、burrow=区画、noble=貴族、mayor=市長、militia=民兵、artifact=アーティファクト、forgotten beast=忘れられし獣、
megabeast=巨大獣、goblin=ゴブリン、elf=エルフ、kobold=コボルド、legends=伝説、civilization=文明、site=拠点
