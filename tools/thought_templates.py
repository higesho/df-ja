"""思考タブの感情の文（"He was angry after getting into an argument."）のテンプレートを作る。

ゲームは「主語 + is/was/felt/feels/is in/was in + 感情 + きっかけ」で1文を組み立てる。
感情の語は実行ファイルの一覧（約130語）、きっかけの句は文テンプレートの group e44340 が訳す。
"{1} was {2} {3}." のように差し込みを並べるとふつうの文まで飲み込むので、感情の語ごとにテンプレートを作る。

使い方: python -I -X utf8 tools/thought_templates.py
出力: translations/thoughts.tsv（build.py が文のファイルとして読む）
"""
import glob
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "translations" / "thoughts.tsv"

# 実行ファイルの感情の語（"dwelling upon " の前後に並んでいる）
EMOTIONS = """grim satisfaction|horrified|shocked|alarmed|suspicious|fondness|grumpy|grouchy|satisfied|annoyed|
affection|adoration|admiration|accepting|vengeful|love|blissful|joy|sad|gaiety|excited|triumph|bitter|awe|aversion|
astonished|aroused|apathetic|anxious|anguish|angry|amused|ambivalent|amazed|alienated|agony|aggravated|agitated|eager|
distressed|displeasure|dismayed|dislike|disillusioned|disgusted|disappointed|despair|delighted|dejected|content|
contemptuous|confused|caring|bored|gratitude|glum|gloomy|gleeful|frustrated|frightened|free|ferocity|afraid|
exhilarated|exasperated|enjoyment|empty|empathy|embarrassed|elated|lustful|lonely|loathing|jubilant|jovial|jolly|
isolated|irritated|interested|insulted|humiliated|hopeless|hope|hateful|happy|guilty|regretful|relieved|rejected|
enraptured|proud|pleasure|passionate|patient|panicked|outraged|optimistic|nostalgic|nervous|mortified|miserable|
wonder|unhappy|uneasy|thrilled|terrified|tenderness|sympathy|ashamed|shaken|servile|self-pity|indignant|restless|
resentful|repentant|remorseful|euphoric|pessimistic|enthusiastic|doubt|expectant|defeated|existential crisis|
zealous|wrathful|worried""".replace("\n", "").split("|")

# 主語（英語、日本語、be 動詞の現在形・過去形）
SUBJECTS = [
    ("He", "彼", "is", "was"),
    ("She", "彼女", "is", "was"),
    ("It", "それ", "is", "was"),
    ("They", "彼ら", "are", "were"),
    ("You", "あなた", "are", "were"),
]


def load_terms():
    terms = {}
    for path in sorted((ROOT / "translations").glob("*.tsv")):
        if path.name in ("thoughts.tsv", "sentences.tsv", "sentences-fix.tsv", "combat.tsv", "prefs.tsv"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) == 2 and parts[0].strip() and parts[1].strip() not in ("", "-"):
                terms.setdefault(parts[0].strip().lower(), parts[1].strip())
    return terms


def main():
    terms = load_terms()
    rows = []
    missing = []
    for emotion in EMOTIONS:
        ja = terms.get(emotion.lower())
        if not ja:
            missing.append(emotion)
            continue
        for subj, sja, pres, past in SUBJECTS:
            # きっかけの句（{1}）は "after …" / "dwelling upon …" など。e44340 の文テンプレートが訳す
            rows += [
                (f"{subj} {past} {emotion} {{1}}.", f"{sja}は{{1}}、{ja}を感じていた。"),
                (f"{subj} {pres} {emotion} {{1}}.", f"{sja}は{{1}}、{ja}を感じている。"),
                (f"{subj} {past} in {emotion} {{1}}.", f"{sja}は{{1}}、{ja}を感じていた。"),
                (f"{subj} {pres} in {emotion} {{1}}.", f"{sja}は{{1}}、{ja}を感じている。"),
                (f"{subj} felt {emotion} {{1}}.", f"{sja}は{{1}}、{ja}を感じた。"),
                (f"{subj} feels {emotion} {{1}}.", f"{sja}は{{1}}、{ja}を感じている。"),
                (f"{subj} {past} {emotion}.", f"{sja}は{ja}を感じていた。"),
                (f"{subj} {pres} {emotion}.", f"{sja}は{ja}を感じている。"),
                (f"{subj} felt {emotion}.", f"{sja}は{ja}を感じた。"),
                (f"{subj} feels {emotion}.", f"{sja}は{ja}を感じている。"),
            ]
    # 思い出にひたる形（きっかけの句として使われる）
    rows += [
        ("dwelling upon {1}", "{1}、そのことを思い返し"),
        ("remembering {1}", "{1}、そのことを思い出し"),
        ("reliving {1}", "{1}、そのことを何度も思い返し"),
    ]
    out = ["# 思考タブの感情の文（tools/thought_templates.py が作る。直すときはスクリプトを直す）"]
    seen = set()
    for en, ja in rows:
        if en in seen:
            continue
        seen.add(en)
        out.append(f"manual\tcore\t{en}\t{ja}")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(out) - 1} 件" + (f"（訳のない感情語 {len(missing)}: {missing}）" if missing else ""))


if __name__ == "__main__":
    main()
