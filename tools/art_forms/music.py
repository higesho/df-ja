"""音楽の形式の説明文のテンプレートと、組み合わせでできる語句を作る。

出力:
  translations/sentences-fix.tsv に「芸術の形式（音楽）」の節を足す
  translations/art-forms.tsv に組み合わせでできる語句を足す
"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])
FIX = ROOT / "translations" / "sentences-fix.tsv"
TERMS = ROOT / "translations" / "art-forms.tsv"
MARK = "# === 芸術の形式（音楽）==="

sent = []   # (英語, 日本語)
terms = []  # (英語, 日本語)


def s(en, ja):
    sent.append((en, ja))


def t(en, ja):
    terms.append((en, ja))


# --- 1. 書き出しの一文 -------------------------------------------------
# "{形式名} is a {種類}[ directed toward the worship of {神}][ originating in {土地}]
#  [ which grew out of the performances of {集団}][ originally devised by {人}]."
TAILS = [
    (" directed toward the worship of {}", "{}への信仰に向けた", True),   # 名詞に直接かかる
    (" originating in {}", "{}で生まれ", False),
    (" which grew out of the performances of {}", "{}の演奏から育ち", False),
    (" originally devised by {}", "もともと{}が考案した", False),
]


def opening(kind_en, kind_ja, kind_is_slot):
    """種類が差し込み（{2}）か決まった語かで、2通り作る"""
    for mask in range(16):
        n = 1  # {1} は形式名
        en = "{1} is a "
        if kind_is_slot:
            n += 1
            en += "{%d}" % n
            kind = "{%d}" % n
        else:
            en += kind_en
            kind = kind_ja
        head, mids = "", []
        for i, (ten, tja, attaches) in enumerate(TAILS):
            if not mask & (1 << i):
                continue
            n += 1
            en += ten.format("{%d}" % n)
            if attaches:
                head = tja.format("{%d}" % n)
            else:
                mids.append(tja.format("{%d}" % n))
        en += "."
        if mids or head:
            ja = "{1}は、" + "".join(m + "、" for m in mids) + head + kind + "です。"
        else:
            ja = "{1}は" + kind + "です。"
        s(en, ja)


for _en, _ja in [
    ("form of music used during marches and military engagements", "行進や軍事行動の最中に用いられる音楽の形式"),
    ("devotional form of music", "信仰のための音楽の形式"),
    ("form of music used to commemorate important events", "重要な出来事を記念するために用いられる音楽の形式"),
    ("form of music used for entertainment", "娯楽のための音楽の形式"),
]:
    opening(_en, _ja, False)

# --- 2. 唱え手と楽器 ---------------------------------------------------
RECITE = [
    ("recites the words of {X}", "{X}の言葉を唱え"),
    ("recites a composition of {X}", "{X}からなる作品を唱え"),
    ("recites nonsensical words and sounds", "意味を成さない言葉と音を唱え"),
]
for ren, rja in RECITE:
    n = 1
    ren_f = ren.replace("{X}", "{2}") if "{X}" in ren else ren
    rja_f = rja.replace("{X}", "{2}") if "{X}" in rja else rja
    last = 3 if "{2}" in ren_f else 2
    s(f"A {{1}} {ren_f} while the music is played on a {{{last}}}.",
      f"{{1}}が{rja_f}、その間、音楽は{{{last}}}で演奏されます。")
    s(f"A {{1}} {ren_f} while the music is played on {{{last}}}.",
      f"{{1}}が{rja_f}、その間、音楽は{{{last}}}で演奏されます。")
    s(f"A {{1}} {ren_f}.", f"{{1}}が{rja_f}ます。")
s("The music is played on a {1}.", "音楽は{1}で演奏されます。")
s("The music is played on {1}.", "音楽は{1}で演奏されます。")

# --- 3. 演奏全体の指示 -------------------------------------------------
for subj_en, subj_ja in [("The entire performance", "演奏全体は")]:
    s(f"{subj_en} should {{1}} and {{2}}, and it is to {{3}}.", f"{subj_ja}{{1}}、{{2}}、そして{{3}}演奏されるべきです。")
    s(f"{subj_en} should {{1}} and {{2}}.", f"{subj_ja}{{1}}、{{2}}演奏されるべきです。")
    s(f"{subj_en} should {{1}}, and it is to {{2}}.", f"{subj_ja}{{1}}、そして{{2}}演奏されるべきです。")
    s(f"{subj_en} should {{1}}.", f"{subj_ja}{{1}}演奏されるべきです。")
    s(f"{subj_en} is to {{1}}.", f"{subj_ja}{{1}}演奏されるべきです。")
    s(f"{subj_en} {{1}}, and it is to {{2}}.", f"{subj_ja}{{1}}、そして{{2}}演奏されるべきです。")
    s(f"{subj_en} {{1}}.", f"{subj_ja}{{1}}演奏されます。")

# 楽節ごとの指示（"The passage" / "Each passage" / 楽節の名前）
for pre_en, pre_ja in [("The {1}", "{1}は"), ("Each {1}", "どの{1}も")]:
    s(f"{pre_en} should {{2}} and {{3}}, and it is to {{4}}.", f"{pre_ja}{{2}}、{{3}}、そして{{4}}演奏されるべきです。")
    s(f"{pre_en} should {{2}} and {{3}}.", f"{pre_ja}{{2}}、{{3}}演奏されるべきです。")
    s(f"{pre_en} should {{2}}, and it is to {{3}}.", f"{pre_ja}{{2}}、そして{{3}}演奏されるべきです。")
    s(f"{pre_en} should {{2}}.", f"{pre_ja}{{2}}演奏されるべきです。")
    s(f"{pre_en} is to {{2}}.", f"{pre_ja}{{2}}演奏されるべきです。")

# --- 4. 楽句の長さ -----------------------------------------------------
s("The melody and counterpoint both have {1} throughout the form.", "旋律と対位旋律はどちらも、形式を通じて{1}を用います。")
s("The melody has {1}, while the counterpoint has {2} throughout the form.", "旋律は{1}を、対位旋律は{2}を、形式を通じて用います。")
s("The melody has {1} throughout the form.", "旋律は形式を通じて{1}を用います。")
s("The counterpoint melody has {1} throughout the form.", "対位旋律は形式を通じて{1}を用います。")
for pre_en, pre_ja in [("Each passage", "どの楽節も"), ("The passage", "この楽節は")]:
    s(f"{pre_en} has {{1}} in the melody and counterpoint.", f"{pre_ja}旋律と対位旋律に{{1}}を用います。")
    s(f"{pre_en} has {{1}} in the melody, while the counterpoint has {{2}}.", f"{pre_ja}旋律に{{1}}を、対位旋律に{{2}}を用います。")
    s(f"{pre_en} has {{1}} in the melody.", f"{pre_ja}旋律に{{1}}を用います。")
    s(f"{pre_en} has {{1}} in the counterpoint melody.", f"{pre_ja}対位旋律に{{1}}を用います。")

# --- 5. 音階とリズム ---------------------------------------------------
SCALE = [
    ("without preference for a scale", "特定の音階にはよらず"),
    ("using the {S} scale", "{S}音階を用いて"),
]
RHYTHM = [
    ("in free rhythm", "自由なリズムで"),
    ("in the {R} rhythm", "{R}のリズムで"),
]
for subj_en, subj_ja in [("It is performed", ""), ("Each passage is performed", "どの楽節も"), ("The passage is performed", "この楽節は")]:
    for sen, sja in SCALE + [(None, None)]:
        for ren, rja in RHYTHM + [(None, None)]:
            if sen is None and ren is None:
                continue
            n = 0
            parts_en, parts_ja = [], []
            if sen is not None:
                if "{S}" in sen:
                    n += 1
                    parts_en.append(sen.replace("{S}", "{%d}" % n))
                    parts_ja.append(sja.replace("{S}", "{%d}" % n))
                else:
                    parts_en.append(sen)
                    parts_ja.append(sja)
            if ren is not None:
                if "{R}" in ren:
                    n += 1
                    parts_en.append(ren.replace("{R}", "{%d}" % n))
                    parts_ja.append(rja.replace("{R}", "{%d}" % n))
                else:
                    parts_en.append(ren)
                    parts_ja.append(rja)
            s(f"{subj_en} {' '.join(parts_en)}.", subj_ja + "、".join(parts_ja) + "演奏されます。")

# --- 6. 通して守ること -------------------------------------------------
s("Throughout, when possible, performers are to {1}.", "できるかぎり、演奏者は終始{1}ます。")
s("Throughout, when possible, composers and performers are to {1}.", "できるかぎり、作曲者と演奏者は終始{1}ます。")
for pre_en, pre_ja in [("Each passage", "どの楽節も"), ("The passage", "この楽節は")]:
    s(f"{pre_en} should be composed and performed using {{1}}.", f"{pre_ja}{{1}}を用いて作られ、演奏されるべきです。")
    s(f"{pre_en} should be performed using {{1}}.", f"{pre_ja}{{1}}を用いて演奏されるべきです。")

# --- 7. 旋律型 ---------------------------------------------------------
PATTERN = [("falling-rising", "下降して上昇する"), ("rising-falling", "上昇して下降する"), ("falling", "下降する"), ("rising", "上昇する")]
for when_en, when_ja in [("when improvising", "即興のとき"), ("when improvising or composing", "即興や作曲のとき")]:
    for pen, pja in PATTERN:
        s(f"From beginning to end, {when_en}, artists should {{1}} include a {pen} melody pattern.",
          f"初めから終わりまで、{when_ja}、芸術家は{{1}}{pja}旋律型を含めるべきです。")
        s(f"From beginning to end, {when_en}, artists should {{1}} include a {pen} melody pattern with {{2}}.",
          f"初めから終わりまで、{when_ja}、芸術家は{{1}}{pja}旋律型を{{2}}とともに含めるべきです。")
for pen, pja in PATTERN:
    s(f"Each passage should {{1}} include a {pen} melody pattern.", f"どの楽節も{{1}}{pja}旋律型を含めるべきです。")
    s(f"The passage should {{1}} include a {pen} melody pattern.", f"この楽節は{{1}}{pja}旋律型を含めるべきです。")

# リズムの仕組み（自動で作った訳は常体なので、ここで上書きする）
for en, ja in [
    ("The rhythm system is fundamentally polyrhythmic.", "リズムの仕組みは、根本からポリリズムです。"),
    ("The rhythm system is fundamentally polymetric.", "リズムの仕組みは、根本からポリメーターです。"),
    ("There are always multiple rhythm lines, and each of their bars is played over the same period of time, regardless of the number of beats.",
     "リズムの線はつねに複数あり、拍の数にかかわらず、どの線の小節も同じ長さの時間で演奏されます。"),
    ("There are always multiple rhythm lines, and the beats are always played together, even if one rhythm line completes (and then repeats) before the other is finished.",
     "リズムの線はつねに複数あり、一方の線が先に終わって繰り返しに入っても、拍はつねにそろえて演奏されます。"),
    ("The rhythm lines are thought of as one, without a primary-subordinate relationship, though individual lines can be named.",
     "リズムの線は主従のない一つのものとして捉えられますが、線ごとに名前を付けることもできます。"),
]:
    s(en, ja)

# --- 8. 声部の役割 -----------------------------------------------------
s("The {1} always {2}.", "{1}は常に{2}ます。")
s("Each {1} always {2}.", "どの{1}も常に{2}ます。")
s("The {1} is voiced by {2}.", "{1}は{2}が奏でます。")
s("Each of the {1} is voiced by {2}.", "どの{1}も{2}が奏でます。")

# --- 9. 構成 -----------------------------------------------------------
s("{1} has a simple structure: {2}.", "{1}の構成は単純です。{2}。")
s("{1} has the following structure: {2}.", "{1}の構成は次のとおりです。{2}。")
s("{1} has a well-defined multi-passage structure: {2}.", "{1}は、はっきりした複数楽節の構成を持ちます。{2}。")

# --- 10. 音域 ----------------------------------------------------------
# 1文に声部が2つ並ぶ（"A が全音域を使い、B は低音域から中音域までを使う"）
RANGE = [
    ("{S} covers its entire range from the {A} to the {B}", "{S}は{A}から{B}までの全音域を使", "い", "います"),
    ("{S} uses its entire range from the {A} to the {B}", "{S}は{A}から{B}までの全音域を使", "い", "います"),
    ("{S} ranges from the {A} to the {B}", "{S}は{A}から{B}までを使", "い", "います"),
    ("{S} covers its entire range", "{S}は全音域を使", "い", "います"),
    ("{S} uses its entire range", "{S}は全音域を使", "い", "います"),
    ("{S} stays in the {A}", "{S}は{A}にとどま", "り", "ります"),
    ("{S} is confined to the {A}", "{S}は{A}に限ら", "れ", "れます"),
]


def range_clause(form, start):
    """差し込みの番号を start から振り直して (英語, 日本語の語幹) を返す"""
    en, ja = form[0], form[1]
    n = start
    for key in ("{S}", "{A}", "{B}"):
        if key in en:
            en = en.replace(key, "{%d}" % n)
            ja = ja.replace(key, "{%d}" % n)
            n += 1
    return en, ja, n


for f1 in RANGE:
    en1, ja1, nxt = range_clause(f1, 1)
    s(en1 + ".", ja1 + f1[3] + "。")
    for f2 in RANGE:
        en2, ja2, _ = range_clause(f2, nxt)
        s(f"{en1} and {en2}.", f"{ja1}{f1[2]}、{ja2}{f2[3]}。")

# --- 11. 音階の作り方 --------------------------------------------------
s("Scales are conceived of as two chords built using a division of the perfect fourth interval into {1} notes.",
  "音階は、完全四度を{1}個の音に分けて組み立てた、二つの和音として捉えられます。")
s("Scales are constructed from {1} notes dividing the octave.", "音階は、オクターブを分ける{1}個の音から組み立てられます。")
s("Scales are constructed from {1} notes spaced evenly throughout the octave.",
  "音階は、オクターブに等間隔で並ぶ{1}個の音から組み立てられます。")
s("In quartertones, their spacing is roughly {1}, where 1 is the tonic, O marks the octave and x marks other notes.",
  "四分音で表すと、その並びはおよそ {1} です（1 が主音、O がオクターブ、x がそのほかの音）。")
s("It is called {1}.", "これは{1}と呼ばれます。")
s("The names are {1}.", "名前は{1}です。")
s("As always, the {1} scale is {2}.", "いつもどおり、{1}音階は{2}。")
s("The {1} scale is {2}.", "{1}音階は{2}。")
s("These chords are named {1} and {2}.", "これらの和音は{1}と{2}と呼ばれます。")
for _cen, _cja in [("pentachord", "五音和音"), ("tetrachord", "四音和音"), ("trichord", "三音和音")]:
    s(f"The {{1}} {_cen} is the {{2}} {{3}}.", f"{{1}}{_cja}は、{{3}}のうち{{2}}です。")
    s(f"The {{1}} {_cen} is the {{2}}.", f"{{1}}{_cja}は{{2}}です。")

# --- 12. リズム --------------------------------------------------------
s("The {1} rhythm is made from {2} patterns: {3}.", "{1}のリズムは{2}個のパターンから成ります。{3}。")
s("The {1} rhythm is a single line with {2} beats.", "{1}のリズムは、{2}拍からなる一本の線です。")
s("The {1} rhythm is a single line with {2} beats divided into {3} bars in a {4} pattern.",
  "{1}のリズムは、{2}拍を{3}小節に{4}の形で分けた、一本の線です。")
s("The beats are named {1}.", "拍の名前は{1}です。")

# --- 組み合わせでできる語句（構成の項目）--------------------------------
for art_en, art_ja in [("additional ", "さらにもう一つの"), ("another ", "別の"), ("", "")]:
    for len_en, len_ja in [("", ""), ("brief ", "短い"), ("lengthy ", "長い")]:
        for rel_en, rel_ja in [("", ""), ("unrelated ", "関連のない")]:
            t(f"{art_en}{len_en}{rel_en}passage", f"{art_ja}{rel_ja}{len_ja}楽節")
            t(f"{art_en}{len_en}{rel_en}passages", f"{art_ja}{rel_ja}{len_ja}楽節")
for len_en, len_ja in [("", ""), ("brief ", "短い"), ("lengthy ", "長い")]:
    t(f"{len_en}introduction", f"{len_ja}導入部")
    t(f"{len_en}verse", f"{len_ja}詩節")
    t(f"{len_en}verses", f"{len_ja}詩節")
    t(f"{len_en}chorus", f"{len_ja}反復部")
    t(f"{len_en}finale", f"{len_ja}終曲")
    t(f"{len_en}coda", f"{len_ja}終結部")
    t(f"{len_en}bridge-passage", f"{len_ja}橋渡しの楽節")
    for th_en, th_ja in [("theme", "主題"), ("first theme", "第一主題"), ("second theme", "第二主題")]:
        t(f"{len_en}{th_en}", f"{len_ja}{th_ja}")
        t(f"{len_en}exposition of the {th_en}", f"{th_ja}の{len_ja}提示部")
        t(f"{len_en}recapitulation of the {th_en}", f"{th_ja}の{len_ja}再現部")
        t(f"{len_en}series of variations on the {th_en}", f"{th_ja}による{len_ja}変奏の連なり")
    t(f"{len_en}recapitulation of the previous passage", f"前の楽節の{len_ja}再現部")
    t(f"{len_en}synthesis of the two themes", f"二つの主題の{len_ja}統合部")
    t(f"{len_en}synthesis of previous passages", f"前の楽節群の{len_ja}統合部")

# --- 書き出し -----------------------------------------------------------
old = FIX.read_text(encoding="utf-8")
if MARK in old:
    old = old[: old.index(MARK)].rstrip("\n") + "\n"
lines = [MARK, "# tools/sentences/… ではなく scratchpad/gen_music.py で作った。語句は translations/art-forms.tsv"]
seen = set()
for en, ja in sent:
    if en in seen:
        continue
    seen.add(en)
    lines.append(f"manual\tcore\t{en}\t{ja}")
FIX.write_text(old + "\n".join(lines) + "\n", encoding="utf-8")
print(f"文テンプレート {len(seen)} 件")

tmark = "# --- 構成の項目（組み合わせ）---"
told = TERMS.read_text(encoding="utf-8")
if tmark in told:
    told = told[: told.index(tmark)].rstrip("\n") + "\n"
have = {l.split("\t")[0] for l in told.splitlines() if l.strip() and not l.startswith("#")}
tl = [tmark]
tseen = set()
for en, ja in terms:
    if en in have or en in tseen or not en:
        continue
    tseen.add(en)
    tl.append(f"{en}\t{ja}")
TERMS.write_text(told + "\n".join(tl) + "\n", encoding="utf-8")
print(f"語句 {len(tseen)} 件")
