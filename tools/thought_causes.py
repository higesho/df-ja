"""思考タブの「きっかけ」の句（"after talking with a friend"）のうち、まだ訳せないものを洗い出す。

ゲームは「after / dwelling upon …」の後ろにきっかけの句をつなぐ。句は実行ファイルの一覧にあり、
多くは文テンプレートの group e44340 が訳せる。訳せないものだけを書き出して、手で訳を足す。

使い方: python -I -X utf8 tools/thought_causes.py          # 候補を work/prefs/causes_todo.txt に書く
出力: work/prefs/causes_todo.txt（1行1句）
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXE = ROOT.parent / "Dwarf Fortress.exe"
WORK = ROOT / "work" / "prefs"

# きっかけの一覧が並んでいるあたり（この文字列の前後）
ANCHORS = [b"talking with a friend", b"getting into an argument", b"eating rotten food"]
# きっかけではない文（性格の説明など）を外す
SKIP_HEAD = ("has ", "is ", "was ", "does ", "doesn't ", "would ", "likes ", "prefers ", "can ", "could ",
             "never ", "always ", "tends ", "will ", "needs ", "wants ", "takes ", "sees ", "feels ")


def main():
    data = EXE.read_bytes()
    cands = set()
    for anchor in ANCHORS:
        i = data.find(anchor)
        if i < 0:
            continue
        seg = data[i - 8000: i + 8000]
        for m in re.finditer(rb"[\x20-\x7e]{6,}", seg):
            s = m.group(0).decode()
            if not re.fullmatch(r"[a-z][A-Za-z' ,-]{5,70}", s):
                continue
            if " " not in s.strip() or s != s.strip():
                continue
            if s.startswith(SKIP_HEAD):
                continue
            cands.add(s)
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "causes_all.txt").write_text("\n".join(sorted(cands)) + "\n", encoding="utf-8")
    print(f"候補 {len(cands)} 件 → work/prefs/causes_all.txt")


if __name__ == "__main__":
    main()
