# 芸術の形式（音楽・詩・踊り）の説明文

ゲームは、音楽・詩・踊りの「形式」の説明文を、短い語句をつなげて作ります
（実行ファイルの `ded9d0` = 音楽、`e8e2e0` = 詩、`4f47b0` = 踊り）。
組み合わせの数が多すぎて、文の部品を機械で取り出す `tools/sentences/` のやり方では
当てられないので、ここでは**文のかたちを手で書いて**います。

- `translations/art-forms.tsv` … 差し込まれる語句（速さ・強さ・奏法・楽節の名前など）
- `translations/sentences-fix.tsv` の「芸術の形式」の節 … 文のかたち（このスクリプトが作る）

## 作り直しかた

```
python -I -X utf8 tools/art_forms/music.py .
python -I -X utf8 tools/art_forms/poem.py .
python -I -X utf8 tools/art_forms/dance.py .
python -I -X utf8 tools/art_forms/sentences.py .
python -I -X utf8 tools/build.py
powershell -ExecutionPolicy Bypass -File install.ps1
```

`music.py` → `poem.py` → `dance.py` → `sentences.py` の順に実行すること
（それぞれが `art-forms.tsv` の自分の節を作り直すため）。

## 元の文のかたちの調べかた

実行ファイルの関数から、コードの順に文字列を取り出すと、文の組み立てが分かります
（`docs/architecture.md` の LEA 参照の手順）。

```
python -I -X utf8 tools/re/funcs.py "../Dwarf Fortress.exe" ded9d0
```

## 確かめかた

`work/check/para_music.txt` `para_poem.txt` `para_dance.txt` が検査用の文章です。
`para_` で始まる検査ファイルは、ゲームが単語ごとに折り返して描く文章の経路
（`markup_process_string`）で訳されます。

```
python -I -X utf8 tools/check.py work/check/para_music.txt
```

世界ごとに作られる名前（楽器の `therleth`、音階の `anam`）は英語のまま残ります。
辞書に載せようがないので、エンジンはこれを「訳せた」とみなします（`sentence.rs` の `procgen_name`）。
