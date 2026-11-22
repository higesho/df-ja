"""MOD の raw ファイルから、日本語訳の雛形（dfint-ja/dictionary.csv）を作る。MOD 作者・翻訳者向け。

使い方: python tools/mod_template.py <MODのフォルダ> [出力先のdictionary.csv]
  → <MODのフォルダ>/dfint-ja/dictionary.csv（text,translation）
  → 出力先を指定すると、MOD のフォルダには書き込まない（翻訳パックを作るとき）
  - MOD が定義する名前（生き物・植物・素材・アイテム・建物・反応など）をすべて書き出す
  - dfint-ja 本体の辞書に訳がある語は、その訳を入れておく（そのままでよければ消してもよい）
  - 既に dictionary.csv があれば、書いてある訳は残し、新しい語だけ足す
"""
import csv
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from extract_raws import collect_terms  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    mod = pathlib.Path(sys.argv[1])
    if not (mod / "info.txt").exists():
        print(f"注意: {mod} に info.txt がありません（MOD のフォルダか確認してください）")
    terms = collect_terms(mod)
    known = {}
    simple = ROOT / "data" / "simple-dictionary.csv"
    if simple.exists():
        with simple.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                known[r["text"].lower()] = r["translation"]
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else mod / "dfint-ja" / "dictionary.csv"
    old = {}
    if out.exists():
        with out.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                old[r["text"]] = r["translation"]
    rows = dict(old)
    new = 0
    for en in sorted(terms):
        if en not in rows:
            rows[en] = known.get(en.lower(), "")
            new += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "translation"])
        for en, ja in rows.items():
            w.writerow([en, ja])
    blank = sum(1 for v in rows.values() if not v)
    print(f"{out}: {len(rows)} 語（新規 {new}、未翻訳 {blank}）")


if __name__ == "__main__":
    main()
