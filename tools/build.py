"""翻訳ソース（translations/*.tsv）から、エンジンが読む dfint-data 用の CSV を生成する。

入力（優先度の高い順。同じ英語があれば上が勝つ）:
  translations/overrides.tsv   手で直した訳
  translations/wiki-terms.tsv  日本語Wikiの訳語（用語単体の訳）
  translations/harvested.tsv   ログから集めた未翻訳文字列の訳
  translations/ui.tsv          実行ファイル内の UI 文字列
  translations/terms.tsv       raw ファイル由来の名前（基本語）
  work/raw_terms.csv           raw 名の一覧（派生語の生成と分類に使う）

出力:
  data/simple-dictionary.csv   完全一致辞書（text,translation）
  data/lookups/*.csv           組み立て型ルックアップ（table,text,translation）

使い方: python tools/build.py
"""
import csv
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from terms import resolve, split_terms  # noqa: E402

TR = ROOT / "translations"
DATA = ROOT / "data"
TOKEN = re.compile(r"\[[A-Z/][A-Z0-9_:/.\-]*\]|%[0-9.]*[sdif]|\{[^}]*\}")  # ゲームのトークン（[C:7:0:1] [B] など）。[Completed] のような普通の語は除く

# 実行ファイルが組み立てる汎用アイテム名（raw には無い）。単数/複数どちらも同じ訳
BUILTIN_ITEM_NOUNS = {
    "coin": "硬貨", "coins": "硬貨", "backpack": "背嚢", "backpacks": "背嚢", "quiver": "矢筒", "quivers": "矢筒", "waterskin": "水袋", "waterskins": "水袋",
    "flask": "フラスコ", "flasks": "フラスコ", "bag": "袋", "bags": "袋", "vial": "小瓶", "vials": "小瓶",
    "bar": "延べ棒", "bars": "延べ棒", "block": "ブロック", "blocks": "ブロック",
    "boulder": "丸石", "boulders": "丸石", "log": "丸太", "logs": "丸太",
    "door": "扉", "doors": "扉", "floodgate": "水門", "floodgates": "水門",
    "hatch cover": "ハッチ", "hatch covers": "ハッチ", "grate": "格子", "grates": "格子",
    "bed": "ベッド", "beds": "ベッド", "table": "テーブル", "tables": "テーブル",
    "chair": "椅子", "chairs": "椅子", "throne": "玉座", "thrones": "玉座",
    "cabinet": "キャビネット", "cabinets": "キャビネット", "chest": "宝箱", "chests": "宝箱",
    "coffer": "小箱", "coffers": "小箱", "box": "箱", "boxes": "箱",
    "barrel": "樽", "barrels": "樽", "bin": "収納箱", "bins": "収納箱",
    "bucket": "バケツ", "buckets": "バケツ", "bag": "袋", "bags": "袋",
    "cage": "檻", "cages": "檻", "chain": "鎖", "chains": "鎖", "rope": "ロープ", "ropes": "ロープ",
    "statue": "彫像", "statues": "彫像", "coffin": "棺桶", "coffins": "棺桶",
    "sarcophagus": "石棺", "sarcophagi": "石棺", "casket": "棺", "caskets": "棺",
    "slab": "平板", "slabs": "平板", "mechanism": "仕掛け", "mechanisms": "仕掛け",
    "window": "窓", "windows": "窓", "armor stand": "鎧立て", "armor stands": "鎧立て",
    "weapon rack": "武器立て", "weapon racks": "武器立て", "quern": "石臼", "querns": "石臼",
    "millstone": "ひき臼", "millstones": "ひき臼", "anvil": "金床", "anvils": "金床",
    "flask": "フラスコ", "flasks": "フラスコ", "vial": "小瓶", "vials": "小瓶",
    "waterskin": "水袋", "waterskins": "水袋", "goblet": "ゴブレット", "goblets": "ゴブレット",
    "mug": "マグ", "mugs": "マグ", "cup": "カップ", "cups": "カップ",
    "crown": "王冠", "crowns": "王冠", "ring": "指輪", "rings": "指輪",
    "earring": "耳飾り", "earrings": "耳飾り", "bracelet": "腕輪", "bracelets": "腕輪",
    "amulet": "首飾り", "amulets": "首飾り", "scepter": "笏", "scepters": "笏",
    "figurine": "小像", "figurines": "小像", "gem": "宝石", "gems": "宝石",
    "cut gem": "カットされた宝石", "cut gems": "カットされた宝石",
    "rough gem": "原石", "rough gems": "原石", "large gem": "大きな宝石", "large gems": "大きな宝石",
    "cloth": "布", "thread": "糸", "threads": "糸", "yarn": "毛糸",
    "pipe section": "パイプ", "pipe sections": "パイプ", "tube": "管", "tubes": "管",
    "corkscrew": "コルク抜き", "pedestal": "台座", "pedestals": "台座",
    "totem": "トーテム", "totems": "トーテム", "corpse": "死体", "corpses": "死体",
    "remains": "遺骸", "skull": "頭蓋骨", "skulls": "頭蓋骨", "bones": "骨",
    "meat": "肉", "fat": "脂肪", "tallow": "獣脂", "leather": "革", "skin": "皮",
    "hide": "皮", "hides": "皮", "egg": "卵", "eggs": "卵", "seeds": "種", "seed": "種",
    "fish": "魚", "cheese": "チーズ", "milk": "乳", "honey": "蜂蜜", "flour": "粉",
    "sugar": "砂糖", "oil": "油", "soap": "石鹸", "wax": "蝋", "paper": "紙",
    "dye": "染料", "powder": "粉末", "ash": "灰", "potash": "肥料", "pearlash": "パールアッシュ",
    "lye": "灰汁", "coke": "コークス", "charcoal": "木炭", "glass": "ガラス",
    "book": "本", "books": "本", "scroll": "巻物", "scrolls": "巻物", "codex": "写本",
    "quire": "折丁", "quires": "折丁", "sheet": "紙", "sheets": "紙",
    "ammo": "弾薬", "trap component": "罠部品", "trap components": "罠部品",
}

# 素材名の後ろに付く部位・状態（"cow leather" → 牛の革 などの組み立て用）
# 遺骸・鎖かたびら・罠の部品など、raw から拾えない品物の名前
EXTRA_ITEM_NOUNS = {
    "skeleton": "骸骨", "mangled corpse": "損壊した死体", "mangled corpses": "損壊した死体",
    "mangled skeleton": "損壊した骸骨", "mangled skeletons": "損壊した骸骨",
    "partial skeleton": "部分的な骸骨", "partial skeletons": "部分的な骸骨",
    "web": "糸の巣", "webs": "糸の巣",
    "chain mail": "鎖帷子", "chain shirt": "鎖のシャツ", "chain leggings": "鎖のレギンス",
    "chain hood": "鎖の頭巾", "chain greaves": "鎖のすね当て",
    "serrated disc": "鋸状の円盤", "serrated discs": "鋸状の円盤",
    "corkscrew": "コルク栓抜き", "corkscrews": "コルク栓抜き",
    "spiked ball": "棘付きの球", "spiked balls": "棘付きの球",
    "axe blade": "斧刃", "axe blades": "斧刃",
    "splint": "副木", "splints": "副木", "crutch": "松葉杖", "crutches": "松葉杖",
    "cast": "ギプス", "casts": "ギプス", "traction bench": "牽引台", "traction benches": "牽引台",
}

# 容れ物に入れる中身の種類（備蓄の分類。"Meat Barrel" / "Fish Barrel"）
CONTAINER_FOR = {
    "fish": "魚", "food": "食料", "drink": "飲み物", "plant": "植物", "refuse": "ごみ",
    "finished goods": "完成品", "furniture": "家具", "weapon": "武器", "armor": "鎧",
    "ammo": "弾", "coin": "硬貨", "stone": "石", "wood": "木材", "bar": "延べ棒",
    "gem": "宝石", "animal": "動物", "corpse": "死体", "sheet": "紙", "cloth": "布",
}

# 容れ物の名前（"<中身> Bag (<材質>)" の真ん中）
CONTAINER_NOUNS = {
    "bag": "袋", "bags": "袋", "barrel": "樽", "barrels": "樽", "bin": "収納箱", "bins": "収納箱",
    "pot": "壺", "pots": "壺", "box": "箱", "boxes": "箱", "chest": "宝箱", "chests": "宝箱",
    "coffer": "小箱", "coffers": "小箱", "cage": "檻", "cages": "檻", "bucket": "バケツ", "buckets": "バケツ",
    "backpack": "背嚢", "backpacks": "背嚢", "quiver": "矢筒", "quivers": "矢筒",
    "waterskin": "水袋", "waterskins": "水袋", "flask": "フラスコ", "flasks": "フラスコ",
    "vial": "小瓶", "vials": "小瓶", "jug": "水差し", "jugs": "水差し",
}

MATERIAL_SUFFIXES = {
    "leather": "革", "bone": "骨", "bones": "骨", "skin": "皮", "hair": "毛", "wool": "羊毛",
    "fat": "脂肪", "tallow": "獣脂", "meat": "肉", "shell": "殻", "horn": "角", "ivory": "象牙",
    "tooth": "歯", "teeth": "歯", "hoof": "蹄", "chitin": "キチン", "scale": "鱗", "feather": "羽",
    "silk": "絹", "blood": "血", "ichor": "体液", "milk": "乳", "cheese": "チーズ", "egg": "卵",
    "soap": "石鹸", "wood": "材", "fiber": "繊維", "thread": "糸", "cloth": "布", "yarn": "毛糸",
    "ash": "灰", "charcoal": "木炭", "flour": "粉", "oil": "油", "seed": "種", "seeds": "種",
    "leaf": "葉", "leaves": "葉", "flower": "花", "flowers": "花", "fruit": "実", "nut": "木の実",
    "paper": "紙", "slurry": "どろどろ", "dye": "染料", "sugar": "砂糖", "syrup": "シロップ",
    "wax": "蝋", "venom": "毒", "extract": "エキス", "tissue": "組織", "nail": "爪", "claw": "鉤爪",
    # 内臓（冒険者の食べ物 "wombat tripe"）
    "tripe": "胃袋", "liver": "レバー", "lungs": "肺", "lung": "肺", "heart": "心臓", "brain": "脳", "kidney": "腎臓",
    "parchment": "羊皮紙", "sweetbread": "胸腺", "intestines": "腸", "gizzard": "砂肝", "spleen": "脾臓", "pancreas": "膵臓", "eye": "目玉",
}

# 地形タイルの名前の後半（"<素材> wall" など）
TERRAIN_SUFFIXES = {
    "wall": "壁", "floor": "床", "ramp": "傾斜路", "pillar": "柱", "fortification": "防護壁",
    "up stair": "上り階段", "down stair": "下り階段", "up/down stair": "上下階段",
    "boulder": "丸石", "pebbles": "小石", "cavern wall": "洞窟の壁", "cavern floor": "洞窟の床",
    # 木（"Pecan tree Sapling" / "Snow-covered Oak Branches"）
    "sapling": "の苗木", "shrub": "の低木", "stump": "の切り株", "trunk branch": "の幹枝",
    "branches": "の枝", "twigs": "の小枝", "root": "の根", "fallen leaves": "の落ち葉",
}

# タイルの名前に付く形容詞（"Rough Microcline Wall" → 荒削りの微斜長石の壁）
TERRAIN_ADJS = {
    "rough": "荒削りの", "smooth": "滑らかな", "snow-covered": "雪に覆われた",
    "damp": "湿った", "dry": "乾いた", "muddy": "泥だらけの", "mossy": "苔むした",
    "furrowed": "畝の立った", "engraved": "彫刻された", "exposed": "露出した",
    "dead": "枯れた", "dense": "密生した", "sparse": "まばらな",
    "waterlogged": "水浸しの", "frozen": "凍った", "glowing": "光る",
}

# 地面に薄く積もった・付いたもの（実行ファイルの "A dusting of " など）
TERRAIN_COATS = {
    "a dusting of": "うっすらと積もった", "a thin layer of": "薄く積もった",
    "a smear of": "こびりついた", "a spattering of": "飛び散った",
}

# スキルの熟練度（日本語Wikiの訳語）。"Proficient Miner" → 鉱夫（達人）
SKILL_LEVELS = {
    "Dabbling": "生かじり", "Novice": "未熟者", "Adequate": "十分", "Competent": "優秀",
    "Skilled": "熟練", "Proficient": "達人", "Talented": "有能", "Adept": "名人",
    "Expert": "専門家", "Professional": "プロ", "Accomplished": "熟達", "Great": "偉大",
    "Master": "マスター", "High Master": "ハイマスター", "Grand Master": "グランドマスター",
    "Legendary": "伝説的",
}
# スキルを持つ人の呼び名。訳は辞書から引き、辞書に無いものだけここに書く
SKILL_NAMES = {
    "Miner": None, "Appraiser": None, "Woodcutter": None, "Wood Cutter": "木こり", "Carpenter": None,
    "Mason": None, "Stonecutter": None, "Stone Carver": None, "Planter": None, "Woodworker": None, "Stoneworker": None, "Metalsmith": None, "Jeweler": None, "Craftsdwarf": None, "Farmer": None, "Engineer": None, "Doctor": None, "Hunter": None, "Ranger": None, "Fishery Worker": None, "Administrator": None, "Recordkeeper": "記録管理人", "Cheesemaker": "チーズ職人", "Discipline": None, "Reader": "読書家", "Observer": None, "Climber": None, "Engraver": None, "Brewer": None, "Cook": None, "Fisherdwarf": None,
    "Grower": "栽培者", "Herbalist": None, "Butcher": None, "Tanner": None, "Weaver": None,
    "Clothier": None, "Wood Crafter": "木工職人", "Stone Crafter": None, "Bowyer": None,
    "Mechanic": None, "Architect": "建築家", "Swordsdwarf": "剣士", "Axedwarf": "斧使い",
    "Macedwarf": "メイス使い", "Hammerdwarf": "ハンマー使い", "Speardwarf": "槍使い",
    "Marksdwarf": "射手", "Crossbowdwarf": "クロスボウ使い", "Bowdwarf": "弓使い",
    "Pikedwarf": "長槍使い", "Wrestler": None, "Fighter": None, "Dodger": None,
    "Armorsmith": None, "Weaponsmith": None, "Furnace Operator": None, "Glassmaker": None,
    "Leatherworker": None, "Bone Carver": None, "Gem Cutter": "宝石研磨師", "Gem Setter": None,
    "Negotiator": None, "Judge of Intent": "意図の判定者", "Persuader": None, "Liar": None,
    "Conversationalist": None, "Comedian": None, "Flatterer": None, "Consoler": None,
    "Pacifier": "なだめ役", "Record Keeper": None, "Organizer": None, "Leader": None,
    "Teacher": None, "Student": None, "Diagnoser": "診断医", "Surgeon": None,
    "Wound Dresser": None, "Suturer": None, "Bone Doctor": "骨接ぎ医", "Ambusher": None, "Observer": None,
    "Shield User": None, "Armor User": None, "Climber": None, "Swimmer": None, "Dancer": None,
    "Musician": None, "Poet": None, "Writer": None, "Siege Engineer": None, "Siege Operator": None,
    "Pump Operator": "ポンプ操作員", "Animal Trainer": None, "Animal Caretaker": None,
    "Trapper": None, "Milker": None, "Cheese Maker": "チーズ職人", "Miller": None,
    "Thresher": None, "Presser": None, "Soap Maker": None, "Potash Maker": None, "Lye Maker": None,
    "Wax Worker": None, "Dyer": None, "Strand Extractor": "繊維抽出者", "Fish Cleaner": None,
    "Fish Dissector": None, "Animal Dissector": None, "Metal Crafter": None, "Metalsmith": None,
    "Beekeeper": None, "Papermaker": None, "Bookbinder": None, "Gelder": None, "Knapper": None,
    "Lasher": None, "Blowgunner": None, "Kicker": None, "Biter": None, "Striker": None,
    "Thrower": None, "Knife User": "ナイフ使い", "Spinner": "糸紡ぎ", "Mathematician": "数学者",
    "Astronomer": "天文学者", "Chemist": "化学者", "Geographer": "地理学者",
    "Optics Engineer": "光学技術者", "Fluid Engineer": "流体技術者", "Alchemist": "錬金術師",
    "Caster": "鋳造工", "Firearm User": "銃使い", "Crutch Walker": "松葉杖使い",
}
# 冒険者・人物画面で使う呼び名（ゲーム本体の一覧から。訳は辞書から引く）
for _n in ("Rider|Negotiator|Persuader|Intimidator|Fisherman|Tracker|Swordsman|Axeman|Hammerman|"
           "Maceman|Crossbowman|Spearman|Bowman|Pikeman|Percussionist|Wind Instrumentalist|Logician|"
           "Critical Thinker|Tactician|Archer|Wordsmith|Speaker|Singer|Stringed Instrumentalist|"
           "Keyboardist|Soaper|Wood Burner|Blacksmith|Woodcrafter|Potter|Shearer|Misc. Object User|"
           "Crutch-walker|Schemer|Glazer|Druid").split("|"):
    SKILL_NAMES.setdefault(_n, None)


def read_tsv(path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] and parts[1]:
            out[parts[0]] = parts[1]
    return out


def tokens_ok(en, ja):
    return sorted(TOKEN.findall(en)) == sorted(TOKEN.findall(ja))


def strip_no(ja):
    return ja[:-1] if ja.endswith("の") else ja


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    sources = ["overrides.tsv", "persona.tsv", "values.tsv", "prefs.tsv", "thought-causes.tsv", "bodyparts.tsv", "gems.tsv", "wiki-terms.tsv", "harvested.tsv", "ui.tsv", "ui-extra.tsv", "ui-extra2.tsv", "dfhack.tsv", "raw-descriptions.tsv", "terms.tsv", "beast-terms.tsv", "build-phrases.tsv"]
    ja = {}
    rank = {}  # 英語ごとの出典の優先度（小さいほど優先）
    rejected = []
    for i, name in reversed(list(enumerate(sources))):  # 優先度の低い順に入れ、上書きさせる
        for en, tr in read_tsv(TR / name).items():
            if not tokens_ok(en, tr):
                rejected.append((name, en, tr))
                continue
            ja[en] = tr
            rank[en] = i
            # ドワーフ以外の人物では "craftsdwarfship" が "craftsmanship" になる
            if "craftsdwarfship" in en:
                alt = en.replace("craftsdwarfship", "craftsmanship")
                ja[alt] = tr
                rank[alt] = i
    # 体の部位は単数・複数のどちらでも出る（"drums his fingers" / "chews on his lip"）ので、
    # 足りないほうを同じ訳で足す。辞書にあるものは上書きしない
    for en, tr in list(read_tsv(TR / "bodyparts.tsv").items()):
        if not tokens_ok(en, tr):
            continue
        forms = []
        if en.endswith(("s", "x", "ch", "sh")):
            forms.append(en + "es")
        elif en.endswith("y") and len(en) > 2 and en[-2] not in "aeiou":
            forms.append(en[:-1] + "ies")
        else:
            forms.append(en + "s")
        if en.endswith("ies"):
            forms.append(en[:-3] + "y")
        elif en.endswith("es"):
            forms.append(en[:-2])
            forms.append(en[:-1])
        elif en.endswith("s"):
            forms.append(en[:-1])
        for alt in forms:
            if len(alt) > 2:
                ja.setdefault(alt, tr)
                rank.setdefault(alt, len(sources))
    # 獣人の名前（"were" + 生き物。creatures.lua の werebeast）。
    # 1語なので組み立て型の表では受けられず、辞書に入れる
    pg_were = TR / "procgen-names.tsv"
    if pg_were.exists():
        n_were = 0
        for line in pg_were.read_text(encoding="utf-8").splitlines():
            cols = line.split("	")
            if line.startswith("#") or len(cols) != 3 or cols[0] != "rcp" or not cols[2].strip():
                continue
            en, tr = cols[1].strip(), cols[2].strip()
            for form in (f"were{en}", f"were{en}s"):
                ja.setdefault(form, f"ワー{tr}")
                rank.setdefault(form, len(sources))
                n_were += 1
        print(f"獣人の名前: {n_were} 件")

    # 欲求タブの文 "She is not distracted after being away from people." / "Overall, she is somewhat focused with satisfied needs."
    needs = {"state": {}, "need": {}, "overall": {}}
    np_ = TR / "needs.tsv"
    if np_.exists():
        for line in np_.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) == 3 and p[0] in needs:
                needs[p[0]][p[1]] = p[2]
    subjects = [("He", "彼"), ("She", "彼女"), ("It", "それ"), ("They", "彼ら"), ("You", "あなた")]
    for subj, sj in subjects:
        be = "are" if subj in ("They", "You") else "is"
        for st, stj in needs["state"].items():
            for nd, ndj in needs["need"].items():
                k = f"{subj} {be} {st} {nd}."
                ja.setdefault(k, f"{sj}は{ndj}、{stj}。")
                rank.setdefault(k, len(sources))
        for ov, ovj in needs["overall"].items():
            k = f"Overall, {subj.lower()} {be} {ov}."
            ja.setdefault(k, f"全体として、{sj}は{ovj}。")
            rank.setdefault(k, len(sources))

    raw = {r["en"]: r for r in csv.DictReader((ROOT / "work" / "raw_terms.csv").open(encoding="utf-8"))}
    _, derived = split_terms(raw)
    raw_ja = {}
    for en in raw:
        tr = resolve(en, ja, derived)
        if tr:
            raw_ja[en] = tr

    # 1) 完全一致辞書（エンジンは小文字で照合する）
    simple = {}
    # 大文字小文字だけ違う英語が複数あるときは、優先度の高い出典の訳を使う
    by_rank = sorted(ja.items(), key=lambda kv: rank[kv[0]])
    for en, tr in by_rank + list(raw_ja.items()) + list(BUILTIN_ITEM_NOUNS.items()):
        if en == tr:
            continue
        simple.setdefault(en.lower(), (en, tr))
    # 前後に空白がある英語（実行ファイルの文の部品 "… Workshops[C:7:0:0]. "）は、空白を落とした形でも引けるようにする。
    # 文章（マークアップ）の中では、文ごとに前後の空白を落としてから辞書を引くため
    for key, (en, tr) in list(simple.items()):
        s = en.strip()
        if s != en and len(s) >= 12 and " " in s and s.lower() not in simple:
            simple[s.lower()] = (s, tr.strip())
    # 文の間の空白2つ（".  "）は、文章（マークアップ）の中では1つにまとめられる。1つにした形でも引けるようにし、
    # さらに文の数と「。」の数が合うものは1文ずつにも分けて入れる（文章は文ごとに辞書を引くため）
    sent_end_en = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\[])")
    sent_end_ja = re.compile(r"(?<=[。！？])")
    for key, (en, tr) in list(simple.items()):
        if "  " not in en and not sent_end_en.search(en):
            continue
        one = re.sub(r"(?<=[.!?:]) {2,}", " ", en.strip())
        if one != en and one.lower() not in simple:
            simple[one.lower()] = (one, tr)
        es = [x for x in sent_end_en.split(en.strip()) if x.strip()]
        js = [x for x in sent_end_ja.split(tr.strip()) if x.strip()]
        if len(es) > 1 and len(es) == len(js):
            for e1, j1 in zip(es, js):
                if len(e1) >= 12 and e1.lower() not in simple:
                    simple[e1.lower()] = (e1.strip(), j1.strip())
    write_csv(DATA / "simple-dictionary.csv", ["text", "translation"], sorted(simple.values(), key=lambda r: r[0].lower()))

    # 2) ルックアップ
    def kinds(en):
        return set(raw[en]["kind"].split("|"))

    creatures = sorted((en, tr) for en, tr in raw_ja.items() if "creature" in kinds(en))
    plants = sorted((en, tr) for en, tr in raw_ja.items() if "plant" in kinds(en))
    materials = sorted((en, tr) for en, tr in raw_ja.items() if kinds(en) & {"material", "plant"})
    # 要塞の家畜（"stray yak bull" / 知らせでは "Stray Yak Bull"）。生き物ごとに「野良〜」を辞書に足す。
    # 手で書いた分（野良犬など）は上書きしない
    # 生き物の表には乳や革などの産物の名前も入っているので、それは外す
    products = ("cheese", "milk", "leather", "bone", "skull", "tooth", "teeth", "horn", "hoof", "wool", "hair",
                "silk", "extract", "blood", "fat", "tallow", "brain", "heart", "liver", "lung", "meat", "eye",
                "nail", "scale", "shell", "powder", "soap", "parchment", "ivory", "tail", "wax", "egg")
    for en, tr in creatures:
        if any(w in en.lower() for w in products):
            continue
        key = f"stray {en}"
        if key.lower() not in simple:
            simple[key.lower()] = (key, f"野良{tr}")
    # 好みの画面の布（"hemp fabric"）。素材・植物ごとに「〜の布」を辞書に足す
    for en, tr in materials:
        key = f"{en} fabric"
        if key.lower() not in simple:
            simple[key.lower()] = (key, f"{tr}の布")
    # 体や品物に付いた汚れ（持ち物の一覧の "water covering"）。素材ごとに「〜まみれ」を辞書に足す
    for en, tr in materials:
        key = f"{en} covering"
        if key.lower() not in simple:
            simple[key.lower()] = (key, f"{tr}まみれ")
    items = sorted((en, tr) for en, tr in raw_ja.items() if "item" in kinds(en))
    items += sorted(BUILTIN_ITEM_NOUNS.items())
    items += sorted(EXTRA_ITEM_NOUNS.items())
    # 左右のある身に着ける物（"troll leather right glove"）
    for en, tr in list(items):
        if en in ("glove", "gloves", "gauntlet", "gauntlets", "mitten", "mittens", "boot", "boots", "high boot", "high boots",
                  "low boot", "low boots", "shoe", "shoes", "sock", "socks", "sandal", "sandals", "chausse", "chausses"):
            items += [("right " + en, "右の" + tr), ("left " + en, "左の" + tr)]

    # 世界生成で組み立てられる名前の部品（怪物・神の材質）。
    # 語彙は data/vanilla/vanilla_procedural/scripts/generators/ に決まっていて、
    # 組み合わせだけが世界ごとに変わるので、組み立て型のテーブルで受ける
    pg = {k: [] for k in ("kind", "spouse", "end", "adj", "mat", "sadj", "snoun", "rcp", "mythadj", "mythnoun", "divine")}
    pg_path = TR / "procgen-names.tsv"
    if pg_path.exists():
        for line in pg_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            cols = line.split("	")
            if len(cols) != 3 or cols[0] not in pg or not cols[2].strip():
                continue
            pg[cols[0]].append((cols[1].strip(), cols[2].strip()))

    lookups = DATA / "lookups"
    if lookups.exists():
        for p in lookups.glob("*.csv"):
            p.unlink()
    H = ["table", "text", "translation"]
    write_csv(lookups / "00-index.csv", H, [
        ["", "{CREATURE}", "{CREATURE}"],
        ["", "{PLANT}", "{PLANT}"],
        ["", "{MATERIAL}", "{MATERIAL}"],
        ["", "{ITEM}", "{ITEM}"],
        ["", "{TERRAIN}", "{TERRAIN}"],
        ["", "{SKILL}", "{SKILL}"],
        ["", "{PERSON}", "{PERSON}"],
        ["", "{MONSTER}", "{MONSTER}"],
        ["", "{CONTAINER}", "{CONTAINER}"],
        ["", "{GEM}", "{GEM}"],
    ])
    # ゲームは複数形を素直に "s" を足して作ることがある（"giant walrus" → "giant walruss"、
    # "forgotten beast" → "forgotten beasts"）。raw に複数形が無いものだけ足す
    def with_plain_plural(pairs):
        known = {en for en, _ in pairs}
        out = list(pairs)
        for en, tr in pairs:
            for form in (en + "s", en + "es"):
                if form not in known:
                    known.add(form)
                    out.append((form, tr))
        return sorted(out)

    write_csv(lookups / "creatures.csv", H, [["CREATURE", en, tr] for en, tr in with_plain_plural(creatures)])
    write_csv(lookups / "plants.csv", H, [["PLANT", en, strip_no(tr)] for en, tr in with_plain_plural(plants)])
    # 注意: テーブルが自分自身を {:MATERIAL} で参照すると無限再帰になるので、参照は別テーブルへ
    mat_rows = [["MATERIAL", en, strip_no(tr)] for en, tr in materials]
    mat_rows += [["MATERIAL:SUFFIX", en, tr] for en, tr in sorted(MATERIAL_SUFFIXES.items())]
    mat_rows += [
        ["MATERIAL", "{:CREATURE} {:MATERIAL:SUFFIX}", "{:CREATURE}の{:MATERIAL:SUFFIX}"],
        ["MATERIAL", "{:PLANT} {:MATERIAL:SUFFIX}", "{:PLANT}{:MATERIAL:SUFFIX}"],
        ["MATERIAL", "{:CREATURE} {:MATERIAL:PART} {:MATERIAL:SUFFIX}", "{:CREATURE}の{:MATERIAL:PART}の{:MATERIAL:SUFFIX}"],
        ["MATERIAL", "{:MONSTER} {:MATERIAL:SUFFIX}", "{:MONSTER}の{:MATERIAL:SUFFIX}"],
        # 世界生成で作られる神話の材質（"primeval stardust" / "strange goo"）。
        # 語彙は materials.lua に決まっていて、組み合わせだけが世界ごとに変わる
        ["MATERIAL", "{:MATERIAL:MYTHADJ} {:MATERIAL:MYTHNOUN}", "{:MATERIAL:MYTHADJ}{:MATERIAL:MYTHNOUN}"],
    ]
    mat_rows += [["MATERIAL:PART", en, tr] for en, tr in sorted(read_tsv(TR / "bodyparts.tsv").items()) if tokens_ok(en, tr)]
    # 実行ファイルに直接書かれている材質（raw に無いので raw_terms では拾えない）。
    # 名前に使う物質の表（procgen-names.tsv の mat）を流用し、足りないものを足す
    builtin_mat = dict(pg["mat"])
    builtin_mat.update({
        "blood": "血", "magma": "マグマ", "lava": "溶岩", "sand": "砂", "dust": "塵",
        "slime": "粘液", "pus": "膿", "sweat": "汗", "tears": "涙", "spit": "唾",
        "slush": "シャーベット状の雪", "sleet": "みぞれ", "frost": "霜", "steam": "蒸気",
        # 建造物の材料（"Rock Block Wall" / "Wood Block Floor"）
        "rock block": "石ブロック", "wood block": "木ブロック", "glass block": "ガラスブロック",
        "green glass block": "緑ガラスブロック", "clear glass block": "透明ガラスブロック",
        "crystal glass block": "水晶ガラスブロック",
    })
    mat_rows += [["MATERIAL", en, tr] for en, tr in sorted(builtin_mat.items())]
    mat_rows += [["MATERIAL:MYTHADJ", en, tr] for en, tr in pg["mythadj"]]
    mat_rows += [["MATERIAL:MYTHNOUN", en, tr] for en, tr in pg["mythnoun"]]
    # 神の材質の名前（divine.lua の決まった62種）
    mat_rows += [["MATERIAL", en, tr] for en, tr in pg["divine"]]
    write_csv(lookups / "materials.csv", H, mat_rows)
    item_rows = [["ITEM:NOUN", en, tr] for en, tr in items]
    item_rows += [
        ["ITEM", "{:ITEM:NOUN}", "{:ITEM:NOUN}"],
        ["ITEM", "{:MATERIAL} {:ITEM:NOUN}", "{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "{:CREATURE} {:ITEM:NOUN}", "{:CREATURE}の{:ITEM:NOUN}"],
        # 着る者の体の大きさ（冒険者の装備 "small copper breastplate"、"small donkey leather helm"）
        ["ITEM", "small {:MATERIAL} {:ITEM:NOUN}", "小型の{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "small {:CREATURE} {:MATERIAL:SUFFIX} {:ITEM:NOUN}", "小型の{:CREATURE}の{:MATERIAL:SUFFIX}の{:ITEM:NOUN}"],
        ["ITEM", "large {:MATERIAL} {:ITEM:NOUN}", "大型の{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "large {:CREATURE} {:MATERIAL:SUFFIX} {:ITEM:NOUN}", "大型の{:CREATURE}の{:MATERIAL:SUFFIX}の{:ITEM:NOUN}"],
        ["ITEM", "{:CREATURE} {:MATERIAL:SUFFIX} {:ITEM:NOUN}", "{:CREATURE}の{:MATERIAL:SUFFIX}の{:ITEM:NOUN}"],
        # 調理した内臓（"prepared albatross intestines" → 調理済みのアホウドリの腸）
        ["ITEM", "prepared {:CREATURE} {:MATERIAL:SUFFIX}", "調理済みの{:CREATURE}の{:MATERIAL:SUFFIX}"],
        ["ITEM", "chopped {:CREATURE} {:MATERIAL:SUFFIX}", "刻んだ{:CREATURE}の{:MATERIAL:SUFFIX}"],
        ["ITEM", "minced {:CREATURE} {:MATERIAL:SUFFIX}", "細切れの{:CREATURE}の{:MATERIAL:SUFFIX}"],
        # 腐った遺骸（"{Rotten creepy crawler Remains}"）
        ["ITEM", "rotten {:CREATURE} {:ITEM:NOUN}", "腐った{:CREATURE}の{:ITEM:NOUN}"],
        # 罠の部品（"large, serrated bronze disc" / "menacing copper spike"）
        ["ITEM", "large, serrated {:MATERIAL} {:ITEM:NOUN}", "大型の鋸状の{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "serrated {:MATERIAL} {:ITEM:NOUN}", "鋸状の{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "menacing {:MATERIAL} {:ITEM:NOUN}", "威嚇する{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "spiked {:MATERIAL} {:ITEM:NOUN}", "棘付きの{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "giant {:MATERIAL} {:ITEM:NOUN}", "巨大な{:MATERIAL}の{:ITEM:NOUN}"],
        ["ITEM", "enormous {:MATERIAL} {:ITEM:NOUN}", "巨大な{:MATERIAL}の{:ITEM:NOUN}"],
    ]
    write_csv(lookups / "items.csv", H, item_rows)
    # 容れ物（"rock nuts Bag (sheep wool)" のような「中身 容れ物（材質）」の真ん中を受ける）。
    # 外側の「（材質）」は engine の translate_parenthesized が外して、ここに「中身 容れ物」だけが来る。
    # ITEM の表から {:ITEM} を参照すると自分自身を指して止まらなくなるので、別の表にしてある
    container_rows = [["CONTAINER:NOUN", en, tr] for en, tr in sorted(CONTAINER_NOUNS.items())]
    container_rows += [["CONTAINER:FOR", en, tr] for en, tr in sorted(CONTAINER_FOR.items())]
    container_rows += [
        ["CONTAINER", "{:ITEM} {:CONTAINER:NOUN}", "{:ITEM}の{:CONTAINER:NOUN}"],
        ["CONTAINER", "{:MATERIAL} {:CONTAINER:NOUN}", "{:MATERIAL}の{:CONTAINER:NOUN}"],
        ["CONTAINER", "{:MATERIAL:SUFFIX} {:CONTAINER:NOUN}", "{:MATERIAL:SUFFIX}の{:CONTAINER:NOUN}"],
        ["CONTAINER", "{:PLANT} {:CONTAINER:NOUN}", "{:PLANT}の{:CONTAINER:NOUN}"],
        ["CONTAINER", "{:CREATURE} {:CONTAINER:NOUN}", "{:CREATURE}の{:CONTAINER:NOUN}"],
        ["CONTAINER", "{:CONTAINER:FOR} {:CONTAINER:NOUN}", "{:CONTAINER:FOR}の{:CONTAINER:NOUN}"],
    ]
    write_csv(lookups / "containers.csv", H, container_rows)

    # 宝石の研磨の形（"cushion cut kunzite" → クッションカットのクンツァイト）
    shapes = sorted((en, tr) for en, tr in raw_ja.items() if "shape" in kinds(en))
    gem_rows = [["GEM:CUT", en, tr] for en, tr in shapes]
    gem_rows += [["GEM:NAME", en, tr] for en, tr in sorted(read_tsv(TR / "gems.tsv").items()) if tokens_ok(en, tr)]
    gem_rows += [
        ["GEM", "{:GEM:CUT} {:MATERIAL}", "{:GEM:CUT}の{:MATERIAL}"],
        ["GEM", "large {:GEM:CUT} {:MATERIAL}", "大きな{:GEM:CUT}の{:MATERIAL}"],
        ["GEM", "{:GEM:CUT} {:GEM:NAME}", "{:GEM:CUT}の{:GEM:NAME}"],
        ["GEM", "large {:GEM:CUT} {:GEM:NAME}", "大きな{:GEM:CUT}の{:GEM:NAME}"],
    ]
    write_csv(lookups / "gems.csv", H, gem_rows)

    # 地形の名前（"Red Sand Wall" → 赤砂の壁、"Dense hair grass" → 密生したヘアグラス）
    terrain_rows = [["TERRAIN:SUFFIX", en, tr] for en, tr in sorted(TERRAIN_SUFFIXES.items())]
    terrain_rows += [
        ["TERRAIN", "{:MATERIAL} {:TERRAIN:SUFFIX}", "{:MATERIAL}の{:TERRAIN:SUFFIX}"],
        ["TERRAIN", "{:PLANT} {:TERRAIN:SUFFIX}", "{:PLANT}{:TERRAIN:SUFFIX}"],
    ]
    # タイルの名前に付く形容詞（"Rough Microcline Wall" / "Snow-covered Ice" / "Dense hair grass"）。
    # テーブルは自分を参照できないので、形容詞ごとに組み合わせの行を作る
    for adj, adj_ja in TERRAIN_ADJS.items():
        terrain_rows += [
            ["TERRAIN", f"{adj} {{:MATERIAL}} {{:TERRAIN:SUFFIX}}", f"{adj_ja}{{:MATERIAL}}の{{:TERRAIN:SUFFIX}}"],
            ["TERRAIN", f"{adj} {{:PLANT}} {{:TERRAIN:SUFFIX}}", f"{adj_ja}{{:PLANT}}{{:TERRAIN:SUFFIX}}"],
            ["TERRAIN", f"{adj} {{:TERRAIN:SUFFIX}}", f"{adj_ja}{{:TERRAIN:SUFFIX}}"],
            ["TERRAIN", f"{adj} {{:MATERIAL}}", f"{adj_ja}{{:MATERIAL}}"],
            ["TERRAIN", f"{adj} {{:PLANT}}", f"{adj_ja}{{:PLANT}}"],
        ]
    # 形容詞が2つ重なる形（"Snow-covered Dense fescue grass"）。
    # 後ろに来るのは草木の茂り具合を表す語だけなので、その組み合わせだけ作る
    for adj, adj_ja in TERRAIN_ADJS.items():
        for adj2, adj2_ja in TERRAIN_ADJS.items():
            if adj2 not in ("dense", "sparse", "dead", "dry", "frozen", "waterlogged") or adj == adj2:
                continue
            terrain_rows += [
                ["TERRAIN", f"{adj} {adj2} {{:PLANT}}", f"{adj_ja}{adj2_ja}{{:PLANT}}"],
                ["TERRAIN", f"{adj} {adj2} {{:MATERIAL}} {{:TERRAIN:SUFFIX}}", f"{adj_ja}{adj2_ja}{{:MATERIAL}}の{{:TERRAIN:SUFFIX}}"],
                ["TERRAIN", f"{adj} {adj2} {{:TERRAIN:SUFFIX}}", f"{adj_ja}{adj2_ja}{{:TERRAIN:SUFFIX}}"],
            ]
    # 地面にうっすら積もったもの（"A dusting of snow" / "A spattering of dwarf blood"）
    for coat, coat_ja in TERRAIN_COATS.items():
        terrain_rows += [
            ["TERRAIN", f"{coat} {{:MATERIAL}}", f"{coat_ja}{{:MATERIAL}}"],
            ["TERRAIN", f"{coat} {{:PLANT}}", f"{coat_ja}{{:PLANT}}"],
        ]
    write_csv(lookups / "terrain.csv", H, terrain_rows)

    # 邪神の信徒の呼び名（"dwarf cultist of change" → ドワーフの変化の信者）。
    # ゲームは「称号12種」と「飾る語168種」を組み合わせて作る（mythical.lua の mythical_names / mythical_adjectives）。
    # 種族が頭に付くので、組み立て型のテーブルで「{種族} {称号}」を受ける
    MYTHICAL_TITLES = [
        ("servant", "下僕"), ("follower", "信奉者"), ("cultist", "信者"), ("worshipper", "崇拝者"),
        ("adept", "熟達者"), ("priest", "司祭"), ("cleric", "聖職者"), ("shaman", "呪術師"),
        ("lord", "君主"), ("master", "主"), ("ancient", "古き者"), ("elder", "長老"),
    ]
    person_rows = []
    adj_path = TR / "mythical-adj.tsv"
    if adj_path.exists():
        for line in adj_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            cols = line.split("	")
            if len(cols) != 3:
                continue
            adj, pos, adj_ja = cols[0].strip(), cols[1].strip(), cols[2].strip()
            for name, name_ja in MYTHICAL_TITLES:
                for one, many in ((name, name + "s"),):
                    # 複数形は称号のほうに付く（"cultists of change" / "gale cultists"）
                    forms = [f"{one} {adj}", f"{many} {adj}"] if pos == "after" else [f"{adj} {one}", f"{adj} {many}"]
                    for form in forms:
                        person_rows.append(["PERSON:TITLE", form, f"{adj_ja}の{name_ja}"])
    if person_rows:
        person_rows.append(["PERSON", "{:CREATURE} {:PERSON:TITLE}", "{:CREATURE}の{:PERSON:TITLE}"])
        write_csv(lookups / "persons.csv", H, person_rows)
        print(f"信徒の呼び名: {len(person_rows) - 1} 件")

    # 世界生成で組み立てられる怪物の名前（夜のトロル・悪魔・天使）。
    # ゲームは data/vanilla/vanilla_procedural/scripts/generators/creatures.lua で
    # 「形容詞 + 種類」「種類 + of + 物質」「連れ合いの呼び名」を組み合わせて作る。
    # 語彙は決まっているが組み合わせは世界ごとに変わるので、組み立て型のテーブルで受ける
    if pg["kind"]:
        colors = sorted((en, tr) for en, tr in raw_ja.items() if "color" in kinds(en))
        monster_rows = [["MONSTER:KIND", en, tr] for en, tr in pg["kind"]]
        monster_rows += [["MONSTER:SPOUSE", en, tr] for en, tr in pg["spouse"]]
        monster_rows += [["MONSTER:END", en, tr] for en, tr in pg["end"]]
        # 頭に付く形容詞。色は体の色から採られるので、色の名前も「〜の」の形で入れる
        monster_rows += [["MONSTER:ADJ", en, tr] for en, tr in pg["adj"] + pg["sadj"]]
        monster_rows += [["MONSTER:ADJ", en, tr + "の"] for en, tr in colors]
        # 名前に使われる名詞（物質と神の領域）。"banshee of steam" / "deformity Messenger"
        monster_rows += [["MONSTER:OF", en, tr] for en, tr in pg["mat"] + pg["snoun"]]
        # 怪物の姿のもとになる生き物（creatures/rcp.lua の name_string）。
        # 生き物の表に無い語（tortoise, pterosaur …）もここに入れる
        monster_rows += [["MONSTER:RCP", en, tr] for en, tr in pg["rcp"]]
        monster_rows += [
            ["MONSTER", "{:MONSTER:RCP} {:MONSTER:KIND}", "{:MONSTER:RCP}の{:MONSTER:KIND}"],
            ["MONSTER", "{:MONSTER:RCP} {:MONSTER:KIND} {:MONSTER:SPOUSE}", "{:MONSTER:RCP}の{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
            ["MONSTER", "{:MONSTER:SPOUSE} of the {:MONSTER:RCP} {:MONSTER:KIND}", "{:MONSTER:RCP}の{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
            ["MONSTER", "{:MONSTER:KIND}", "{:MONSTER:KIND}"],
            ["MONSTER", "{:MONSTER:ADJ} {:MONSTER:KIND}", "{:MONSTER:ADJ}{:MONSTER:KIND}"],
            ["MONSTER", "{:CREATURE} {:MONSTER:KIND}", "{:CREATURE}の{:MONSTER:KIND}"],
            ["MONSTER", "{:MONSTER:OF} {:MONSTER:KIND}", "{:MONSTER:OF}の{:MONSTER:KIND}"],
            ["MONSTER", "{:MONSTER:KIND} {:MONSTER:END}", "{:MONSTER:END}{:MONSTER:KIND}"],
            ["MONSTER", "{:MONSTER:KIND} of {:MONSTER:OF}", "{:MONSTER:OF}の{:MONSTER:KIND}"],
            # 連れ合い（"bleak monster bride" / "groom of the wicked troll" / "troll mates of twilight"）
            ["MONSTER", "{:MONSTER:ADJ} {:MONSTER:KIND} {:MONSTER:SPOUSE}", "{:MONSTER:ADJ}{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
            ["MONSTER", "{:CREATURE} {:MONSTER:KIND} {:MONSTER:SPOUSE}", "{:CREATURE}の{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
            ["MONSTER", "{:MONSTER:KIND} {:MONSTER:SPOUSE} {:MONSTER:END}", "{:MONSTER:END}{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
            ["MONSTER", "{:MONSTER:SPOUSE} of the {:MONSTER:ADJ} {:MONSTER:KIND}", "{:MONSTER:ADJ}{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
            ["MONSTER", "{:MONSTER:SPOUSE} of the {:CREATURE} {:MONSTER:KIND}", "{:CREATURE}の{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
            ["MONSTER", "{:MONSTER:SPOUSE} of the {:MONSTER:OF} {:MONSTER:KIND}", "{:MONSTER:OF}の{:MONSTER:KIND}の{:MONSTER:SPOUSE}"],
        ]
        write_csv(lookups / "monsters.csv", H, monster_rows)
        print(f"組み立て型の怪物の名前: {len(monster_rows)} 件")

    # スキルの熟練度 + 呼び名
    skill_rows = [["SKILL:LEVEL", en, tr] for en, tr in SKILL_LEVELS.items()]
    missing_skill = []
    for en, tr in SKILL_NAMES.items():
        tr = tr or ja.get(en) or ja.get(en.lower())
        if tr:
            skill_rows.append(["SKILL:NAME", en, tr])
        else:
            missing_skill.append(en)
    skill_rows.append(["SKILL", "{:SKILL:LEVEL} {:SKILL:NAME}", "{:SKILL:NAME}（{:SKILL:LEVEL}）"])
    write_csv(lookups / "skills.csv", H, skill_rows)
    if missing_skill:
        print("訳の無いスキル名:", ", ".join(missing_skill))

    # 3) 文章（単語ごとに折り返して描くテキスト）の訳
    para_rows = []
    para_path = TR / "paragraphs.tsv"
    if para_path.exists():
        for line in para_path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("	")
            if len(parts) >= 2 and parts[0] and parts[1]:
                if not tokens_ok(parts[0], parts[1]):
                    rejected.append(("paragraphs.tsv", parts[0], parts[1]))
                    continue
                para_rows.append([parts[0], parts[1]])
    write_csv(DATA / "paragraph-dictionary.csv", ["text", "translation"], para_rows)
    print(f"文章の訳: {len(para_rows)} 件")

    # 4) 文テンプレート（実行ファイルの文の部品）。sentences-fix.tsv の手直しが優先
    sent = {}
    for name in ("sentences.tsv", "sentences-fix.tsv", "combat.tsv", "thoughts.tsv", "quotes.tsv", "beast-desc.tsv"):
        p = TR / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            # 自動で作ったグループのうち質の悪いものは使わない。戦闘の文（e6cc0）は combat.tsv、価値観の句（e3c780）は values.tsv の辞書で置き換える
            if len(parts) >= 4 and parts[0].split(".")[0] not in ("e6cc0", "e3c780"):
                sent[(parts[0], parts[1], parts[2])] = parts[3]
    # 欲求タブの、神の名前が入る文（"She is not distracted after being unable to pray to Bestra."）
    nd = {"state": {}}
    for line in (TR / "needs.tsv").read_text(encoding="utf-8").splitlines():
        p = line.split("	")
        if len(p) == 3 and p[0] == "state":
            nd["state"][p[1]] = p[2]
    for subj, sj in [("He", "彼"), ("She", "彼女"), ("It", "それ"), ("They", "彼ら"), ("You", "あなた")]:
        be = "are" if subj in ("They", "You") else "is"
        for st, stj in nd["state"].items():
            sent[("manual", "core", f"{subj} {be} {st} after being unable to pray to {{1}}.")] = f"{sj}は{{1}}に祈れず、{stj}。"
            sent[("manual", "core", f"{subj} {be} {st} after communing with {{1}}.")] = f"{sj}は{{1}}と交感できて、{stj}。"
    # 性格の説明（e3eb80）は「句 + 葛藤の節（。ただ、…）」の順につなぐので、後ろの句の位置 {REST} を文末に移す
    for key, ja in list(sent.items()):
        if key[0].split(".")[0] == "e3eb80" and key[1] == "core" and "{REST}" in ja:
            sent[key] = ja.replace("{REST}", "") + "{REST}"
    # 段落の区切り [B] [P] [R] をまたぐ本体は、区切りで英語と訳の両方を分けて、1文ずつの本体も作る。
    # エンジンは区切りで文を分けてから照合するため、またいだままでは当たらない
    brk = re.compile(r"\[(?:B|P|R)\]")
    sent_en = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\[])")
    sent_ja = re.compile(r"(?<=[。！？])")

    def glue(pieces):
        """差し込みや空白だけの断片（文末の "{1}"）は前の文にくっつける"""
        out = []
        for x in pieces:
            if out and re.fullmatch(r"\s*(\{\d+\}\s*)*", x):
                out[-1] += x
            elif x.strip():
                out.append(x)
        return out
    split_rows = {}
    for (g, k, e), j in sent.items():
        if k != "core" or not (brk.search(e) or sent_en.search(e)):
            continue
        en_parts, ja_parts = brk.split(e), brk.split(j.replace("{REST}", ""))
        if len(en_parts) != len(ja_parts):
            continue
        # さらに文の境目でも分ける（英語の文末の数と日本語の「。」の数が合うときだけ）
        en2, ja2 = [], []
        for en_p, ja_p in zip(en_parts, ja_parts):
            es = glue(sent_en.split(en_p.strip()))
            js = glue(sent_ja.split(ja_p.strip()))
            if len(es) > 1 and len(es) == len(js):
                en2 += es
                ja2 += js
            else:
                en2.append(en_p)
                ja2.append(ja_p)
        en_parts, ja_parts = en2, ja2
        for en_p, ja_p in zip(en_parts, ja_parts):
            en_p, ja_p = en_p.strip(), ja_p.strip()
            if not en_p or not ja_p or not re.search(r"[A-Za-z]{3}", en_p):
                continue
            if sorted(re.findall(r"\{\d+\}", en_p)) != sorted(re.findall(r"\{\d+\}", ja_p)):
                continue
            # 句点の無い訳の終わりに「。」を足す（英語が . で終わるとき）
            if en_p.endswith(".") and not ja_p.endswith(("。", "！", "？")):
                ja_p += "。"
            split_rows.setdefault((g, "core", en_p), ja_p)
    # 文末の記号の後ろに差し込みだけが続く本体（"…or the indicated buttons.{3}"）は、その差し込みを外した形も作る。
    # エンジンは文を文末で区切ってから照合するので、後ろの差し込みには何も入らず当たらない
    for (g, k, e), j in list(sent.items()):
        if k != "core":
            continue
        m = re.search(r"[.!?](\{\d+\})+$", e)
        if not m:
            continue
        tail = re.findall(r"\{\d+\}", m.group(0))
        e2 = e[: m.start() + 1]
        j2 = j.replace("{REST}", "")
        for t in tail:
            j2 = j2.replace(t, "")
        if re.search(r"\{\d+\}", e2) and sorted(re.findall(r"\{\d+\}", e2)) == sorted(re.findall(r"\{\d+\}", j2)):
            split_rows.setdefault((g, "core", e2), j2.strip())
    for key, ja_p in split_rows.items():
        sent.setdefault(key, ja_p)
    print(f"区切りで分けた文テンプレート: {len(split_rows)} 件")
    write_csv(DATA / "sentence-templates.csv", ["group", "kind", "text", "translation"],
              [[g, k, e, j] for (g, k, e), j in sent.items()])
    print(f"文テンプレート: {len(sent)} 件")

    # 差し込みの無い完全な文のテンプレート（"Perhaps some of your friends here can remind you.{1}{2}" の末尾の差し込みは外す）は、
    # 完全一致辞書にも入れる。末尾に差し込みが続くテンプレートは、エンジンが照合に使わないため
    added = 0
    for (g, k, e), j in sent.items():
        if k not in ("core", "suffix"):
            continue
        e2 = re.sub(r"(\{\d+\})+$", "", e).strip()
        j2 = re.sub(r"(\{\d+\})+$", "", j.replace("{REST}", "")).strip()
        if "{" in e2 or "{" in j2 or not e2 or not j2 or not e2[0].isupper() or not e2.endswith((".", "!", "?")):
            continue
        for form in {e2, re.sub(r"(?<=[.!?:]) {2,}", " ", e2)}:
            if form.lower() not in simple:
                simple[form.lower()] = (form, j2)
                added += 1
    write_csv(DATA / "simple-dictionary.csv", ["text", "translation"], sorted(simple.values(), key=lambda r: r[0].lower()))
    print(f"文テンプレートから完全一致辞書に足した文: {added} 件")

    print(f"完全一致辞書: {len(simple)} 件 / 生物 {len(creatures)} / 素材 {len(materials)} / アイテム {len(items)}")
    if rejected:
        rej = ROOT / "work" / "rejected.tsv"
        rej.write_text("".join(f"{s}\t{e}\t{t}\n" for s, e, t in rejected), encoding="utf-8")
        print(f"トークン不一致で除外: {len(rejected)} 件 → {rej}")


if __name__ == "__main__":
    main()
