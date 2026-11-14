"""data/vanilla/vanilla_text の TEXT_SET（住民の発言、本の題名など）を翻訳用バッチにする。

[CONTEXT:...] [NAME] などのトークンを {1} {2} … にした本体（core）として書き出す。
出力: work/sentences/batches/txt_NNN.json（prepare.py の後に実行する）
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT.parent / "data" / "vanilla" / "vanilla_text" / "objects"
OUT = ROOT / "work" / "sentences" / "batches"
TOKEN = re.compile(r"\[[A-Z_]+(?::[A-Z_]+)*\]")

items = []
for p in sorted(SRC.glob("*.txt")):
    group = None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        m = re.fullmatch(r"\[TEXT_SET:([A-Z_]+)\]", line)
        if m:
            group = "txt_" + m.group(1).lower()
            continue
        if not group or not line or re.fullmatch(r"\[[^\]]*\]", line) or not re.search(r"[a-z]", line):
            continue
        slots = []

        def sub(m):
            slots.append(m.group(0))
            return "{" + str(len(slots)) + "}"

        text = TOKEN.sub(sub, line)
        items.append({"group": group, "kind": "core", "text": text, "slots": slots})

OUT.mkdir(parents=True, exist_ok=True)
for p in OUT.glob("txt_*.json"):
    p.unlink()
for i in range(0, len(items), 150):
    (OUT / f"txt_{i // 150:03d}.json").write_text(json.dumps(items[i:i + 150], ensure_ascii=False, indent=0), encoding="utf-8")
print(f"{len(items)} 行 → {OUT}")
