# dfint-ja の仕組みとバージョンアップへの追随手順

この文書は、日本語化がどう動いているか、ゲームが更新されたときに何を確かめて何を作り直すかの記録です。
記載のアドレスや値は **53.17（Steam, Windows）** のものです。

## 1. 全体像

```
Dwarf Fortress.exe ──(起動時に読み込む)── dfhooks.dll（engine/ をビルドしたもの）
                                             │ バイト列のパターンで関数を探してフック
                                             ▼
   ゲームの描画・文章処理の関数 ──→ エンジンが英語を日本語に置き換える ──→ フォントで描画
                                             ▲
                       dfint-data/（辞書・テンプレート・設定。tools/build.py が data/ に生成）
```

ゲームフォルダに置くのは `dfhooks.dll`（DFHack と併用するときは `dfhooks_dfint_ja.dll`）と `dfint-data/` の2つだけです（`install.ps1`）。

**方針: ゲームのファイルは変更しない。** 実行ファイル（`Dwarf Fortress.exe`）や `data/vanilla` の raw などゲーム本体のファイルには一切手を加えず、翻訳はすべて DLL のフックでメモリ上で行います。訳・設定・フォント・ログは `dfint-data/` に置き、他の MOD の訳は各 MOD のフォルダから読むだけです。アンインストールはこの2つを消すだけで元に戻ります。新しい機能もこの方針に従ってください。

## 2. フックする関数

`data/offsets.txt` の `[PATTERN:名前:バイト列]` で探します（`??` は任意の1バイト）。どれも実行ファイル内で**ちょうど1か所**に一致しなければなりません。

| パターン名 | 役割 | エンジン側 |
|---|---|---|
| ADDST / ADDST_FLAG / TOP_ADDST | 1つの文字列を画面に書く（通常の画面 / 上に重なる画面） | `hooks.rs` → 翻訳して自前のフォントで描き、ゲームには同じ幅の空白を渡す |
| DRAW_NINESLICE / DRAW_HORIZONTAL_NINESLICE | 枠の描画 | 枠の下に文字を描かないための記録 |
| GPS_ALLOCATE / UPDATE_ALL / UPDATE_TILE | 画面サイズの変更・描画の確定 | 自前の文字をまとめて描画 |
| MARKUP_PROCESS_STRING | 長い文章を「マークアップ文章」（単語の配列）に変換する（53.17 では RVA 0xd69ba0） | `paragraph.rs` → 訳文に差し替えてから変換させる |
| MARKUP_FORMAT | マークアップ文章を幅に合わせて並べる（RVA 0xd69970） | `paragraph.rs` → 日本語の字幅で並べ直す |
| ADDCOLOREDST | `graphicst::addcoloredst(str, colorstr)`。1文字ごとに色を変えて描く（RVA 0xaf3230）。ユニット画面の思考・性格の行（"He felt fondness talking with a friend."）はこれで1文ずつ描かれる | `hooks.rs` → 文全体を訳して描く。英文で地の色と違う色の語（感情の語など）は、辞書の訳が訳文にあれば同じ色にする |
| WRAP_LINES | 文字列を幅で折り返して `std::string*` の vector に行を追加する（RVA 0x900dc0、引数 out, src, 幅）。1226 か所から呼ばれる。ユニット画面の台詞などは毎フレームこれで折り返してから1行ずつ addst で描く | `wrap.rs` → 訳文を日本語の字幅で折り返し、ゲームには「行ごとに1語になる仮の文字列（0xFF の並び）」を渡して同じ数の行を作らせる。作られた行の string を記録し、addst / addcoloredst で日本語に差し替える |
| TOOLTIP_INIT | 起動時にボタンなどの説明文 609 件を WRAP_LINES で行に分けて保存する関数（RVA 0x406c80）。日本語化のフックが付く前に動く | `wrap.rs` → 最初の描画（UPDATE_ALL）で1回だけ、保存先の行の一覧（関数内の `lea rcx,[rip+X]; call WRAP_LINES` の X）を空にして呼び直し、訳文で作り直させる |
| ADD_TILE | `graphicst::add_tile(texpos, …)`。タイル1枚を描く（RVA 0xaf4810）。入植の準備画面のタブの見出しだけは、文字列ではなく1文字ずつこの関数で描かれる | `tabs.rs` → 文字のタイルを空白に差し替えて、続けて描かれた1語を訳し、自前のフォントで描く |

### ゲーム内部の構造（paragraph.rs が使う）

- markup_text_boxst: `+0x00` 単語ポインタの vector（begin/end/cap）、`+0x30` 幅（マス）、`+0x34` 最大行
- markup_text_wordst: `+0x00` std::string、`+0x20` 色（3バイト）、`+0x24` リンク番号（i32、-1 = なし。リンクの色は描画時に付く）、`+0x28` x、`+0x2c` y、`+0x30` フラグ（1 改行、2 段落の区切り、4 字下げ）
- gps 関連のオフセットは `offsets.txt` の `[OFFSET:...]`

## 3. 文字列が日本語になるまで

### 3.1 1行の文字列（addst 系）

`translator/mod.rs` が次の順に試します（結果は呼び出し元＋文字列ごとにキャッシュ）。

1. `no-translate-callers.txt` の呼び出し元、または自動で「文章を単語ごとに描く」と判定した呼び出し元 → 訳さない
2. `context-dictionary.csv`（呼び出し元ごとの訳。同じ英語を場所で訳し分ける）
3. `simple-dictionary.csv`（完全一致。小文字で照合）
4. `lookups/*.csv`（組み立て型。`{:MATERIAL}の{:ITEM:NOUN}` など）
5. 数字入り（数字を `%d` にして辞書を引く／「ラベル＋数字」のラベルだけ訳す）
6. 前後に空白が付いた文字列（`translate_padded`。設定画面の子項目 `" Desired grid width for scaling (default = 170)"` のように行頭に空白が入る）は、空白を残して中身だけ辞書で引く
7. 「ラベル: 値」のラベルだけ訳す（`Lover: Olon` → `恋人: Olon`。`translate_label`）。値は辞書で引き、無ければ文テンプレートでも訳す（全部訳せたときだけ）。ラベルは64文字まで
8. 文テンプレート（`sentence.rs`、3.3）
9. "..." で切れた文字列 → 「The/the 職業 名前」 → 個数の付いた品物 → 「数 品物」 → 「部品/部品」 → 「語 (語)」
10. 「, 」で区切って部品ごとに訳す。英語のまま残る部品が人名・地名らしい（大文字で始まる）ときだけ使う。`visit, along with …` のように英語と日本語が混ざる場合は使わない
11. どれも無ければ英語のまま、ログに `missing translation`

**中央寄せ**（`hooks.rs` の `justify_shift`）。ゲームはボタンの見出しを、枠の幅と**英語の文字数**から描き始めの位置を決めて描く。訳は英語と幅が違う（日本語1文字は英字2つぶん）ので、同じ位置から描くと中央からずれる。直し方は2つ:

- `addst(文字列, 寄せ, 幅)` の**幅が 0 より大きい**ときは、その幅の中で訳を中央・右に寄せ直す
- 幅が 0 のとき（ボタンの見出しはこちら）は、`no-translate-callers.txt` に `^呼び出し元 center` と書いた呼び出し元だけ、**英語の中心に訳の中心を合わせる**。呼び出し元はログの `### "English" @^xxxxx` で分かる。いまは `^1e4f2a`（ゲーム中の Esc メニュー）と `^263d22`（タイトル画面）
- ボタンの枠（nineslice）を覚えておいて中に収める方法も試したが、**メニューのボタンは枠として描かれていなかった**（nineslice はタイトル画面でしか呼ばれない）ので、呼び出し元の名簿にした
- **項目ごとに呼び出し元が違うことがある。** タイトル画面は7つのボタンがそれぞれ別の呼び出し元（`^263a90`〜`^263e1f`）で、`^263d22`（設定）だけ登録していたときは**設定しか直っていなかった**。目で見ると直ったように見えるので、**画面写真の画素を測って確かめること**（ボタンの地色の帯の中心と、文字の中心を比べる）。ゲーム中の Esc メニューは逆に1つの呼び出し元（`^1e4f2a`）で全項目が描かれている
- 背景色の付いた文字（タイトルの副題 `^2602df`）では、**ゲームが塗る背景の帯は英語の幅のまま**で、その中で訳だけが中央に寄る。帯の左右に余白が残って見えるが、直す手立ては無い

`translate_label` を文テンプレートより先に置いているのは、`Nearest site: A day's travel west`（入植地の画面）のように、ラベルが辞書にあるのに後半だけ文テンプレートに当たって「Nearest site「1日の西旅程」」になるのを防ぐため。ラベルの長さの上限（64文字）は `Average Seconds Between Tracks/Interludes (Fortress): ` が入る長さ

補足:
- 3 の辞書引き（`default::get`）も「, 」で区切るが、**全部の部品が引けたときだけ**確定する。一部だけ引けたときは後段（数字入りの日付など）に回す（`1st Granite, early spring, 5` が「1st Granite,初春, 5」になっていた）
- 文テンプレートの差し込み値を辞書で引く `lookup_term` も、数字を `%d` にした形を引く（`1st Granite` → `%dst granite` → 花崗岩の月1日）
- **ゲームが自分で折り返して1行ずつ描く文章**（遊び方の選択画面の説明など。WRAP_LINES を使わず関数の中で折り返している）: 同じ呼び出し元から続けて描かれた未訳の行を `pending` にため、つないだ文が辞書にあれば、訳を英語の行と同じ数に折り返して `line_map` に覚える。次の描画からは行ごとに訳を返す。ログに `折り返された文章 N 行を訳で組み立て直しました`。辞書には**つないだ全文**を入れておく
- 文テンプレートで訳せない文の最後の手当て（`sentence.rs` の `translate_fallback`）: 色で囲まれた見出し `[C:1:0:1]Related Entities[C:7:0:0]` は中身を辞書で引く。`名前 (enemy)` は括弧の中を辞書で引いて「名前（敵）」にする
- 差し込み値の列挙（`hunting, the wind and the sky`）は項目ごとに訳して「、」でつなぐ。全項目が訳せたときだけ
- 先頭が差し込み `{1}` の手直しテンプレート（`{1} titan` など）は、`名前, "あだ名", 種族` の全体に当たって名前ごと飲み込むので作らない。語で始まる形（`male {1} follower of {2}`）にするか、辞書に完全一致で入れる
- 宝石の名前は raw の `[IS_GEM:名前:複数形]` にある（`extract_raws.py` は 53.17 まで拾っていなかった）。訳は `translations/gems.tsv`（「large 〜」→「大きな〜」も入れてある）
- `build.py` は、段落の区切り `[B] [P] [R]` や文の境目（`.  [C:` のように色指定の前で切れていて `prepare.py` が分けなかったもの）をまたぐ本体を、英語と訳の両方で分けて1文ずつの本体も作る（英語の文末と「。」の数が合うときだけ。文末の `{1}` だけの断片は前の文に付ける）。エンジンは区切りと文末で分けてから照合するため、またいだままでは当たらない。ゲーム内ガイド（関数 1f4fb0）の文はこれで訳される
- 前後に空白がある辞書の見出し語（実行ファイルの部品 `"… Workshops[C:7:0:0]. "`）は、空白を落とした形も辞書に入れる（文章の中では文ごとに空白を落としてから引くため）
- 幅に合わせて `...` で切られた文字列（タブの見出し、`名前, expedition...`）は、切られる前の見出し語が辞書に1種類だけあればその訳を使う（`translate_truncated`）
- 同じ英語でも場所で訳を変えたいとき（2行に分けて描く注意書きの2行目 `work orders.` など）は `data/context-dictionary.csv` に呼び出し元つきで書く
- **書き出し（prefix）の末尾の空白は削らない**（`sentence.rs` の読み込み）。53.17 の途中まで本体と同じく削っていたため、「He 」＋「is a nervous wreck」のような書き出しと本体の組み合わせがほとんど当たっていなかった
- 性格の説明の関数（e3eb80）は解析が途中で切れるので、書き出し `He ` `She ` `They ` `It ` `You ` を `sentences-fix.tsv` で足してある。句の多くは「X + 代名詞（関数 14c620 / 14c290）+ Y」でできていて、`work/frag/phrases.py <関数>` で文字列の並びから組み立てられる（53.17 で約220句がテンプレートに無い）
- 折り返して1行ずつ描く文章（冒険者の作成画面の性格・外見など）は、文の終わりで終わる行が来たら、つないだ文を文テンプレートでも訳してみる。英語が残らなかったときだけ行ごとの訳に差し替える（`join_lines` と `fully_translated`）
- **性格・価値観・夢・外見の説明**（冒険者の作成画面、住民の画面）:
  - 句は実行ファイルの関数 e3eb80（性格）、e3c780（価値観・夢）、72b960（外見・けが）にある。`work/frag/persona_extract.py` が代名詞（関数 14c620 / 14c290）を `{N}` にして句を組み立て、訳の無いものを出す
  - 性格の句と葛藤の節は `sentences-fix.tsv` の group e3eb80（節は「。ただ、…」のように句点で始める）。`build.py` が e3eb80 の本体の `{REST}` を文末へ移す
  - 価値観は「Like others in his culture, he A, B, …, and Z.」「He personally A and B.」の手直しテンプレート＋列挙（`value_list`）。列挙は「辞書の完全一致 → " and " で分ける → 1項目として訳す」の順
  - 外見は「His {1} is {2}.」などの手直しテンプレートと、語句の組み立て（`compose_words`: 辞書の語句を左から長い順につなぐ。名詞どうしの間に「の」）。述語の位置の印「〔述〕」は、訳の後で「の〔述〕」「な〔述〕」→「だ」に直す
  - 外見・夢・部位・声などの語句は `translations/persona.tsv`（辞書で最優先の次）。「high」「long」などの短い語も外見向けの訳で上書きしている
  - 文の訳は「テンプレート → 辞書の完全一致」の順のまま。辞書を先にすると、ゲーム内ガイドで文脈つきのテンプレートより UI 用の訳が優先されてしまった。主語つきの完全一致の文（「She has a scratchy voice.」）を使いたいときは、それに当たる汎用テンプレートを作らない
- `build.py` は、差し込みの無い完全な文のテンプレート（末尾の `{1}{2}` は外す）を完全一致辞書にも入れる。末尾に差し込みが続くテンプレートはエンジンが照合に使わないため（「Perhaps some of your friends here can remind you.{1}{2}」）。文の間の空白2つを1つにした形と、1文ずつに分けた形も辞書に入れる（マークアップの文章は空白を1つにまとめる）
- 冒険者の近くの生き物の一覧の方角: 2〜3文字（NNE など）は辞書、1文字（N S E W）は `data/context-dictionary.csv` で関数 b18100 の中の16か所の呼び出し元だけに入れてある（ほかの場所の "N" "S" を巻き込まないため）。バージョンが変わったら呼び出し元を調べ直す
- **冒険者モード**:
  - 会話の記録「話し手 (to 相手): 台詞」は、話し手と台詞を分けて訳し「話し手（相手へ）「台詞」」にする（`translate_text` の先頭）
  - WRAP_LINES の仮の行は、末尾4文字に通し番号を入れて中身でも引けるようにしてある（`wrap.rs` の `placeholder` / `by_bytes`）。会話の選択肢や記録のように、ゲームが行を別の string に写してから描くと、アドレスでは見つからず仮の行（0xFF の並び）がそのまま描かれていた
  - 会話の選択肢のキーワード（呼び出し元 886f7b）は英語のまま。ゲームが英語の長さでキーワードを並べるので、訳や「訳(英語)」を入れると隣と重なる。検索欄も英語でしか打てない。`no-translate-callers.txt` に `^呼び出し元 keyword` と書けば「訳(英語)」で出す仕組みはあるが、使っていない
  - 文の区切りは "etc. 小文字" で切らない（"When flying, use [KEY] etc. and[KEY] etc. to change altitude."）。キー表示 `[KEY:..]` でも切らない
  - "..." で切れた文字列は、文テンプレートで訳して「…」で終える（`strip_end`）
  - 「The 職業 名前」（会話の相手の見出し）→「職業の名前」（`translate_titled_name`）
  - 「the 職業 名前」（小文字の the。攻撃の確認 "Really start a conflict with the farmer …"）も同じく「職業の名前」。文の中の差し込み値 "the Farmer Momu"（幅で切られて名前が1語）も「農家のMomu」
  - 体の部位の名前は `translations/bodyparts.tsv`（raw の `[BP:..]` から集めて Haiku で訳した）
  - 技能の呼び名 "Competent Woodcrafter" は `lookups/skills.csv`（`{:SKILL:NAME}（{:SKILL:LEVEL}）`）。呼び名の一覧は `tools/build.py` の `SKILL_NAMES`（ゲーム本体の呼び名の一覧から足した）
  - 「/」でつないだ攻撃の名前 "hack/iron battle axe" は部品ごとに辞書で引いて「/」でつなぐ（`translate_slashed`）。"Dodge (Adequate)" は括弧の外と中を引いて「回避（十分）」（`translate_parenthesized`）。どちらも全部の部品が訳せたときだけ
  - 攻撃の画面の難しさ（Tricky など）・速さ（Slow など）・当たり方（square）は短い語で、ほかの場所と訳し分けるため `data/context-dictionary.csv` に呼び出し元つきで入れた（関数 893xxx〜894xxx。呼び出し元は「lea で文字列を読む位置 + 0x23」）
  - **戦闘の文**（"The kea bites the stray dog in the left front leg, denting the skin and bruising the fat!"）は1文で addst に来る。`tools/combat_templates.py` が動詞（raw の ATTACK_VERB / ATTACK）ごとに文テンプレートを作り `translations/combat.tsv` に書く（build.py が読む）。訳は「主語は武器で相手の部位を噛みついた（皮膚にへこみ、脂肪に打撲）！」の形で、傷の列挙は括弧にまとめる
    - 実行ファイルから自動で取り出した戦闘の部品（group e6cc0）は質が悪く combat.tsv の邪魔をするので、build.py で外している
    - " and the injured part …" は ", the injured part …" に直してから照合する（武器の差し込みが " and " の位置を取り違えないため）。"in the 部位 from behind / from the side" は外して訳し、主語の「は」の後ろに「背後から」「横から」を入れる（`translate_text` の先頭）
    - 武器が体の部位の "with his first toe, right foot" は、手足の名前ごとにテンプレートを作る（`LIMBS`）。主語が You の "with your iron axe" は「あなたの」を付けない
    - 差し込み値の "his/her/its/their 語" は代名詞を外し、"your 語" は「あなたの語」、"the goblin's iron breastplate" は「ゴブリンの鉄の胸当て」（`value`）
    - 試験: ゲームの `gamelog.txt`（文字コードは cp437）に戦闘の文・会話・出来事の文がそのまま残る。cp437 で読んで重複を除き `tools/sentences/test.py -f` にかける（つかむ・ぶつかる・衝撃で曲がる、などの形もここから足した）
    - 攻撃の画面の相手の様子 "Recovering from attacking you with steel spear" / "Attacking …, aiming for the …" は `sentences-fix.tsv`
  - **ユニットの画面（キャラクターの画面）の性格・価値観・欲求**:
    - 性格の文章は、行末の空白を削った行で1行ずつ来る（"She often feels filled with joy, though she"）。`join_lines` は、行末が文の終わり（. ! ? :）でないか、次の行が小文字で始まれば折り返しの途中とみなし、空白を補ってつなぐ。つなぐ行は最大40行（価値観の段落は19行あった）
    - 価値観の段落 "Like others in her culture, she disdains the law, …, values decorum, dignity and proper behavior and is …" は、句そのものに ", " を含むものがあるので、`value_list` は「辞書にある最も長いつながり」を1項目にしてから訳す（途中の " and " で切った形も辞書と照らす）
    - 価値観の句は自動で作った文テンプレート（group e3c780）が質が悪く列挙を飲み込むので、build.py で外し、辞書（values.tsv）で引く
    - 欲求タブ "She is not distracted after being away from people." は辞書の完全一致（needs.tsv から全組み合わせ）、"…after being unable to pray to {神}." は文テンプレート
    - **段落の最後の行が短いとつなぎ直せなかった**（価値観の段落の最後は `society.` の1行だけ）。`join_lines` の長さの判定は、最後の行ではなく**つないだ文**で見る
    - 特性タブの能力のまとめ "He has a feel for music, but he has a little difficulty with words, …" は `{主語} has {1}, but {代名詞} has {2}.` の形で `sentences-fix.tsv`（訳は「{主語}の長所は{1}。短所は{2}。」）。`{主語} has {1}.` の形は "You have no idea what's lurking out there." のようなふつうの文まで飲み込むので**作らない**
    - 飲酒・屋外作業・心の強さの文（"He needs alcohol to get through the working day." / "He likes working outdoors and grumbles only mildly at inclement weather." / "He is getting used to tragedy."）は、主語（彼・彼女・それ・彼ら・あなた）ごとに `sentences-fix.tsv` に書く
    - **好みタブ**（"Zutthan Ragid likes bauxite, …, guineafowls for their social nature."）は `{1} likes {2}.` / `When possible, {代名詞} prefers to consume {1}.` / `{主語} absolutely detests {1}.` の文テンプレート。一覧の項目が1つでも訳せないと段落ごと英語に戻るので、部品をそろえるのが肝心
      - 「〜ゆえに」は `prefs.tsv`（raw の `[PREFSTRING:..]`）、布は build.py が素材ごとに「〜の布」を辞書に足す、色は `the color {1}` → 「{1}」、世界生成の治癒の素材（"peculiar liquor" → 風変わりな酒）は `materials.lua` の `mythical_healing_*` の組み合わせを overrides.tsv に入れた
    - **健康→説明**の体の特徴のまとめ "He is clumsy, quick to tire, very slow to heal and very flimsy." は、`{主語} is {1}, {2}.` と `{主語} is {1} and {2}.`（主語ごと、`sentences-fix.tsv`）。列挙の差し込みは `value_list` が「、」でつなぐ。`{主語} is {1}.` の形は "He is a legendary miner." のようなふつうの文まで飲み込むので**作らない**（`", "` か `" and "` を含む形だけにする）。一覧の語（"very flimsy" など 47 語）は `ui-extra.tsv`。体言止めで並ぶので、訳の末尾の「な」は落としてある（「脆弱な」→「脆弱」）
    - **思考タブ**の感情の文 "He was angry after getting into an argument." は `thoughts.tsv`（感情の語ごとのテンプレート）。きっかけの句（"after getting into an argument"）は文テンプレートの group e44340 が差し込み値として訳す。思い出にひたる形は `dwelling upon {1}` / `remembering {1}` / `reliving {1}`
    - 癖の文（group 10fbb90、"When she's bored, she often scratches her head"）は、差し込みが全部同じ人の代名詞なので、訳に同じ語が3回出ていた。重なる「{n}が」「{n}の」を落とした形を `sentences-fix.tsv` に入れてある（164件）
  - 頭に個数が付いた品物 "5 pig tail cloth" / "2 copper battle axes"（入植の持ち物の一覧）は `translate_leading_count`。個数を外して訳し「5 ピッグテイルの布」に戻す。複数形で書かれるので、辞書に無ければ最後の語を単数形（`-s` / `-es` / `-ies`→`-y`）に戻して引き直す（`singular_forms`）
  - 品物の個数 "prepared albatross intestines [5]" と文明の名前の付いた硬貨 "Iclopesor gold coins" は `translate_counted`（個数を外して訳し、戻す。先頭の大文字の語は持ち主の名前として「〜の」を付ける）。調理した内臓は lookups の `prepared {:CREATURE} {:MATERIAL:SUFFIX}`
  - 知らせの日付 "Date: 19th Granite, 5" は、ラベル「日付」＋値 `%dth Granite, %d`（`overrides.tsv` に12か月×4通りの序数、訳は「花崗岩の月%d日 %d年」）。**数字は訳文の `%d` に前から順に入る**ので、訳も日→年の順にすること
  - 体や品物に付いた汚れ "water covering"（持ち物の一覧）は、build.py が素材ごとに「〜まみれ」を辞書に足す。素材の表に無いもの（水・雪・泥・吐瀉物など）は `overrides.tsv`
  - 釣りの知らせ "There is nothing to catch in the central swamps." の場所は「the ＋ 方角 ＋ 地形」の組み立て（実行ファイルに方角9語と地形3語が並んでいる）。組み合わせを `overrides.tsv` に入れてある
  - 芸術品・品物の説明（"This is a copper door.  All craftsdwarfship is of the highest quality.  It is studded with copper and encircled with bands of copper.  This object menaces with spikes of copper."）は**1本の文字列**で来る。装飾の言い回しは実行ファイルに6種類（`studded with` / `encrusted with` / `decorated with` / `glazed with` / `encircled with bands of` / `adorned with hanging rings of`）あり、`and` で2つつなぐ形があるので、1つの形と2つの組み合わせ42通りを `sentences-fix.tsv` に入れた。品物のある場所「In 〜」は工房ごとに `overrides.tsv`
  - 「範囲: 0 to 10000」の `" to "` は呼び出し元ごとに `context-dictionary.csv` で「〜」にする（世界生成 `^e1bafd`、設定画面 `^234374`、難易度のカスタム設定 `^22fc0c`）
  - 野良の動物 "Stray Yak Bull"（知らせ・動物の一覧）は、build.py が生き物の名前ごとに「野良〜」を辞書に足す（単数形・複数形の両方）。チーズ・革・骨のような**産物の名前を含むものは外す**（「野良ヤクチーズ」になってしまう）
  - 道を尋ねる一覧 "Ask for the whereabouts of {1}" / "Ask for directions to {1}" は `sentences-fix.tsv`。夜の生き物・悪魔の名前「形容詞 種類」（"shrieking monster" → 金切り声の怪物、"brooding woman" → 陰気な女）は `translations/monster-names.tsv` の部品から build.py が全組み合わせを辞書に足す。部品は `data/vanilla/vanilla_procedural/scripts/generators/creatures.lua` の flavor_adj / night_troll_flavor_adjs / *_names から取った（バージョンが変わったら見直す）
  - 差し込み値: 冠詞を外した形が辞書にあれば最初に使う（"the Gem Setter" が職業名の部品テンプレートに当たって「the宝石はめ込み師」になっていた）。2語の職業名 + 名前（"the Gem Setter Kosoth"）も「職業の名前」
  - 会話の答え（支配者 "{1} rules {2}."、領主 "{1} is lord."、旅の目的 "I'm going to {1} in search of work."、市場・宿屋・依頼 "You must kill {1}." など）は、実行ファイルの会話の部品（0x165e000〜0x1663000 付近）から組み立てを推して `sentences-fix.tsv` に手で書いた。依頼（クエスト）をくれる領主との会話はまだ画面で見ていない
  - 冗談の台詞 "... and the goblins said, "Are you going to eat that?"" のように文末の記号の後ろに閉じ引用符が来る文は、引用符までを1文として区切る（`SENT` の正規表現）
- 照合の順番: 文頭が固定の語で始まるテンプレート（書き出しが差し込みで始まるグループの本体も「差し込みで始まる」扱い） → 固定部分の長い順 → 同じなら手直し（manual）。差し込みで始まるもの（`{1} telling of the story of {2}`）は前の文ごと飲み込みやすいので後回し
- 差し込みの正規表現（`SLOT_PATTERN`）はリンク `[LPAGE:..]…[/LPAGE]` を1かたまりとして扱う。`The Town of Entrancing of The Knives …` の組織名の中の ` of ` で切らないため
- 差し込み値の訳の順番（`value`）: 冠詞がリンクの外にあれば外す → 辞書の完全一致 → 列挙（`value_list`）→ 文テンプレート → 種族名＋名前 → 冠詞（The/A/An も）を外して辞書 → 「名詞's 名詞」 → 所有の代名詞を外す → 語の組み立て。辞書を先に引くのは、`a foot race` が文テンプレート「徒競走を行った」に当たるのを防ぐため
- 種族名（`creature_kind`）: 辞書に無い悪魔・夜の生き物は「動物名＋種類」（`lizard fiend` → トカゲの悪鬼）。名前の先頭が ì などの非 ASCII 文字でも名前とみなす（ゲームが大文字にしない）
- 伝説の画面の確認: ゲームで見たいページを開いた後に `python -I -X utf8 tools/sentences/log_check.py`。ログの段落を文に分けて、試験スクリプトで訳せない文・英語が残る文を出す
- `tools/sentences/test.py` には、色の見出し・括弧・「, 」区切り・lookups（素材＋品物の組み立て）の処理が入っていない。これらはゲームの中でだけ確かめられる
- WRAP_LINES の記録（`wrap.rs`）は、行の一覧が空のときだけ古い記録を消す。1つの一覧に段落を続けて追加する画面（冒険者の説明は3段落）で、前の段落が空白になっていた
- **入植の準備画面（入念に旅の準備をする）のタブの見出し**（ドワーフ／アイテム／動物、重要／労働／戦闘／その他）は、ゲームが文字列ではなく**1文字ずつテクスチャのタイル**として描く（`tabs.rs`）
  - 関数 0x1071450 の中の2ループ（左のタブ 0x10746e2 / 0x10746f5、右のタブ 0x10759c1 / 0x10759d4）だけがこの描き方をする。`std::string::operator[]` で1文字取り出し、グローバル `init` の中の「文字コード → タイル番号」の表（`+0x4e0` 通常 / `+0x8e0` 強調）を引いて `gps.locate(2, x)` の後に add_tile を呼ぶ。文字列を渡す描画関数を通らないので、addst 系のフックからは見えない
  - **実行ファイル全体を走査しても、文字をタイルで描いているのはこの2ループだけ**（`mov edx,[base+char*4+0x4e0/0x8e0]` の並びを探した）。ほかの画面のタブは addst で描かれる
  - `tabs.rs` は起動後の最初の描画で表を逆引きして「タイル番号 → 文字」を作り、add_tile に来た文字のタイルを**空白のタイルに差し替えて**から文字を集める。並びが途切れたら1語として訳し（呼び出し元つきなので context-dictionary でも訳し分けられる）、英語と同じ場所の中ほどに自前のフォントで描く。1文字が2行ぶんの高さで描かれるので、半行ぶん下げて縦の中心を合わせる
  - 訳が無いときは英語のまま自前のフォントで描くので、空欄にはならない。表示設定を変えるとタイル番号が変わるため、GPS_ALLOCATE で読み直す

「呼び出し元」はバックトレースの先頭（例 `^3cfa41` = 戻り先の RVA）。**バージョンが変わると変わる**。

### 3.2 長い文章（マークアップ文章、paragraph.rs）

1. MARKUP_PROCESS_STRING の前で、元の英文を次の順に引く
   - `paragraph-dictionary.csv`（英文全体の訳。`translations/paragraphs.tsv` から生成。`{1}` などの可変部分つきテンプレートも可）
   - 文テンプレート（3.3。文ごとに訳し、訳せない文は英語のまま）
2. 訳があれば、訳文を「1文字 = 1単語」に区切ってゲームに渡す（ゲームの折り返し処理を壊さないため）
3. MARKUP_FORMAT の後で、日本語の字幅（全角 24px = 1.5 マス）で並べ直し、同じ行・同じ色の日本語を先頭の単語にまとめて描く（残りの単語は何も描かない）
4. 描画時（addst）に、渡された単語が記録した単語なら、まとめた文字列を描く
5. 訳の無い文章はログに `missing paragraph translation`（`tools/harvest_missing.py` が `work/missing-paragraphs.tsv` に集める）

### 3.3 文テンプレート（sentence.rs）

ゲームは英文を「書き出し（prefix）＋本体（core）＋後ろの句（suffix）」の部品を**コードでつなげて**作る。
例: `"In 125, "` ＋ `"{名前} struck down {名前}"` ＋ `" in {場所}."`

- `sentence-templates.csv`（group, kind, text, translation）。group は部品を作る関数（53.17 の RVA）。同じ group の部品だけを組み合わせる
- 照合: 本体の英語の固定部分で候補を絞り（Aho-Corasick）、`書き出し＋本体＋後ろの句` を1つの正規表現で照合。差し込み同士が隣り合う組み合わせは区切りが決まらないので使わない
- 日本語 = 書き出しの訳 ＋ 本体の訳（`{REST}` の位置に後ろの句の訳）＋ 句点。本体の訳が `{REST}` の前に記号を持つ（`流れは変わったか？{REST}`）ときは、句点を付ける前に末尾の記号を外す（「？？」「！！」になっていた）
- 差し込まれた語句は、さらにテンプレート・辞書で訳せれば訳す（冠詞 a/an/the を外して引く）。人名・地名はそのまま
- 文章は段落・改行のトークン（`[B]` `[P]` `[R]` `[CHAR]` `[KEY]`）と文末（`.!?`）で区切って1文ずつ照合する。色の変更 `[C:..]` とリンク `[LPAGE:..]語句[/LPAGE]` は文の一部として扱う（伝説モードの文はリンクを含む1つの文字列で来る）
- 速さ: 正規表現は「固定部分が順に文中にあるか」「書き出しは文頭・後ろの句は文末に合うか」を文字列で確かめた組み合わせだけ作る（全組み合わせを作ると1文で数万個になり、ゲームが固まった）
- 誤訳よけ（手書きの group `manual` には適用しない）
  - 固定部分に冠詞・前置詞以外の英単語（3文字以上）が必要。さらに英単語2語以上か、文の英字の3割以上
  - 差し込みの値が単語の途中で切れる当てはめ（`"T"` と `"hepani"` など）、リンクの途中で切れる当てはめは使わない
  - 部品の中で差し込みが隣り合う（`}{`）テンプレートは使わない
- 差し込みの値: リンクは中身だけ訳して包み直す。`the kobold 名前` のような「辞書の語＋大文字で始まる名前」は `コボルドの名前` にする
- 伝説の年 `In the late autumn of 2, ...` は `In 2, ...` として照合し、訳の `2年、` を `2年の晩秋、` に直す
- 全体が `"..."` の台詞は中身を訳して「」で囲む
- テンプレートで訳せない文は、辞書の完全一致でも引く（台詞の中の "I'm very fond." など）
- どれでも訳せない「ラベル: 値」（"Lover: Olon Bouldermoisten"）は、辞書にあるラベルだけ訳す（translator/mod.rs の translate_label）
- `translations/sentences-fix.tsv`（group を `manual` にする）で、テンプレートを手で足せる。取り出しで取れなかった文や、取れた部品の質が悪い文（伝説の出来事など）はここに書く
- ゲームを起動せずに確かめるには `tools/sentences/test.py`（エンジンと同じ手順の再現）。ログの `paragraph piece` 行に、文章として渡された英文がそのまま出る
- MOD に同梱された訳も読み込む（docs/mod-translation.md）

## 4. 翻訳データ

| ファイル | 内容 | バージョン依存 |
|---|---|---|
| translations/ui.tsv | 実行ファイルの UI 文字列 | なし（英語がキー） |
| translations/ui-extra.tsv | ui.tsv に無かった UI 文字列（`tools/ui/prepare.py` でバッチ化 → Haiku が `tools/ui/INSTRUCTIONS.md` に従って訳す → `tools/ui/merge.py` で検査して生成） | なし（英語がキー） |
| translations/ui-extra2.tsv | 2回目の洗い出しで見つかった訳の無い UI 文字列（2026-11-13、493件中 323件）。`work/hardcoded_msgids.json` の全文字列のうち、`tools/ui/prepare.py` の `selectable` を通り、辞書にも文テンプレートにも無いものを Haiku が訳し、`python tools/ui/merge.py ui4 ui-extra2` で検査した。"Nth eldest son" などは手でそろえた（上から N 番目の息子）。"n ardent"（"a" の後ろに付く断片）や内部の "… hf" は訳さない | なし（英語がキー） |
| translations/raw-descriptions.tsv | raw ファイルの `[DESCRIPTION:]` `[TOOLTIP:]` `[CATEGORY_NAME:]` などの文章（工房の説明、楽器の説明など）。`python tools/ui/merge.py ui3 raw-descriptions` で生成 | なし（英語がキー） |
| translations/terms.tsv | raw ファイル由来の名前 | なし |
| translations/harvested.tsv | ログから集めた未翻訳の訳 | なし |
| translations/overrides.tsv | 手直し（最優先） | なし |
| translations/wiki-terms.tsv / term-rules.tsv | 日本語Wikiの訳語と置き換え規則 | なし |
| translations/paragraphs.tsv | 長い文章の訳（英文全体） | なし |
| translations/persona.tsv | 性格・夢・外見の語句（"craftsdwarfship" の行は build.py が "craftsmanship" の形も足す） | なし |
| translations/values.tsv | 価値観・性格の句 469件（実行ファイルの一覧 0x17417xx 付近から取り出し、Haiku が `work/persona/VALUES.md` に従って訳した） | なし |
| translations/needs.tsv | 欲求タブの部品（状態・欲求・全体）。build.py が「主語 is 状態 after 欲求.」の全組み合わせを辞書に、神の名前が入る文を文テンプレートに足す | なし |
| translations/monster-names.tsv | 夜の生き物・悪魔の名前の部品（形容詞・種類）。build.py が全組み合わせを辞書に足す | raw のスクリプト `creatures.lua` に依存 |
| translations/combat.tsv | 戦闘の文テンプレート（`tools/combat_templates.py` が作る。手で直さない） | なし |
| translations/prefs.tsv | 好みの「〜ゆえに」（"donkeys for their stubborness"）。`tools/pref_combos.py` が raw の `[PREFSTRING:..]` と生き物・植物の名前から実際にある組み合わせだけ作る（約1300件。手で直さない） | raw の `[PREFSTRING:..]` に依存 |
| translations/thoughts.tsv | 思考タブの感情の文テンプレート（"He was angry after …"）。`tools/thought_templates.py` が感情の語（実行ファイルの一覧 127語）× 主語 × be/felt の形で作る（約6400件。手で直さない） | なし |
| translations/thought-causes.tsv | 思考タブの「きっかけ」の句のうち、文テンプレート（group e44340）で訳せなかったもの。`tools/thought_causes.py` で候補を洗い出し、手で訳す | なし |
| translations/bodyparts.tsv / gems.tsv | 体の部位・宝石の名前 | なし |
| translations/sentences.tsv / sentences-fix.tsv | 文テンプレートの部品の訳 | **group（RVA）が依存**。`tools/sentences/rekey.py` で引き継ぐ |
| data/no-translate-callers.txt | 訳さない呼び出し元 | **依存**（RVA） |
| data/context-dictionary.csv | 呼び出し元ごとの訳 | **依存**（RVA） |
| data/offsets.txt | 関数のパターン、構造体のオフセット | **依存** |
| tools/re/version.json | std::string 操作関数などの RVA | **依存** |

`python tools/build.py` で `data/` を作り、`install.ps1` でゲームフォルダへ。

## 5. ゲームが更新されたときの手順

### 5.1 まず起動して確かめる

1. `install.ps1` → ゲーム起動 → `dfint-data/dfint-log.log` を見る
2. `Expected one result for key '...'` が出たら、そのパターンが見つからない（5.2）
3. 起動はするが表示が崩れる → 構造体のオフセット（5.3）

### 5.2 関数のパターンを作り直す

`tools/re/` のスクリプト（Python 3.10+, `pip install pefile capstone`）。引数の exe はゲームの `Dwarf Fortress.exe`。

- **ADDST 系など既存のもの**: 本家 dfint（https://github.com/dfint/df-steam-hook-rs ）の更新を参照するのが早い
- **MARKUP_PROCESS_STRING**:
  1. `python xref.py <exe> "stout charges to fortune"`（ようこそ画面の文章）で、文字列を使う関数を探す
  2. `python dis.py <exe> <その関数の参照位置>` で、文字列を std::string に組み立てた後に `lea rdx, [rbp-..]; mov rcx, rsi; call X` と呼ぶ X が markup_process_string
- **MARKUP_FORMAT**: `python findlayout.py <exe> <markup_process_string の前後 0x40000 の範囲>` で、単語の +0x28 / +0x2c に書き込む関数を探す。本体の入口は `cmp [rcx+0x30], edx` で始まる（幅が同じなら何もしない）
- **std::string 操作（tools/re/version.json）**: `dis.py` で文字列の追加箇所を見ると、`lea rdx, 文字列; mov rcx, 出力先; call X` の X が append。`callers.py <exe> <X>` で数千か所から呼ばれていれば正しい
- パターンは `python pattern.py <exe> dump <RVA> 64` で関数の先頭を表示し、アドレス部分を `??` にして `python pattern.py <exe> check "<パターン>"` で一意か確かめる
- 新しいパターン・RVA を `data/offsets.txt` と `tools/re/version.json` に書く

### 5.3 構造体のオフセット

マークアップ文章の構造体（2 章）は、MARKUP_FORMAT の逆アセンブル（`dis.py`）で `[rcx+0x30]`（幅）、`[単語+0x28]` `[単語+0x2c]`（位置）、`[単語+0x30]`（フラグ）を確かめる。変わっていれば `engine/src/paragraph.rs` の定数を直してビルド。

### 5.4 呼び出し元に依存するデータ

`no-translate-callers.txt` と `context-dictionary.csv` は RVA が変わるので、ゲームを Debug ログで遊んで作り直す。

- 「文章を単語ごとに描く」呼び出し元はエンジンが自動で判定する（ログに「検出」と出る）。一覧は無くても動く
- 攻撃の画面の短い語（Tricky / Slow / square など）は、文字列を読む lea 命令の位置を実行ファイルから探して「+ 0x23」を呼び出し元にした（3.1 の冒険者モードの項）。同じ方法で探し直す
- 呼び出し元ごとの訳し分け（並べ替えの見出し "Cat" → 分類 など）は、ログの `found translation` / `missing translation` の下の行の先頭（`^xxxx`）を見て書き直す（LOG_LEVEL:Trace にすると訳せた文字列の呼び出し元も出る）
- 中央寄せの見出し（`^xxxx center`）も呼び出し元ごとなので、同じ方法で探し直す（下の「中央寄せ」を参照）

### 5.5 文テンプレートの取り出し直し

```
cd dfint-ja
python tools/re/scale.py "../Dwarf Fortress.exe" work/sentences/funcs.json      # 文を組み立てる関数の一覧
python tools/re/paths.py "../Dwarf Fortress.exe" --json work/sentences/all_paths.json <funcs.json の各 RVA>
python tools/sentences/prepare.py        # 翻訳用バッチ（work/sentences/batches/）
python tools/sentences/vanilla_text.py   # data/vanilla/vanilla_text の文章
python tools/sentences/rekey.py          # 既存の訳を新しい group に引き継ぐ（out/carried.tsv）
python tools/sentences/merge.py          # 検査してまとめる。未翻訳は work/sentences/missing.json
```

- 未翻訳の部品は、`tools/sentences/INSTRUCTIONS.md` に従って訳し、`work/sentences/out/*.tsv` に置いて `merge.py` を再実行する（Claude のサブエージェントに分担させた）
- `tools/sentences/slot_names.tsv` の差し込み関数の RVA も更新する（翻訳者向けの説明に使うだけ。無くても動く）
- 確認: `python -X utf8 tools/sentences/test.py "In 125, Urist shot and killed Bomrek in Lulartobul."`（ゲームを起動せずに照合を再現）
- 取りこぼした部品を探す: `python -I tools/re/frag_xref.py "../Dwarf Fortress.exe"` で、未訳の部品（前後に空白がある文字列）を参照する関数を `work/frag/refs.json` に出す。`funcs.json` に無い関数があれば、その関数だけを `paths.py` にかけて `all_paths.json` に足す
- `paths.py` の上限（経路数 400・1関数40秒）は環境変数 `DFJA_MAX_PATHS` `DFJA_TIME_LIMIT` で変えられるが、**上げないこと**。53.17 で 3000 に上げたら、ありえない組み合わせ（文の途中どうしをつないだもの）が1万9千件増えただけだった。取りこぼしの多くは「 and 」「 in 」のようなつなぎの語で、すでにほかのテンプレートの中で訳されている

### 5.6 仕上げ

```
python tools/build.py
powershell -ExecutionPolicy Bypass -File install.ps1
```

起動して、タイトル → 世界生成（ようこそ画面）→ 入植（到着メッセージ）→ 住民一覧・人物画面を確かめる。

## 6. 解析の要点（53.17 で分かったこと）

- 描画経路がわからない文は、まずログを見る。訳さない呼び出し元で描かれた単語は `skip word`、新しい文字列は `### "..." @呼び出し元` と出る（`###` は訳せたかどうかに関係なく、初めて出た文字列すべて。**訳せなかったもの**は `missing translation for` の次の2行に呼び出し元と文字列が出る。未訳を数えるときはこちらを使う）。どれにも出なければ、フックしていない関数で描かれている（ユニット画面の思考の行は addcoloredst だった）。`tools/re/xref.py` で近くのラベル（"No unmet needs" など）を参照している描画関数を見つけ、その中の call を追う

- ゲームの英文は自然言語生成ではなく、固定の部品を std::string に順に追加して作る。部品は実行ファイルの .rdata にそのままある（約2万3千個、うち文の部品はコードの約1,800関数から参照）
- 名前・場所・品物などは専用の関数が出力先の文字列に追加する（`tools/re/version.json` の slot_functions）
- 伝説・歴史の出来事は種類ごとの大きな関数（例: 死亡の出来事 RVA 0xb88530）の switch で組み立て、末尾の「 in 場所」「 with 品物」などは共通の処理に合流する。`paths.py` はこの合流点で「本体」と「後ろの句」を分ける
- 出力先の std::string は、レジスタ（`mov rcx, rsi`）の場合と、スタック上の変数（`lea rcx, [rbp-0x60]`）の場合がある。画面を作る大きな関数（例: 人物画面の思考 RVA 0x1a7220）は複数の文字列を同時に組み立てるので、`paths.py` は出力先ごとに group を分ける（`1a7220`, `1a7220.1` …）
- 分岐をまたいで渡される文字列（`lea rdx, " drowned "; jmp 共通の append`）を拾うため、`paths.py` はレジスタの中身を経路ごとに追う
- 住民の発言・本の題名などは `data/vanilla/vanilla_text/objects/*.txt`（TEXT_SET。`[CONTEXT:...]` が差し込み）
- 長いポップアップ・告知・説明はマークアップ文章（`[B]` 改段落、`[C:前景:背景:明るさ]` 色、`[P]` 段落）

## 7. DFHack との併用

**2026-11-14、DFHack 53.17-r1（Steam の無料アプリ、App ID 2346660）と同時に動くことを実機で確かめた。**
タイトル画面にも要塞の画面にも DFHack の表示が出たまま、日本語化が効いている。DFHack のホットキー一覧も開ける。

置くファイルは**状況によらず同じ3つ**で、順番も関係ない（2026-11-14 に両方の状態で実機確認）。

| ファイル | 役目 |
|---|---|
| `dfhooks.dll` | 橋渡し役（`chainloader/`）。同じフォルダの `dfhooks_*.dll` を読み込んで、ゲームの呼び出しを渡すだけ |
| `dfhooks_dfint_ja.dll` | 日本語化の本体（`engine/`） |
| `dfint-data/` | 辞書・フォント・設定 |

仕組み:

- ゲームは起動時に `dfhooks.dll` を**1つだけ**読み、そこから `dfhooks_init` / `shutdown` / `update` / `prerender` / `sdl_loop` / `sdl_event` / `ncurses_key` の**7つ**を呼ぶ（DFHack の橋渡し役が公開しているのもこの7つ。実物の export を読んで確認した）
- 日本語化だけのとき … うちの `dfhooks.dll` が `dfhooks_dfint_ja.dll` を読む
- あとから DFHack を入れたとき … DFHack のランチャーが `dfhooks.dll` を自分のものに置き換える。DFHack の橋渡し役が `dfhooks_dfint_ja.dll` も読むので、そのまま動く
- DFHack が先で、あとからファイルを重ねたとき … うちの `dfhooks.dll` が DFHack のものを上書きするが、**うちの橋渡し役は DFHack が居ると気づいたら、処理を丸ごと DFHack の橋渡し役に任せる**（`…\DFHack\dfhooks.dll` を読み込んで7つを転送する）。向こうが今のフォルダを見て DFHack 本体と日本語化の両方を読む
- **なぜ丸投げするのか**: DFHack は読み込まれた直後に `dfhooks_preinit(std::filesystem::path)` を呼んでもらって自分の置き場所を知る。この引数は C++ の型で、ほかの言語から安全に作れない。呼ばずに DFHack を読み込むと「symbols.xml が開けない」と出て DFHack が止まる（実際に出した）。無理に真似るより、本家に任せるほうが安全
- **Steam 版 DFHack の置き方**（53.11-r3 以降）: 本体は別フォルダ（`steamapps/common/DFHack/`）に入り、ゲームフォルダには `dfhooks.dll` と `dfhooks_dfhack.ini` だけが置かれる。ini の中身は本体 DLL への絶対パス1行。`hack/` フォルダはゲームフォルダに来ない
- 依存 DLL を連れている相手（DFHack）を読み込むときは `LoadLibraryExW` に `LOAD_WITH_ALTERED_SEARCH_PATH` を付ける。付けないとエラー126（依存先が見つからない）になる
- `install.ps1` は**必須ではない**。開発中にビルド結果を上の形に並べ直すためのもの。`dfhooks.dll` が自分のものかは、DLL の中に `dfint-ja chainloader` という文字列があるかで見分ける

確かめた上での注意点:

- **日本語が DFHack の画面の上に重なって描かれる。** dfint-ja は1フレームの最後に日本語を描くので、DFHack のパネルがゲームの UI に重なる場所では、下にあるはずの日本語が透けて見える。枠を塗りつぶす仕組み（`draw_nineslice` の cover）は DFHack のパネルには効かない（nineslice で描いていないため）
- DFHack 自身の画面（Lua の UI、overlay ウィジェット）は addst のフックを通らないので**英語のまま**。DFHack を動かした状態のログ 24,351 行を調べたが、DFHack 由来の文字列は1件も来ていない

### 7.1 DFHack を確認の道具として使う

隊商・包囲・芸術品・貴族の命令のような画面は、ふつうに遊ぶとゲーム内で何年も待つ必要がある。
DFHack を入れておくと数分で出せる（MOD が DFHack に依存するわけではない。**こちらの確認作業のための道具**）。

**画面を触らずにコマンドを打てる。** `hack\dfhack-run.exe` が、動いているゲームにコマンドを送り込む。

```
L:\SteamLibrary\steamapps\common\DFHack\hack\dfhack-run.exe lua "print(1+1)"
L:\...\dfhack-run.exe lua --file <スクリプト.lua>
```

**キーの組み合わせ（Ctrl+Shift+P など）はゲームに届かない**（修飾キーが無視され、`p` だけが通って別の操作が始まる）ので、
コマンド欄を開く方法に頼らず `dfhack-run` を使うこと。DFHack のホットキー一覧（ロゴをクリック）は、
開くたびに行の位置が変わるので、座標の決め打ちも当てにならない。

使ったもの:

| 目的 | コマンド |
|---|---|
| 隊商を呼ぶ | `force Caravan`（`force Diplomat` / `force Megabeast` / `force Migrants` も） |
| 隊商の状態を見る | `caravan list` |
| 芸術品の気分を起こす | `strangemood --force --type fey` |
| 移民 | `migrants-now` |
| 蘇生・全快 | `full-heal --all_civ -r` |
| 品物を作る | `modtools/create-item --item DRINK --material PLANT_MAT:...:DRINK --unit <id>` |
| 知らせを読む | `lua "local a=df.global.world.status.announcements ..."` |
| 一時停止・早送り | `lua "df.global.pause_state=false; df.global.enabler.fps=500"` |

**建物はクリックでは置けない**（建設メニューで選ぶところまでは進むが、地図をクリックしても置かれない）。
Lua で直接置く。交易所を建てた例が `work/` の `depot.lua`。材料が無いと建設が止まるので、
`b:setBuildStage(b:getMaxBuildStage())` で完成させた。

**早送りには落とし穴がある。** `enabler.fps` を上げるとゲーム内時間が一気に進み、
水も酒も無い要塞では**住民が脱水で全滅する**（実際に一度全滅させた）。早送りする前に、
住民の渇き・空腹・眠気の値を定期的に 0 に戻すこと。

```lua
for _,u in ipairs(df.global.world.units.active) do
  if dfhack.units.isCitizen(u) then
    u.counters2.thirst_timer = 0
    u.counters2.hunger_timer = 0
    u.counters2.sleepiness_timer = 0
  end
end
```

確認用のセーブは、作業前に複製しておくこと（`save-backup-…`）。

### 7.2 ゲームの文を吸い出して抜けを探す

画面を1枚ずつ見るより速くて漏れが少ない。**ゲームが持っている英語の文をそのまま取り出して、翻訳エンジンにかける。**

出どころは2つ。

```
# ゲーム内の知らせの一覧（いま読み込んでいる要塞のもの）
dfhack-run.exe lua "local a=df.global.world.status.announcements; for i=0,#a-1 do print(a[i].text) end"

# ゲームが書いているログ（遊んだぶんが全部たまる。戦闘の文が大量に入る）
L:\SteamLibrary\steamapps\common\Dwarf Fortress\gamelog.txt
```

重複を除いて `work/frag/` に置き、`tools/sentences/test.py` にかけると、訳せない行が一覧で出る。
2026-11-14 にこれをやったところ、639行のうち40行が未訳で、戦闘の文のテンプレート不足がまとめて見つかった。

**この方法で見つけた取り違えの例**: 仕事の取り消しの知らせ
`Lorbam Bomrekmostib, Stonecrafter cancels Give water: No water source.` が
「… cancels Give water「水源がない」」になっていた。`sentence.rs` の「話し手: 台詞」を会話として扱う処理に
引っかかっていたため。話し手が6語以内という条件なので、**職業名の長さ次第で引っかかったり引っかからなかったり**し、
画面を見ているだけでは気づきにくかった（`" cancels "` を含むものは会話とみなさないようにして解決）。

**注意**: `test.py` は文テンプレートだけを写したもので、**完全一致辞書も組み立て型ルックアップも持たない**。
品物の名前（`copper battle axe` など）はそちらで訳すので、この方法では測れない。品物は実際に画面を出して
`dfint-log.log` の `missing translation` を見ること。

### 7.3 DFHack の日本語化（engine/src/dfhack.rs）

DFHack は自分で文字を描くので、ゲーム本体のフックでは拾えない。`dfhack.dll` が公開している
描画関数に別途割り込む。DFHack が入っていないときは何もしない。

割り込む先（MSVC の名前で公開されているので `GetProcAddress` で取れる）:

| 関数 | 何に使われるか |
|---|---|
| `Screen::paintString(const Pen&, int x, int y, const std::string&, bool map)` | 文字列をそのまま描くところ |
| `Screen::Painter::do_paint_string(const std::string&, const Pen&, bool map)` | **本命**。DFHack の部品（`gui/widgets.lua` の `dc:string(…)`）はここを通る |
| `Screen::fillRect(const Pen&, int x1, int y1, int x2, int y2, bool map)` | DFHack の窓の下地。塗った範囲の**こちらの訳を消す**ために使う |

- 描く位置は、`paintString` は引数の x, y、`do_paint_string` は Painter の `gcursor`（`Painter : ViewRect`
  で ViewRect が `rect2d view, clip` = 16バイトなので、その直後の 16ビット2つ）。
- 色は `Pen` の `fg`（0〜7）+ `bold` と `bg`。ゲームの色表（`gps.uccolor`）で実際の色に直す。
- 訳せたら自前の字で描き、元の場所には**訳の幅ぶんの空白**を渡して英語を消す（addst と同じやり方）。
- `fillRect` で下地を消さないと、DFHack の窓の下にゲーム本体の訳が残って**透けて見える**。
- DFHack はゲームの起動中に読み込まれるので、`update_all`（毎フレーム）から
  `dfhack::try_attach()` を呼んで、見つかったら1度だけ割り込む。

訳す文字列は `translations/dfhack.tsv`。ゲーム本体とは出どころが違うので別ファイルにしてある。
DFHack の操作パネルの文字列は、次のところから取り出せる（`scratchpad/dfh_extract.py` と同じ手順）:

- `hack/scripts/internal/control-panel/registry.lua` … 各ツールの `label` と `desc`
- `hack/scripts/gui/control-panel.lua` … タブの説明（`intro_text`）、ボタン、サブタブの説明（`blurbs`）

#### 折り返された説明文のつなぎ直し

DFHack は長い説明を**自分で折り返してから**1行ずつ渡してくる。`translator` には
「同じ呼び出し元から続けて来た未訳の行をつないで、辞書にあればその訳を行数ぶんに折り返し直す」
仕組みがあるので、これを使う。DFHack には呼び出し元の番地が無いので、**描き始めの列**を
呼び出し元の代わりにする（`^dfhack:40` のように）。折り返された行は列が揃うので、これで分けられる。

ただし `translator` には「`or` や `the` のような語を単独で描いた呼び出し元は、
文章を単語ごとに描いているとみなして以後まったく訳さない」判定がある。
DFHack は短い語も同じ列に描くので、この判定に引っかかると**その列ごと英語のまま**になる。
そのため `func == "dfhack"` のときはこの判定を飛ばしている。

#### まだできていないこと

- **タブの見出し**（操作パネルの「Automation」など）は、絵のモードでは1文字ずつ
  `dc:char(…)` → `Screen::paintTile` で描かれるので、文字列として拾えない。
  ゲーム本体の入植準備画面のタブと同じ作り（`tabs.rs` の `add_tile`）で、
  続けて描かれた1文字を集めて訳す必要がある。`paintTile` は DFHack が描くタイルすべてで
  呼ばれる（毎フレーム数千回）ので、溜め込みの作りは軽くしないと速度に響く。
- ツールの名前（`eggs-fertile` など）は命令の名前そのものなので訳さない。

## 7.4 ゲームを起動せずに翻訳を確かめる（tools/check.py）

`engine` に **検査用のコマンド** を足してある。ゲームに割り込む仕掛けを外し、翻訳器だけを動かすもので、
英語を1行ずつ標準入力に流すと「英語<TAB>訳」をタブ区切りで返す。

```bash
cd engine && cargo build --release --features offline --bin dfint-check
cd "<ゲームフォルダ>" && dfint-ja/engine/target/release/dfint-check.exe < names.txt
```

- `offline` という印を付けてビルドすると `lib.rs` の `attach()`／`detach()` が外れ、フックを張らずに読み込める。
  同じ印が必要なので、ふだんの DLL のビルド（`cargo build --release`）とは**別のビルド**になる。
- `dfint-data` をカレントディレクトリから読むので、**ゲームフォルダで実行する**（インストール済みの辞書が対象）。
- 呼び出し元（bt）は空にしてあるので、「訳さない呼び出し元」「中央揃え」「幅の切り詰め」は再現しない。

`tools/check.py` がこれを使う回帰テスト。`work/check/*.txt`（英語を1行ずつ）を訳して、
`work/check/*.base.txt`（前回の結果）と比べ、違う行数と未訳の行数を出す。

```bash
python -I -X utf8 tools/check.py            # 前回と比べる
python -I -X utf8 tools/check.py --update   # 控えを今回の結果で更新する
python -I -X utf8 tools/check.py --miss     # 訳せなかった行を並べる
```

`tools/sentences/test.py` は**文テンプレートだけ**を Python で再現したものなので、
品物名のように組み立て型のルックアップを使うものは測れない。両方あるが、網羅を見るのは `check.py` のほう。

### 調べる文字列の集め方

ゲームが実際に出す文字列は DFHack で吸い出すのが早い（`work/check/names.txt` は約4000行）。

```lua
-- 品物・生き物・材質・植物・建物・仕事の表示名をすべて書き出す
for _,it in ipairs(df.global.world.items.all) do add(dfhack.items.getReadableDescription(it)) end
for _,u in ipairs(df.global.world.units.all) do add(dfhack.units.getReadableName(u)) end
-- ファイルに書くときは dfhack.df2utf() を通す（ゲームの中は CP437）
```

もう一つの出どころが `dfint-data/dfint-log.log` の `missing translation` 行。
ゲームを動かして画面を一通り開いたあと、次で未訳の文字列だけ取れる。

```bash
grep -A2 "missing translation" dfint-data/dfint-log.log | grep -v "missing translation" | grep -v '^--' | sort -u
```

### 世界生成で組み立てられる名前

怪物（夜の生き物・悪魔・天使）と神話の材質の名前は、`data/vanilla/vanilla_procedural/scripts/generators/`
の Lua が**決まった語彙**を組み合わせて作る。組み合わせは世界ごとに変わるので辞書には入れられない。
語彙は `translations/procgen-names.tsv`（分類・英語・日本語）に置き、`build.py` が
`data/lookups/monsters.csv` に組み立て型の表として書き出す。

- `creatures.lua` … `night_troll_names` / `demon_names` / `angel_names_*`（種類）、`night_troll_flavor_adjs` と
  各所の `flavor_adj`（形容詞）、`night_troll_*_names`（連れ合い）、`night_troll_end_phrases`（末尾句）
- `creatures/rcp.lua` … `name_string`（姿のもとになる生き物。獣人 "were〜" の語幹でもある）
- `data/init/globals.lua` … `random_sphere_adjective` / `random_sphere_nouns`（神の領域）
- `materials.lua` / `divine.lua` … 神話の材質（"primeval stardust"、"shadow stuff"）

## 7.5 配布物を作る（tools/package.ps1）

```powershell
powershell -ExecutionPolicy Bypass -File tools\package.ps1 -Build
```

`dist\DwarfFortress_JP.zip` ができる。**この名前は版をまたいで変えないこと**
（紹介ページが `releases/latest/download/DwarfFortress_JP.zip` で最新版を指しているため）。中身はゲームフォルダに重ねてコピーすれば動く形
（`dfhooks.dll` / `dfhooks_dfint_ja.dll` / `dfint-data\` / はじめにお読みください.txt / LICENSE\）。

- 版は `engine/Cargo.toml` の `version`。`-Version` で上書きできる。
- 画面の左下に出る版の文字列は、ビルド時の環境変数 `HOOK_VERSION` から取る。
  付けないと「開発版」になるので、`package.ps1` が `-Build` のときに設定している。
- 配布する `data/config.txt` の `LOG_LEVEL` は `Warn`（ほとんど何も書かない）。
  `Debug` にすると未訳の文字列が記録されるが、毎回 800KB ほどになるので配布時は切る。
  中央揃えを探すための `centerscan` の記録も `Debug` のときだけ集める。
- **PowerShell のスクリプトは UTF-8 BOM 付きで保存すること。** BOM が無いと
  Windows PowerShell 5.1 が ANSI として読み、日本語のコメントで構文エラーになる。

確かめること（両方とも実機で通す）:

1. DFHack あり … `dfhooks.dll` は DFHack のものを残し、残り2つを置く
2. DFHack なし … `dfhooks_dfhack.ini` を外して、こちらの `dfhooks.dll` が engine を直接読むこと

## 8. 既知の制限

- 文テンプレートで訳せない文は英語のまま（崩れずに表示される）
- 戦闘の記録や芸術品の説明は組み合わせが多く、テンプレートの照合率が低い可能性がある
- 1行の文字列（addst）は表示幅がゲーム側で決まっているので、日本語が長いと隣の表示と重なることがある。
  交易画面の品物の一覧のように重なりが目立つところは、`data/no-translate-callers.txt` に
  `<呼び出し元> clamp` と書くと、英語の文字数ぶんの幅に収まるまで訳を切り詰めて「…」を付ける
- ユニット画面の思考・性格の行（ADDCOLOREDST）の強調色は、色の付いた英単語の辞書の訳が訳文にそのまま含まれるときだけ付く
- WRAP_LINES で折り返した行が addst / addcoloredst 以外の経路で描かれると、仮の文字列（空白に見える 0xFF）がそのまま出て空欄になる
- 怪物の**見た目の説明文**（"An enormous serpent composed of sandy loam.  It has wings and it undulates rhythmically.  Beware its deadly spittle!"）は `tools/beast_desc_templates.py` が訳を作る。文の形は5つで、ゲームは世界生成のときに Lua（`data/vanilla/vanilla_procedural/scripts/generators/creatures/shared_info.lua` の `build_description`）で組み立て、生き物のカーストの説明としてセーブに埋め込む（忘れられし獣・巨人・悪魔・夜の生き物・獣人・実験体・天使が同じ処理）。部品の英語は `tools/beast_desc_extract.py` が Lua と raw から集めて `work/beast_parts.tsv` に書き、訳は `translations/beast-parts.tsv`。生成物は `translations/beast-terms.tsv`（辞書 7700件）と `translations/beast-desc.tsv`（テンプレート 293件）
  - **1文目だけは組み合わせが数十万通り**（大きさ10 × 形容15 × 体の名前243 × 素材285）になるので、大きさ・姿・with句・素材をテンプレートの**固定部分**にして、差し込みは「形容＋体の名前」と素材だけにした。テンプレートは安いが辞書の行数は高い、という振り分け
  - 一般の辞書の訳がこの文脈に合わない語（`great` が「素晴らしい」になる）は `beast-parts.tsv` の末尾で上書きする。このファイルは名前順で最初に読まれるので最優先になる
  - 鱗の質感は「形 + and + 並び」の2つの一覧の組み合わせ。`small` / `large` が大きさの語と英語でぶつかるので、訳はスクリプトに直接書いてある
  - **手順に順番がある**: `build.py` → `beast_desc_templates.py` → `build.py`。生成スクリプトが `data/simple-dictionary.csv`（build.py の出力）を訳の引き先に使うため
  - 夜の生き物・天使の締めの文（"This night creature was first created by …"）は断片をつなぐ形で、日本語の語順に合わないので**まだ訳していない**
- 設定画面の「世界地図にトンネルを表示」の値（`拠点検索中`）など、値の訳が文脈に合っていないものが少し残っている
- **`lookups/00-index.csv` に組み立て型の行を足してはいけない**。`{PLANT} fabric` のような行を足したところ、辞書そのものが読み込まれなくなり、ゲームが英語のまま落ちた。索引は `{CREATURE}` のような1語の参照だけにして、組み立てが必要なものは build.py で辞書の項目として作る（"hemp fabric" → 「麻の布」は素材ごとに辞書へ）
