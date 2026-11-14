"""ゲームの更新後、新しく取り出したバッチに、既存の訳（translations/sentences.tsv）を引き継ぐ。

関数のアドレス（group）は更新で変わるが、英語の部品はほとんど変わらない。
（kind, 英語）が一致する訳を新しい group に付け替えて work/sentences/out/carried.tsv に書く。
訳の無い部品だけが未翻訳として残るので、それを翻訳に回す。

使い方: 新しいバージョンで prepare.py / vanilla_text.py を実行した後に
        python tools/sentences/rekey.py
        python tools/sentences/merge.py
"""
import collections
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / "work" / "sentences"

old = collections.defaultdict(collections.Counter)
for name in ("sentences.tsv", "sentences-fix.tsv"):
    p = ROOT / "translations" / name
    if not p.exists():
        continue
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        g, k, en, ja = (line.split("\t") + [""])[:4]
        old[(k, en)][ja] += 3 if name == "sentences-fix.tsv" else 1

rows, carried, total = [], 0, 0
for p in sorted((WORK / "batches").glob("*.json")):
    for it in json.loads(p.read_text(encoding="utf-8")):
        total += 1
        cand = old.get((it["kind"], it["text"]))
        if cand:
            ja = cand.most_common(1)[0][0]
            rows.append(f'{it["group"]}\t{it["kind"]}\t{it["text"]}\t{ja}\n')
            carried += 1
(WORK / "out").mkdir(parents=True, exist_ok=True)
(WORK / "out" / "carried.tsv").write_text("".join(rows), encoding="utf-8")
print(f"引き継ぎ {carried} / {total}（残り {total - carried} 件が新規の翻訳対象）")
