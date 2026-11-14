"""怪物の見た目の説明文（忘れられし獣・巨人・悪魔・夜の生き物・獣人・実験体・天使）の訳を作る。

ゲームは世界生成のときに Lua（`data/vanilla/vanilla_procedural/scripts/generators/creatures/shared_info.lua`
の `build_description`）で、部品をつなげて説明文を作り、生き物のカーストの説明としてセーブに埋め込む。
例:

    An enormous serpent composed of sandy loam.  It has wings and it undulates rhythmically.
    Its eyes glow red.  Its black scales are small and overlapping.  Beware its deadly spittle!

文の形は次の5つ。組み合わせは数十万通りになるので、丸ごと辞書に入れるのは無理。
**語の少ない所は全組み合わせを辞書に、多い所は文テンプレートの差し込みに**分ける。

    ① A{大きさ} {形容}{体の名前}{ 姿}{ with句}{ composed of 素材}.
    ② It has {特徴} and {様子}.        （特徴が無ければ「{様子}.」だけ）
    ③ Its eyes glow {色}.              （目が1つなら "Its eye glows {色}."）
    ④ Its {色} {毛/羽/鱗/皮膚/外骨格} {質感}.
    ⑤ Beware its {攻撃}!               （種類ごとの締めの一文のこともある）

部品の英語は `tools/beast_desc_extract.py` が Lua と raw から取り出して `work/beast_parts.tsv` に書く。
訳は `translations/beast-parts.tsv`（手で訳した分）と、既にある訳（translations/*.tsv と
`data/simple-dictionary.csv`）から引く。

使い方（**先に build.py を1度流して `data/simple-dictionary.csv` を作っておくこと**）:

    python -I -X utf8 tools/build.py
    python -I -X utf8 tools/beast_desc_templates.py
    python -I -X utf8 tools/build.py

出力:
    translations/beast-terms.tsv  完全一致で引く分（英語<TAB>日本語）
    translations/beast-desc.tsv   文テンプレート（group<TAB>kind<TAB>英語<TAB>日本語）
"""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTS = ROOT / "work" / "beast_parts.tsv"
OUT_TERMS = ROOT / "translations" / "beast-terms.tsv"
OUT_DESC = ROOT / "translations" / "beast-desc.tsv"

# 体の表面と、その訳（④の文）
SURFACES = [
    ("hair is", "毛"),
    ("feathers are", "羽"),
    ("scales are", "鱗"),
    ("skin is", "肌"),
    ("exoskeleton is", "外骨格"),
]


def load_terms():
    """英語 → 日本語。translations/*.tsv と、build.py が作った完全一致辞書から集める"""
    terms = {}
    skip = {"sentences.tsv", "sentences-fix.tsv", "combat.tsv", "thoughts.tsv", "prefs.tsv",
            "quotes.tsv", "term-rules.tsv", "monster-names.tsv", "beast-desc.tsv", "beast-terms.tsv"}
    for path in sorted((ROOT / "translations").glob("*.tsv")):
        if path.name in skip:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) == 2 and cols[0].strip() and cols[1].strip() not in ("", "-"):
                terms.setdefault(cols[0].lower(), cols[1].strip())
                terms.setdefault(cols[0].strip().lower(), cols[1].strip())
    built = ROOT / "data" / "simple-dictionary.csv"
    if built.exists():
        with built.open(encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) == 2:
                    terms.setdefault(row[0].strip().lower(), row[1].strip())
    return terms


def load_parts():
    """分類 → 英語の一覧（出た順、重複を除く）"""
    parts = {}
    for line in PARTS.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        kind, en = cols[0], cols[1]
        bucket = parts.setdefault(kind, [])
        if en not in bucket:
            bucket.append(en)
    return parts


def main():
    terms = load_terms()
    parts = load_parts()
    missing = []

    def ja(en):
        """部品の訳。無ければ記録して None"""
        found = terms.get(en.lower()) or terms.get(en.strip().lower())
        if not found:
            missing.append(en)
        return found

    def pairs(kind):
        """訳のある部品だけ (英語, 日本語) で返す"""
        return [(en, ja(en)) for en in parts.get(kind, []) if ja(en)]

    sizes = pairs("size")
    adjs = pairs("adj")
    bodies = pairs("body")
    forms = pairs("form")
    withs = pairs("with")
    materials = pairs("material")
    features = pairs("feature")
    manners = pairs("manner")
    colors = pairs("color")
    textures = pairs("texture")
    bewares = pairs("beware")
    closings = pairs("closing")

    terms_out = []  # (英語, 日本語)
    desc_out = []   # (英語, 日本語) 文テンプレート

    def add_term(en, jp):
        terms_out.append((en, jp))

    def add_tmpl(en, jp):
        desc_out.append((en, jp))

    # --- ① 体の名前（形容が付く形も） ---
    # 「形容 + 体の名前」は差し込み {1} に入るので、全組み合わせを辞書に入れる
    for ben, bja in bodies:
        add_term(ben, bja)
        for aen, aja in adjs:
            add_term(f"{aen} {ben}", f"{aja}{bja}")

    # --- ① 文そのもの ---
    # 大きさ・姿・with句・素材のあるなしで組み合わせる。差し込みは「形容+体の名前」と素材
    size_opts = [("", "")] + [(sen, sja) for sen, sja in sizes]
    form_opts = [("", "")] + [(f" {fen}", fja) for fen, fja in forms]
    with_opts = [("", "")] + [(f" {wen}", wja) for wen, wja in withs]
    for sen, sja in size_opts:
        for fen, fja in form_opts:
            for wen, wja in with_opts:
                head = f"A{sen} {{1}}{fen}{wen}"
                tail_ja = f"{wja}{fja}{sja}{{1}}"
                # 素材つき。"composed of" という固有の言い回しがあるので、文を取り違える心配は小さい
                add_tmpl(f"{head} composed of {{2}}.", f"{{2}}でできた{tail_ja}。")
                # 素材なし。大きさも姿も無い "A {1}." はふつうの文まで飲み込むので作らない
                if sen or fen or wen:
                    add_tmpl(f"{head}.", f"{tail_ja}。")
    # 大きさも姿も無い形は、文そのものを辞書に入れる
    for ben, bja in bodies:
        add_term(f"A {ben}.", f"{bja}。")
        for aen, aja in adjs:
            add_term(f"A {aen} {ben}.", f"{aja}{bja}。")

    # --- ② 特徴と様子 ---
    # 角・尾は「数 + 形 + 名詞」で組み立てられる
    for kind, count_kind, shape_kind, noun_kind in (
        ("horn", "horn_count", "horn_shape", "horn_noun"),
        ("tail", "tail_count", "tail_shape", "tail_noun"),
    ):
        for cen, cja in pairs(count_kind):
            for sen2, sja2 in pairs(shape_kind):
                for nen, nja in pairs(noun_kind):
                    # ゲームは "It has two long, curving horns" のように組む（空白はそのまま）
                    features.append((f"{cen.strip()} {sen2.strip()} {nen}", f"{cja}{sja2}{nja}"))
    for fen, fja in features:
        bare = fen
        for art in ("a ", "an ", "the "):
            if bare.lower().startswith(art):
                bare = bare[len(art):]
                break
        add_term(f"It has {fen}.", f"{fja}がある。")
        add_tmpl(f"It has {fen} and {{1}}.", f"{fja}があり、{{1}}。")
        add_term(fen, fja)
        if bare != fen:
            add_term(bare, fja)
    # 特徴が無いときは、様子だけが1文になる（先頭が大文字）
    for men, mja in manners:
        sentence = men[0].upper() + men[1:] if men else men
        add_term(f"{sentence}.", f"{mja}。")
        add_term(men, mja)

    # --- ③ 目の色 ---
    for cen, cja in colors:
        add_term(f"Its eyes glow {cen}.", f"その目は{cja}に光っている。")
        add_term(f"Its eye glows {cen}.", f"その目は{cja}に光っている。")

    # --- ④ 体表の色と質感 ---
    for sen3, sja3 in SURFACES:
        add_tmpl(f"Its {{1}} {sen3} {{2}}.", f"その{sja3}は{{1}}色で、{{2}}。")
    # 差し込みに入る質感
    for ten, tja in textures:
        add_term(ten, tja)
    # 鱗だけは「形 + and + 並び」の2つの一覧から組み立てる（shared_info.lua の SCALES）。
    # small / large は「大きさ」の語と英語がぶつかるので、訳はここに直接書く
    scale_shapes = {"small": "小さく", "large": "大きく", "round": "丸く", "blocky": "角張っており",
                    "jagged": "ぎざぎざしており", "oval-shaped": "楕円形で"}
    scale_spreads = {"overlapping": "重なり合っている", "set far apart": "間隔を空けて並んでいる",
                     "close-set": "密に並んでいる"}
    for sh, sh_ja in scale_shapes.items():
        for sp, sp_ja in scale_spreads.items():
            add_term(f"{sh} and {sp}", f"{sh_ja}{sp_ja}")

    # --- ⑤ 締めの一文 ---
    add_tmpl("Beware its {1}!", "{1}に気をつけろ！")
    for ben2, bja2 in bewares:
        add_term(ben2, bja2)
        add_term(f"Beware its {ben2}!", f"{bja2}に気をつけろ！")
    for cen2, cja2 in closings:
        add_term(cen2, cja2)

    # --- 実験体（夜の生き物）の締めの文 ---
    # creatures.lua が断片をつなげて作る。日本語とは語順が違うので、組み合わせごとにテンプレートにする。
    # 先頭が "This night creature was first created " で固定なので、ほかの文に当たる心配はない
    powers = [
        (" through the fiend's terrifying power", "魔王の恐ろしい力によって"),
        (" through the fiend's twisted power", "魔王の歪んだ力によって"),
        (" through the fiend's chaotic power", "魔王の混沌の力によって"),
        (" after horrible experiments", "恐ろしい実験の末に"),
        (" after horrible experiments gone wrong", "恐ろしい実験が失敗した末に"),
    ]
    for acc_en, acc_ja in (("", ""), ("accidentally ", "偶然に")):
        for has_site in (False, True):
            for power_en, power_ja in powers:
                for target_en in ("", " unleashed upon ", " on "):
                    for has_place in (False, True):
                        n = 0
                        def slot():
                            nonlocal n
                            n += 1
                            return f"{{{n}}}"
                        maker = slot()
                        site = slot() if has_site else None
                        en = f"This night creature was first created {acc_en}by the {maker}"
                        if site:
                            en += f" of {site}"
                        en += power_en
                        target = None
                        if target_en:
                            target = slot()
                            en += target_en + target
                        place = slot() if has_place else None
                        if place:
                            en += f" in {place}"
                        year = slot()
                        en += f" in the year {year}."
                        ja = f"この夜の生き物は、{year}年"
                        if place:
                            ja += f"、{place}にて"
                        ja += "、"
                        if site:
                            ja += f"{site}の"
                        ja += f"{maker}が"
                        if target:
                            ja += f"{target}に対し、"
                        ja += power_ja + acc_ja + "作り出した。"
                        add_tmpl(en, ja)
    # 対象として入る決まり文句
    add_term("multitudes", "多くの者")
    add_term("an unknown creature", "名も知れぬ生き物")

    # --- 書き出し（同じ英語は先に作ったほうを残す） ---
    seen = set()
    rows = []
    for en, jp in terms_out:
        key = en.lower()
        if key in seen or not jp:
            continue
        seen.add(key)
        rows.append(f"{en}\t{jp}")
    OUT_TERMS.write_text(
        "# 怪物の見た目の説明文の部品と、組み立てた文（tools/beast_desc_templates.py が作る。直すときはスクリプトか beast-parts.tsv を直す）\n"
        + "\n".join(rows) + "\n", encoding="utf-8")

    seen = set()
    rows = []
    for en, jp in desc_out:
        if en in seen:
            continue
        seen.add(en)
        rows.append(f"manual\tcore\t{en}\t{jp}")
    OUT_DESC.write_text(
        "# 怪物の見た目の説明文の文テンプレート（tools/beast_desc_templates.py が作る）\n"
        + "\n".join(rows) + "\n", encoding="utf-8")

    uniq_missing = sorted(set(missing))
    print(f"{OUT_TERMS.name}: {len(seen) and len(OUT_TERMS.read_text(encoding='utf-8').splitlines()) - 1} 件")
    print(f"{OUT_DESC.name}: {len(rows)} 件")
    if uniq_missing:
        print(f"訳の無い部品 {len(uniq_missing)} 件: {uniq_missing[:20]}")


if __name__ == "__main__":
    main()
