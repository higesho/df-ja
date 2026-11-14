"""ゲームの raw ファイルから、画面に出る英語の名前を抽出する。

出力: dfint-ja/work/raw_terms.csv  (en, kind, objects)
  en      : 英語の名前（小文字のまま）
  kind    : 名前の種類（creature / plant / material / item / building / reaction / bodypart / color / shape / position ...）
  objects : その名前を使っている raw オブジェクト ID（最大3件、参考用）

使い方: python tools/extract_raws.py [ゲームフォルダ]
"""
import csv
import pathlib
import re
import sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
GAME = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent
VANILLA = GAME / "data" / "vanilla"
OUT = ROOT / "work" / "raw_terms.csv"

TOKEN = re.compile(r"\[([^\[\]]+)\]")

# オブジェクト定義のタグ → 種類
OBJECT_TAGS = {
    "CREATURE": "creature", "PLANT": "plant", "INORGANIC": "material",
    "MATERIAL_TEMPLATE": "material", "TISSUE_TEMPLATE": "material",
    "ITEM_WEAPON": "item", "ITEM_ARMOR": "item", "ITEM_HELM": "item", "ITEM_GLOVES": "item",
    "ITEM_SHOES": "item", "ITEM_PANTS": "item", "ITEM_SHIELD": "item", "ITEM_AMMO": "item",
    "ITEM_SIEGEAMMO": "item", "ITEM_TRAPCOMP": "item", "ITEM_TOOL": "item", "ITEM_TOY": "item",
    "ITEM_INSTRUMENT": "item", "ITEM_FOOD": "item",
    "BUILDING_WORKSHOP": "building", "BUILDING_FURNACE": "building",
    "REACTION": "reaction", "BODY": "bodypart",
    "COLOR": "color", "SHAPE": "shape", "COLOR_PATTERN": "pattern",
    "ENTITY": "entity", "CREATURE_VARIATION": None, "BODY_DETAIL_PLAN": None,
    "INTERACTION": None, "LANGUAGE": None, "WORD": None, "SYMBOL": None, "TRANSLATION": None,
    "MUSIC": None, "SOUND": None,
}

# [OBJECT:xxx] ごとに、オブジェクトを定義するタグとして認めるもの
OBJECT_TYPES = {
    "CREATURE": {"CREATURE"}, "PLANT": {"PLANT"}, "INORGANIC": {"INORGANIC"},
    "MATERIAL_TEMPLATE": {"MATERIAL_TEMPLATE"}, "TISSUE_TEMPLATE": {"TISSUE_TEMPLATE"},
    "ITEM": {t for t in OBJECT_TAGS if t.startswith("ITEM_")},
    "BUILDING": {"BUILDING_WORKSHOP", "BUILDING_FURNACE"}, "REACTION": {"REACTION"},
    "BODY": {"BODY"}, "DESCRIPTOR_COLOR": {"COLOR"}, "DESCRIPTOR_SHAPE": {"SHAPE"},
    "DESCRIPTOR_PATTERN": {"COLOR_PATTERN"}, "ENTITY": {"ENTITY"},
}

# 名前を表すタグ → 値として使う引数の位置
NAME_TAGS = {
    "NAME": None,  # 全引数（ただし数字や大文字トークンは除く）
    "NAME_PLURAL": None, "ADJ": None, "ALL_NAMES": None,
    "CASTE_NAME": None, "GENERAL_CHILD_NAME": None, "GENERAL_BABY_NAME": None,
    "BABYNAME": None, "CHILDNAME": None,
    "STATE_NAME": [1], "STATE_ADJ": [1], "STATE_NAME_ADJ": [1],
    "SEED": [0, 1], "GROWTH_NAME": None, "TISSUE_NAME": None,
    "TREE_HAS_MALE_AND_FEMALE": None,
    "BP": [2, 3], "MALE_NAME": None, "FEMALE_NAME": None, "SPOUSE": None,
    "NAME_MALE": None, "NAME_FEMALE": None,
    "PLURAL_NAME": None, "ADJECTIVE": None,
    "PREFSTRING": None,
    "IS_GEM": [0, 1],  # 宝石の名前と複数形（STP は SKIP_VALUE で除く）
}
SKIP_VALUE = re.compile(r"^(STP|NP|NONE|[A-Z0-9_]+|-?\d+)$")


def collect_terms(root):
    """root 以下の objects/*.txt から名前を集める。{英語: {"kinds": set, "objects": [...]}}"""
    terms = defaultdict(lambda: {"kinds": set(), "objects": []})
    for path in sorted(pathlib.Path(root).rglob("objects/*.txt")):
        text = path.read_text(encoding="cp437", errors="replace")
        kind, obj_id = None, None
        in_position = False
        allowed = set()
        for m in TOKEN.finditer(text):
            parts = m.group(1).split(":")
            tag, args = parts[0], parts[1:]
            if tag == "OBJECT":
                allowed = OBJECT_TYPES.get(args[0] if args else "", set())
                kind, obj_id = None, None
                continue
            if tag in allowed and args:
                kind, obj_id = OBJECT_TAGS[tag], f"{tag}:{args[0]}"
                in_position = False
                continue
            if tag == "POSITION" and kind == "entity":
                in_position, obj_id = True, f"POSITION:{args[0] if args else ''}"
                continue
            if kind is None or tag not in NAME_TAGS:
                continue
            if kind == "entity" and not in_position:
                continue
            if tag == "PREFSTRING":
                sub = "prefstring"
            elif kind == "entity":
                sub = "position"
            else:
                sub = kind
            idx = NAME_TAGS[tag]
            values = [args[i] for i in idx if i < len(args)] if idx else args
            for v in values:
                v = v.strip()
                if not v or SKIP_VALUE.match(v) or not re.search(r"[a-z]", v):
                    continue
                t = terms[v]
                t["kinds"].add(sub)
                if obj_id and len(t["objects"]) < 3 and obj_id not in t["objects"]:
                    t["objects"].append(obj_id)
    return terms


def main():
    terms = collect_terms(VANILLA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["en", "kind", "objects"])
        for en in sorted(terms, key=lambda s: (sorted(terms[s]["kinds"])[0], s)):
            t = terms[en]
            w.writerow([en, "|".join(sorted(t["kinds"])), " ".join(t["objects"])])
    print(f"{len(terms)} 件を書き出しました: {OUT}")


if __name__ == "__main__":
    main()
