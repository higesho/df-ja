"""辞書にも文テンプレートにも訳が無い固定文字列（work/untranslated_msgids.json）から、
単独で表示されうるものを選び、Haiku 用のバッチ（work/ui2/batches/bNN.json）にする。

使い方: python tools/ui/prepare.py [1バッチの件数]
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 250
# 文章の中でしか単独で現れない語（エンジンの PARAGRAPH_WORDS と同じ）。訳すと単語ごとの描画で英語と混ざる
PARAGRAPH_WORDS = set("the to a an of and in is are you your for with it its this that be will can as at by on or from has have was if but into their".split())


def selectable(x):
    s = x.strip()
    if "\t" in x or "\n" in x or len(s) < 3:
        return False
    if x.startswith(" ") or (x.endswith(" ") and not x.rstrip().endswith((":", ".", "!", "?"))):
        return False  # 文の部品（前後をほかの文字列とつなげて使う）
    if s.lower() in PARAGRAPH_WORDS:
        return False
    if re.fullmatch(r"[a-z0-9_]+(:[a-z0-9_ ]+)+", s) or "__" in s or re.search(r"\b[a-z]+_[a-z_]+\b", s):
        return False  # 内部の識別子
    if re.fullmatch(r"\[[A-Z_]+(:[^\]]*)?\]", s) or re.fullmatch(r"[A-Z0-9_:]+", s):
        return False  # raw のタグ
    return bool(re.search(r"[A-Za-z]{2}", s))


def main():
    items = json.load(open(ROOT / "work" / "untranslated_msgids.json", encoding="utf-8"))
    items = sorted({x for x in items if selectable(x)}, key=lambda x: (len(x) > 60, x.lower()))
    out = ROOT / "work" / "ui2" / "batches"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("b*.json"):
        f.unlink()
    n = 0
    for i in range(0, len(items), SIZE):
        json.dump(items[i:i + SIZE], open(out / f"b{n:02d}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        n += 1
    print(f"{len(items)} 件 → {n} バッチ")


if __name__ == "__main__":
    main()
