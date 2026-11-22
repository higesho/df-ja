"""art-forms.tsv のうち文（ピリオドで終わるもの）を、手直し（manual）の文テンプレートにも入れる。

文の訳は、単語辞書より先に文テンプレートが引かれる。自動で作ったテンプレートが先に当たって
常体の訳になるので、同じ文を manual で持って、そちらを使わせる。
"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])
TERMS = ROOT / "translations" / "art-forms.tsv"
FIX = ROOT / "translations" / "sentences-fix.tsv"
MARK = "# === 芸術の形式（まとまった文）==="

rows = []
for line in TERMS.read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    en, _, ja = line.partition("\t")
    if en.endswith((".", ":")) and " " in en:
        rows.append((en, ja))

old = FIX.read_text(encoding="utf-8")
if MARK in old:
    old = old[: old.index(MARK)].rstrip("\n") + "\n"
lines = [MARK, "# scratchpad/gen_art_sentences.py で作った（art-forms.tsv の文をそのまま写す）"]
for en, ja in rows:
    lines.append(f"manual\tcore\t{en}\t{ja}")
FIX.write_text(old + "\n".join(lines) + "\n", encoding="utf-8")
print(f"まとまった文 {len(rows)} 件")
