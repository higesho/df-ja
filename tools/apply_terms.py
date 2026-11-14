"""用語の置き換え規則（translations/term-rules.tsv）を ui.tsv / terms.tsv / harvested.tsv に適用する。

term-rules.tsv の形式（# で始まる行はコメント）:
  英語の正規表現<TAB>古い訳語<TAB>新しい訳語
英語の原文が正規表現に（大文字小文字を区別せず）当てはまり、かつ訳に古い訳語が含まれる行だけを書き換える。
英語で文脈を絞るので、「指定」のように別の意味でも使われる語を巻き込みにくい。

使い方:
  python tools/apply_terms.py          書き換えて、変更点を work/term-changes.tsv に出す
  python tools/apply_terms.py --dry    書き換えずに変更点だけ出す
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TR = ROOT / "translations"
TARGETS = ["ui.tsv", "terms.tsv", "harvested.tsv"]


def load_rules():
    rules = []
    for n, line in enumerate((TR / "term-rules.tsv").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("\t")
        if len(p) < 3:
            sys.exit(f"term-rules.tsv:{n}: 列が足りません: {line!r}")
        rules.append((re.compile(p[0], re.I), p[1], p[2]))
    return rules


def replace_outside(text, old, new):
    """text 中の old を new に置き換える。ただし既に new の一部になっている old（彫像の「像」など）は触らない。"""
    if old in new:
        parts = text.split(new)
        return new.join(p.replace(old, new) for p in parts)
    return text.replace(old, new)


def main():
    dry = "--dry" in sys.argv
    rules = load_rules()
    changes = []
    for name in TARGETS:
        path = TR / name
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            p = line.split("\t")
            if len(p) >= 2 and not line.startswith("#"):
                en, ja = p[0], p[1]
                new = ja
                for rx, old, rep in rules:
                    if old in new and rx.search(en):
                        new = replace_outside(new, old, rep)
                if new != ja:
                    changes.append((name, en, ja, new))
                    p[1] = new
                    line = "\t".join(p)
            out.append(line)
        if not dry:
            path.write_text("".join(l + "\n" for l in out), encoding="utf-8")
    log = ROOT / "work" / "term-changes.tsv"
    log.parent.mkdir(exist_ok=True)
    log.write_text("".join(f"{a}\t{b}\t{c}\t{d}\n" for a, b, c, d in changes), encoding="utf-8")
    print(f"{'（試行）' if dry else ''}変更 {len(changes)} 行 → {log}")


if __name__ == "__main__":
    main()
