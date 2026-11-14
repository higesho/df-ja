"""翻訳作業の出力（work/done/<名前>_pNN.tsv）を検査して translations/ にまとめる。

  work/todo/ui_XX.txt    → translations/ui.tsv
  work/todo/terms_XX.txt → translations/terms.tsv

入力の行と出力の英語列が一致しない部分は取り込まず、報告する。
使い方: python tools/merge_done.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TODO = ROOT / "work" / "todo"
DONE = ROOT / "work" / "done"
TR = ROOT / "translations"
TOKEN = re.compile(r"\[[^\]]*\]|%[0-9.]*[sdif]")


def main():
    TR.mkdir(exist_ok=True)
    merged = {"ui": {}, "terms": {}}
    for todo in sorted(TODO.glob("*.txt")):
        kind = todo.stem.split("_")[0]
        src = [line.split("\t")[0] for line in todo.read_text(encoding="utf-8").splitlines() if line]
        got = {}
        for part in sorted(DONE.glob(f"{todo.stem}_p*.tsv")):
            for line in part.read_text(encoding="utf-8").splitlines():
                p = line.split("\t")
                if len(p) >= 2:
                    got[p[0]] = p[1].strip()
        missing = [s for s in src if s not in got]
        bad = [s for s in src if s in got and sorted(TOKEN.findall(s)) != sorted(TOKEN.findall(got[s]))]
        for s in src:
            if s in got and s not in bad:
                merged[kind][s] = got[s]
        print(f"{todo.name}: {len(src)} 行 / 訳あり {len(src) - len(missing)} / 欠落 {len(missing)} / トークン不一致 {len(bad)}")
        for s in bad[:5]:
            print(f"   ! {s!r} -> {got[s]!r}")
    for kind, d in merged.items():
        if d:
            (TR / f"{kind}.tsv").write_text("".join(f"{e}\t{j}\n" for e, j in d.items()), encoding="utf-8")
            print(f"translations/{kind}.tsv: {len(d)} 件")


if __name__ == "__main__":
    main()
