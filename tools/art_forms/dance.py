"""踊りの形式の説明文（実行ファイルの 4f47b0）のテンプレートと語句を作る。"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])
FIX = ROOT / "translations" / "sentences-fix.tsv"
TERMS = ROOT / "translations" / "art-forms.tsv"
MARK = "# === 芸術の形式（踊り）==="
TMARK = "# --- 踊りの形式の語句 ---"

sent, terms = [], []
s = lambda en, ja: sent.append((en, ja))
t = lambda en, ja: terms.append((en, ja))

# ---------------- 語句 ----------------
for en, ja in [
    # 踊りの文脈に合わない訳を直す
    ("fluid", "流れるような"), ("turns", "回転"), ("runs", "駆け足"), ("leaps", "跳躍"),
    ("kicks", "蹴り"), ("spins", "旋回"), ("moves", "動き"),
    ("shadowed", "影のようになぞった"), ("performed in succession", "順に演じられる"),
    ("performed in retrograde", "逆の順で演じられる"), ("mirrored", "鏡写しの"),
    ("eighth", "8分の1"), ("quarter", "4分の1"), ("half", "2分の1"),
    ("serene", "安らかな"), ("calm", "穏やかな"), ("passionate", "情熱的な"),
    ("aggressive", "攻撃的な"), ("sluggish", "鈍重な"), ("joyous", "喜びに満ちた"),
    ("quickly", "素早く"),
    # 動きの名前（文テンプレートにしか無かったものを語句として持つ）
    ("turns", "回転"), ("facial expressions", "表情"), ("hand gestures", "手の仕草"),
    ("straight walks", "直線の歩み"), ("curved walks", "曲線の歩み"),
    ("left kicks", "左の蹴り"), ("right kicks", "右の蹴り"),
    ("leg lifts", "脚上げ"), ("left leg lifts", "左脚上げ"), ("right leg lifts", "右脚上げ"),
    ("body level", "体の高さ"), ("body level changes", "体の高さの変化"),
    ("arm carriage", "腕の運び"), ("raised left arms", "左腕上げ"), ("raised right arms", "右腕上げ"),
    ("raised arms", "腕上げ"), ("independent body movement", "体の独立した動き"), ("sway", "揺れ"),
    ("forward bends", "前屈"), ("backward bends", "後屈"),
    ("leftward bends", "左への傾き"), ("rightward bends", "右への傾き"),
    ("footwork", "足さばき"), ("movement along the line of dance", "踊りの列に沿った移動"),
    ("special position", "特別な姿勢"), ("special positions", "特別な姿勢"),
    ("specific move", "決まった動き"), ("specific moves", "決まった動き"),
    # 動きに付く言葉
    ("repeated", "繰り返しの"), ("large", "大きな"), ("counterclockwise", "反時計回りの"), ("clockwise", "時計回りの"),
    ("aborted", "途中でやめる"), ("partially realized", "途中までしか行わない"),
    ("by group members", "集団の仲間による"), ("of the lead", "先導者の"), ("of the follower", "追従者の"),
    # 道筋は文の途中でつなぐので「〜ながら」
    ("along an intricate path", "複雑な道筋をたどりながら"),
    ("along an improvised path", "即興の道筋をたどりながら"),
    ("along a counterclockwise circle", "反時計回りの円を描きながら"),
    ("along a clockwise circle", "時計回りの円を描きながら"),
    ("turning counterclockwise", "反時計回りに回りながら"),
    ("turning clockwise", "時計回りに回りながら"),
    # 相手との関わり
    ("rarely make contact", "めったに触れ合いません"),
    ("maintain open contact", "離れたまま向き合い続けます"),
    ("dance closely", "身を寄せて踊ります"),
    # まとまった文
    ("The form guides dancers during improvised performances.", "この形式は、即興の演舞で踊り手を導きます。"),
    ("The rules of the form are applied by choreographers to produce individual dances which can be performed.",
     "この形式の規則を振付師が用いて、演じられる個々の舞踊が作られます。"),
]:
    t(en, ja)

# 踊りの種類（"sacred group celebration dance"）
KIND = [
    [("sacred", "神聖な"), ("social", "社交的な"), ("", "")],
    [("group", "集団の"), ("solo", "独りの"), ("", "")],
    [("celebration", "祝祭"), ("participation", "参加型"), ("performance", "演舞"),
     ("partner", "ペア"), ("war", "戦いの"), ("", "")],
]
for a_en, a_ja in KIND[0]:
    for b_en, b_ja in KIND[1]:
        for c_en, c_ja in KIND[2]:
            parts_en = [x for x in (a_en, b_en, c_en) if x]
            if not parts_en:
                continue
            t(" ".join(parts_en), a_ja + b_ja + c_ja)

# ---------------- 書き出しの一文 ----------------
FOR = [
    ("", ""),
    (" for a single pair", "一組の踊り手による"),
    (" for {N} dancers", "{N}人の踊り手による"),
    (" for {N} to {M} dancers", "{N}〜{M}人の踊り手による"),
    (" for {N} pairs", "{N}組の踊り手による"),
    (" for {N} to {M} pairs", "{N}〜{M}組の踊り手による"),
]
for fen, fja in FOR:
    for orig in (0, 1):
        for grew in (0, 1):
            for devised in (0, 1):
                n = 2  # {1}=形式名, {2}=種類
                en = "{1} is a {2} dance"
                f_en, f_ja = fen, fja
                for key in ("{N}", "{M}"):
                    if key in f_en:
                        n += 1
                        f_en = f_en.replace(key, "{%d}" % n)
                        f_ja = f_ja.replace(key, "{%d}" % n)
                en += f_en
                mods = []
                if orig:
                    n += 1
                    en += " originating in {%d}" % n
                    mods.append("{%d}で生まれ" % n)
                if grew:
                    n += 1
                    en += " which grew out of the performances of {%d}" % n
                    mods.append("{%d}の演奏から育ち" % n)
                if devised:
                    n += 1
                    en += " originally devised by {%d}" % n
                    mods.append("もともと{%d}が考案した" % n)
                en += "."
                head = "、".join(mods)
                if head:
                    head += "、"
                ja = "{1}は" + ("、" if head else "") + head + f_ja + "{2}舞踊です。"
                s(en, ja)

# ---------------- 伴奏 ----------------
s("the story of {1}", "{1}の物語")
s("a composition of {1}", "{1}による作品")
for acc_en, acc_ja in [("{2}", "{2}"), ("a composition of {2}", "{2}による曲")]:
    s(f"The dance is accompanied by {acc_en}.".replace("{2}", "{1}"),
      f"この舞踊には{acc_ja}が伴います。".replace("{2}", "{1}"))
    s(f"The dance is accompanied by {acc_en} as the dancers act out {{3}}.".replace("{2}", "{1}").replace("{3}", "{2}"),
      f"この舞踊には{acc_ja}が伴い、踊り手たちが{{3}}を演じます。".replace("{2}", "{1}").replace("{3}", "{2}"))
    s(f"The dance is accompanied by {acc_en} as the dancer acts out {{3}}.".replace("{2}", "{1}").replace("{3}", "{2}"),
      f"この舞踊には{acc_ja}が伴い、踊り手が{{3}}を演じます。".replace("{2}", "{1}").replace("{3}", "{2}"))

# ---------------- 隊形と動き ----------------
FORM = [("loosely mingled", "ゆるく入り混じって"), ("in a double circle", "二重の円になって"),
        ("in a circle", "円になって"), ("in several lines", "数列になって"), ("in a single line", "一列になって")]
TAIL = [
    ("", ""),
    (", moving {S} with the music", "{S}音楽に合わせて"),
    (", moving {S} to the music's {R} rhythm", "音楽の{R}のリズムに合わせて{S}"),
    (", moving {S} to the music's rhythm", "音楽のリズムに合わせて{S}"),
    (", moving {S} to the {R} rhythm", "{R}のリズムに合わせて{S}"),
]
for sub_en, sub_ja in [("The dancers perform", "踊り手たちは"), ("The dancer performs", "踊り手は")]:
    for fen, fja in FORM:
        for path in (0, 1):
            for ten, tja in TAIL:
                n = 0
                en = f"{sub_en} {fen}"
                ja = f"{sub_ja}{fja}"
                if path:
                    n += 1
                    en += " {%d}" % n
                    ja += "{%d}" % n
                t_en, t_ja = ten, tja
                for key in ("{S}", "{R}"):
                    if key in t_en:
                        n += 1
                        t_en = t_en.replace(key, "{%d}" % n)
                        t_ja = t_ja.replace(key, "{%d}" % n)
                en += t_en + "."
                ja += ("、" if t_ja else "") + t_ja + "踊ります。"
                s(en, ja)

# ---------------- 相手との関わり ----------------
s("The partners {1}.", "相手どうしは{1}。")
s("The partners {1}, communicating intent {2}.", "相手どうしは{2}意図を伝え合いながら、{1}。")
s("There are partner changes throughout the dance {1}.", "舞踊の間じゅう、{1}相手が入れ替わります。")
s("There are partner changes throughout the dance.", "舞踊の間じゅう、相手が入れ替わります。")
s("There are partner changes {1}.", "{1}相手が入れ替わります。")
s("The dancers imitate the movement of the {1}.", "踊り手たちは{1}の動きをまねます。")

# ---------------- 形式の格 ----------------
for pen, pja in [("position", "姿勢"), ("positions", "姿勢")]:
    for men, mja in [("move", "動き"), ("moves", "動き")]:
        s(f"This dance is a refined artform, with {{1}} special {pen} and {{2}} specific {men} to be mastered.",
          f"この舞踊は洗練された芸術で、{{1}}つの特別な{pja}と{{2}}通りの決まった{mja}を身につける必要があります。")
s("The entire dance has a basic movement {1}.", "舞踊全体の基本の動きは{1}です。")
s("There is a basic movement {1}.", "基本の動きは{1}です。")

# ---------------- 性格と見どころ ----------------
s("The dance is {1}.", "この舞踊は{1}ものです。")
s("This section is {1}.", "この節は{1}ものです。")
s("The {1} section is {2}.", "{1}の節は{2}ものです。")
s("The dance is punctuated by {1}.", "この舞踊には{1}が随所に現れます。")
s("This section is punctuated by {1}.", "この節には{1}が随所に現れます。")
s("The {1} section is punctuated by {2}.", "{1}の節には{2}が随所に現れます。")

# ---------------- 節の区切り ----------------
s("The dance begins with the {1} of the music.", "舞踊は音楽の{1}から始まります。")
s("The dance enters a new section with the {1} of the music.", "舞踊は音楽の{1}で新しい節に入ります。")
s("The {1} section is distinct.", "{1}の節は、それだけで独立しています。")

# ---------------- 書き出し ----------------
old = FIX.read_text(encoding="utf-8")
if MARK in old:
    old = old[: old.index(MARK)].rstrip("\n") + "\n"
lines = [MARK, "# scratchpad/gen_dance.py で作った。語句は translations/art-forms.tsv"]
seen = set()
for en, ja in sent:
    if en in seen:
        continue
    seen.add(en)
    lines.append(f"manual\tcore\t{en}\t{ja}")
FIX.write_text(old + "\n".join(lines) + "\n", encoding="utf-8")
print(f"文テンプレート {len(seen)} 件")

told = TERMS.read_text(encoding="utf-8")
if TMARK in told:
    told = told[: told.index(TMARK)].rstrip("\n") + "\n"
tl = [TMARK]
tseen = set()
for en, ja in terms:
    if en in tseen:
        continue
    tseen.add(en)
    tl.append(f"{en}\t{ja}")
TERMS.write_text(told + "\n".join(tl) + "\n", encoding="utf-8")
print(f"語句 {len(tseen)} 件")
