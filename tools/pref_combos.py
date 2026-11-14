"""好みの文の「〜ゆえに」（"guineafowls for their social nature"）を組み合わせて作る。

ゲームは raw の [PREFSTRING:..] を使って「<生き物の複数形> for their <特徴>」という句を作る。
差し込みで始まる文テンプレート（"{1} for their {2}"）にすると、ふつうの文まで飲み込むので、
生き物ごとに実際にある組み合わせだけを辞書に書き出す。

使い方: python -I -X utf8 tools/pref_combos.py
出力: translations/prefs.tsv（build.py が読む）
"""
import csv
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAWS = ROOT.parent / "data" / "vanilla"
OUT = ROOT / "translations" / "prefs.tsv"


def load_terms():
    """英語 → 日本語（translations/*.tsv の2列の表）"""
    terms = {}
    for path in sorted((ROOT / "translations").glob("*.tsv")):
        if path.name in ("prefs.tsv", "sentences.tsv", "sentences-fix.tsv", "combat.tsv"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) == 2 and parts[0].strip() and parts[1].strip() not in ("", "-"):
                terms.setdefault(parts[0].strip().lower(), parts[1].strip())
    return terms


def load_creatures():
    """英語の呼び名 → 日本語（lookups/creatures.csv と plants.csv）"""
    names = {}
    for name in ("creatures.csv", "plants.csv"):
        path = ROOT / "data" / "lookups" / name
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) == 3 and row[1]:
                    names.setdefault(row[1].strip().lower(), row[2].strip())
    return names


def main():
    terms = load_terms()
    names = load_creatures()
    rows = []
    seen = set()
    for path in RAWS.rglob("objects/*.txt"):
        text = path.read_text(encoding="cp437", errors="replace")
        # [CREATURE:..] / [PLANT:..] ごとに、その中の [NAME:単数:複数:形容詞] と [PREFSTRING:..] を集める
        for block in re.split(r"(?=\[(?:CREATURE|PLANT):)", text):
            prefs = re.findall(r"\[PREFSTRING:([^\]]+)\]", block)
            if not prefs:
                continue
            plurals = set()
            for tag in ("NAME", "ALL_NAMES", "CASTE_NAME"):
                for m in re.finditer(r"\[" + tag + r":([^\]]+)\]", block):
                    parts = m.group(1).split(":")
                    plurals.add(parts[1] if len(parts) > 1 else parts[0])
            for plural in sorted(p.strip() for p in plurals if p.strip()):
                ja_name = names.get(plural.lower())
                if not ja_name:
                    continue
                for pref in prefs:
                    pref = pref.strip()
                    ja_pref = terms.get(pref.lower())
                    if not ja_pref:
                        continue
                    en = f"{plural} for their {pref}"
                    if en.lower() in seen:
                        continue
                    seen.add(en.lower())
                    rows.append((en, f"{ja_pref}ゆえに{ja_name}"))
    rows.sort()
    out = ["# 好みの「〜ゆえに」（tools/pref_combos.py が作る。直すときはスクリプトを直す）"]
    out += [f"{en}\t{ja}" for en, ja in rows]
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(rows)} 件")


if __name__ == "__main__":
    main()
