# MOD を日本語化する（MOD 作者・翻訳者向け）

dfint-ja は、MOD に同梱された日本語訳を自動で読み込みます。MOD のフォルダに `dfint-ja/` フォルダを入れておけば、dfint-ja を使っている人の画面で、その MOD の生き物・アイテム・建物などが日本語で表示されます。dfint-ja を使っていない人には影響しません（ゲームは `dfint-ja/` フォルダを読みません）。

## 置き方

```
<あなたの MOD>/
  info.txt
  objects/ ...
  graphics/ ...
  dfint-ja/
    dictionary.csv     名前・ラベルの訳（必須）
    lookup.csv         組み立て用の表（任意。生き物・材質を足すときは入れてください）
    paragraphs.csv     MOD が出す長い文章の訳（任意）
```

dfint-ja は次の場所を探します。

| 場所 | 用途 |
|---|---|
| `data/installed_mods/<MOD>/dfint-ja/` | ゲームが使用中の MOD（ゲームがここにコピーする） |
| `mods/<MOD>/dfint-ja/` | 手で入れた MOD |
| Steam ワークショップ（`steamapps/workshop/content/975370/<ID>/dfint-ja/`） | 購読した MOD |
| `dfint-data/mods/<パック名>/` | MOD 作者以外が作った翻訳パック（下記） |

同じ語が複数の場所にあるときは、先に見つかったものが使われます。dfint-ja 本体の訳がある語は、どの場所の訳よりも本体が優先されます（MOD 独自の語を足すための仕組みです）。

## dictionary.csv

UTF-8 の CSV。1行目は見出し `text,translation`。

```csv
text,translation
giant cave toad,巨大洞窟ヒキガエル
giant cave toads,巨大洞窟ヒキガエル
toad leather,ヒキガエルの革
Toad Breeder's Pen,ヒキガエル飼育場
```

- `text` は画面に出る英語そのまま（大文字小文字は区別しません）。
- 単数形と複数形は別の行に書きます（日本語は同じでかまいません）。
- dfint-ja 本体に訳がある語（"iron" など一般的な語）は、本体の訳が優先されます。MOD 独自の語だけを書けば十分です。
- `X leather`（X の革）、`X bone`（X の骨）のような「素材名＋部位」や「素材名＋品物名」は、dfint-ja が自動で組み立てます。ただし組み立てに使うのは下記の `lookup.csv` の表です。MOD が生き物や材質を足すときは、そちらにも書いてください。
- `translation` が空の行は読み飛ばします。

### 雛形を自動で作る

dfint-ja のフォルダで（Python 3.10 以上）:

```
python tools/mod_template.py "<あなたの MOD のフォルダ>"
```

MOD のフォルダに書き込みたくないとき（翻訳パックを作るとき）は、出力先を指定します。

```
python tools/mod_template.py "<MOD のフォルダ>" "<出力先の dictionary.csv>"
```

MOD の raw から名前をすべて取り出して `dfint-ja/dictionary.csv` を作ります。dfint-ja 本体に訳がある語は訳が入った状態になり、残りは空欄です。空欄を埋めてください。もう一度実行すると、書いた訳は残したまま、増えた語だけ足します。

## lookup.csv（任意）

MOD が**生き物や材質を足す**ときは、これも入れてください。dictionary.csv だけでは `duergar leather`（デュエルガーの革）のような組み合わせが英語のまま残ります。

```csv
table,text,translation
CREATURE,duergar,デュエルガー
CREATURE,warg,ワーグ
CREATURE,warg pup,ワーグの子
MATERIAL,grown wood,育てた木材
MATERIAL,grown wooden,育てた木製
PLANT,grown feather tree,育てたフェザーツリー
```

- `table` には `CREATURE`（生き物）、`PLANT`（植物）、`MATERIAL`（材質）、`ITEM:NOUN`（品物）、`MONSTER`（世界生成の怪物）などを書きます。
- ここに生き物を入れておくと、`X leather`（X の革）、`X bone`（X の骨）、`X corpse`（X の死体）、`X leather glove`（X の革の手袋）のような組み合わせが自動で日本語になります。単数形と複数形は別の行に書きます。
- 材質は、名前（`grown wood`）と形容詞形（`grown wooden`）の両方を入れてください。品物の名前は形容詞形で作られます。
- dictionary.csv にも同じ語を書いておくと、名前そのものが単独で出る場面も日本語になります。

## paragraphs.csv（任意）

MOD が出すポップアップなどの長い文章（ゲームが自動で折り返して表示する文章）の訳です。

```csv
text,translation
"The toads are restless tonight. Something stirs in the deep.","今夜はヒキガエルが落ち着かない。深みで何かがうごめいている。"
"{1} has tamed a giant cave toad!","{1}が巨大洞窟ヒキガエルを手なずけた！"
```

- `text` は英文全体。空白の連続は1つとして照合します。
- 名前など変わる部分は `{1}` `{2}` … と書くと、どんな値でも当てはまります。辞書にある語はそこでも訳されます。
- `[B]`（段落の区切り）や `[C:7:0:1]`（色）などのトークンは、訳文にも同じように入れてください。

## 翻訳パック（MOD 作者以外が訳す場合）

MOD 本体を変えずに訳を配りたいときは、`dfint-data/mods/<パック名>/dictionary.csv`（と paragraphs.csv）として配布してください。利用者はゲームフォルダの `dfint-data/mods/` に置くだけで使えます。

### dfint-ja が同梱しているパック

| パック名 | 対象の MOD |
|---|---|
| `playable-races-revisioned` | [Playable Races Revisioned](https://steamcommunity.com/sharedfiles/filedetails/?id=3665499038)（デュエルガー・オーク・ウッドエルフ・ハイエルフ・コボルドなどでのプレイを可能にする MOD） |

同梱パックは dfint-ja を更新すると入れ替わります。訳を自分で変えたいときは、別の名前のフォルダにコピーしてから直してください（名前が違うフォルダは更新で消えません）。

## 用語をそろえる

訳語は dfint-ja の用語集（`docs/glossary.md`）と日本語Wiki（https://wikiwiki.jp/dwarffort/ ）にそろえると、ゲーム全体で読みやすくなります。

## 確かめ方

1. `dfint-data/config.txt` の `LOG_LEVEL` を `Debug` にしてゲームを起動
2. `dfint-data/dfint-log.log` に `MOD の訳を読み込みました: N 件 <ファイル>` と出れば読み込まれています
3. 英語のまま出た文字列はログに `missing translation` として記録されます。`python tools/harvest_missing.py` で一覧にできます
