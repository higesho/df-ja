"""詩の形式の説明文（実行ファイルの e8e2e0）のテンプレートと語句を作る。"""
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])
FIX = ROOT / "translations" / "sentences-fix.tsv"
TERMS = ROOT / "translations" / "art-forms.tsv"
MARK = "# === 芸術の形式（詩）==="
TMARK = "# --- 詩の形式の語句 ---"

sent, terms = [], []
s = lambda en, ja: sent.append((en, ja))
s_ = s
t = lambda en, ja: terms.append((en, ja))

# ---------------- 語句 ----------------
for en, ja in [
    # 連の種類
    ("octet", "八行連"), ("septet", "七行連"), ("sexain", "六行連"), ("quintain", "五行連"),
    ("quatrain", "四行連"), ("tercet", "三行連"), ("couplet", "二行連"),
    ("octets", "八行連"), ("septets", "七行連"), ("sexains", "六行連"), ("quintains", "五行連"),
    ("quatrains", "四行連"), ("tercets", "三行連"), ("couplets", "二行連"),
    ("stanza", "連"), ("stanzas", "連"), ("line", "行"), ("lines", "行"),
    ("verse paragraph", "詩節"), ("verse paragraphs", "詩節"),
    ("brief verse paragraph", "短い詩節"), ("brief verse paragraphs", "短い詩節"),
    ("long verse paragraph", "長い詩節"), ("long verse paragraphs", "長い詩節"),
    ("lengthy verse paragraph", "長い詩節"), ("lengthy verse paragraphs", "長い詩節"),
    ("full verse paragraph", "完全な詩節"), ("full verse paragraphs", "完全な詩節"),
    ("part", "部"), ("parts", "部"), ("section", "節"), ("sections", "節"),
    ("refrain", "折り返し"), ("parallelism", "対句法"), ("a chosen subject", "ある定まった主題"),
    ("the subject of the poem", "詩の主題"),
    # 順番
    ("third", "3番目"), ("sixth", "6番目"), ("seventh", "7番目"), ("eighth", "8番目"),
    ("ninth", "9番目"), ("tenth", "10番目"), ("last", "最後"), ("final", "最終"),
    # 韻律
    ("foot", "音歩"), ("feet", "音歩"),
    ("iambic", "弱強格"), ("trochaic", "強弱格"), ("spondaic", "長長格"), ("dactylic", "長短短格"),
    ("amphibrachic", "短長短格"), ("anapaestic", "短短長格"), ("cretic", "長短長格"),
    ("pyrrhic", "短短格"), ("tribrachic", "短短短格"), ("bacchic", "短長長格"),
    ("antibacchic", "長長短格"), ("molossic", "長長長格"),
    ("monometer", "一歩格"), ("dimeter", "二歩格"), ("trimeter", "三歩格"), ("tetrameter", "四歩格"),
    ("pentameter", "五歩格"), ("hexameter", "六歩格"), ("heptameter", "七歩格"), ("octameter", "八歩格"),
    # 切れ目
    ("a terminal caesura", "行末の切れ目"), ("a medial caesura", "行中の切れ目"),
    ("an initial caesura", "行頭の切れ目"),
    # 修辞（文脈に合わない訳を直す）
    ("consonance", "子音韻"), ("symbolism", "象徴"),
    # 部の性格（文の中でつなぐので連用形）
    ("is dramatic", "劇的です"), ("is reflective", "内省的です"), ("is ribald", "猥雑です"),
    ("is light", "軽妙です"), ("is solemn", "荘重です"), ("is a riddle", "なぞなぞです"),
    ("is a narrative", "物語です"),
    # ねらい（既訳に無いもの）
    ("to make a counter-assertion", "反論しようとする"),
    ("to synthesize previous ideas", "それまでの着想をまとめようとする"),
    ("to develop the previous idea", "前の着想を発展させようとする"),
    ("to invert the previous assertion", "前の主張を反転させようとする"),
    ("to undercut the previous assertion", "前の主張を切り崩そうとする"),
    ("to move away from previous ideas", "それまでの着想から離れようとする"),
    ("to reflect on previous ideas", "それまでの着想を省みようとする"),
    ("to offer a different perspective", "異なる見方を示そうとする"),
    # 行どうしの関わり（並べるので連用形）
    ("often share an underlying meaning", "しばしば根底の意味を共有し"),
    ("often contrast underlying meaning", "しばしば根底の意味を対比させ"),
    ("are required to maintain phrasing", "言い回しを保つことを求められ"),
    ("have similar grammatical structures", "似た文法構造を持ち"),
    ("use the same placement of allusions", "同じ位置に引喩を置き"),
    ("sometimes have reversed word orders", "ときに語順が逆になり"),
    ("reverse grammatical structures", "文法構造を逆転させ"),
    ("present different views of the same subject", "同じ主題について異なる見方を示し"),
    # 見た目の技巧
    ("lines which emerge when reading along certain prescribed paths", "決まった経路に沿って読むと現れる行"),
    ("lines which emerge when reading along certain prescribed paths across the body of the poem", "詩全体の決まった経路に沿って読むと現れる行"),
    ("lines which can be read orthogonally across the standard lines", "通常の行を横切って直角に読める行"),
    ("lines which can be read backwards as well as forwards", "前からも後ろからも読める行"),
    ("lines with different readings depending on word breaks", "語の区切りで読みが変わる行"),
    # まとまった文
    ("The form guides poets during improvised performances.", "この形式は、即興の詩作で詩人を導きます。"),
    ("The rules of the form are applied by poets to produce individual poems which can be recited.", "この形式の規則を詩人が用いて、朗誦できる個々の詩が作られます。"),
    ("As a rule throughout the poem, the end rhymes don't generally match perfectly.", "詩全体の決まりとして、行末の韻は必ずしも完全には一致しません。"),
    ("In this part of the poem, the end rhymes don't need to match perfectly.", "詩のこの部分では、行末の韻は完全に一致しなくてもかまいません。"),
]:
    t(en, ja)

# 行どうしの関わり（1行ずつ述べる形）
REL = [
    ("shares the underlying meaning of", "と根底の意味を共有します"),
    ("contrasts the underlying meaning of", "と根底の意味を対比させます"),
    ("is required to maintain the phrasing of", "の言い回しを保たなければなりません"),
    ("has the same grammatical structure as", "と同じ文法構造を持ちます"),
    ("uses the same placement of allusions as", "と同じ位置に引喩を置きます"),
    ("reverses the word order of", "の語順を逆にします"),
    ("reverses the grammatical structure of", "の文法構造を逆にします"),
    ("presents a different view of the subject of", "の主題について異なる見方を示します"),
    ("must expand the idea of", "の着想を広げなければなりません"),
]

# 声調・音節量・強勢の型
TONE = ["even", "uneven"]
for a in TONE:
    for b in TONE:
        t(f"{a}-{b}", ("平" if a == "even" else "仄") + ("平" if b == "even" else "仄"))
        for c in TONE:
            t(f"{a}-{b}-{c}", "".join("平" if x == "even" else "仄" for x in (a, b, c)))
for a in ["short", "long"]:
    for b in ["short", "long"]:
        t(f"{a}-{b}", ("短" if a == "short" else "長") + ("短" if b == "short" else "長"))
        for c in ["short", "long"]:
            t(f"{a}-{b}-{c}", "".join("短" if x == "short" else "長" for x in (a, b, c)))
for a in ["unstressed", "stressed"]:
    for b in ["unstressed", "stressed"]:
        t(f"{a}-{b}", ("弱" if a == "unstressed" else "強") + ("弱" if b == "unstressed" else "強"))
        for c in ["unstressed", "stressed"]:
            t(f"{a}-{b}-{c}", "".join("弱" if x == "unstressed" else "強" for x in (a, b, c)))

# ---------------- 書き出しの一文 ----------------
# ねらいと主題（"to praise concerning a chosen subject"）は、ひとつの差し込みにして
# 下の「ねらい」のテンプレートに任せる。英語では主題が "concerning" を挟む形と挟まない形がある
ADJ = [("", ""), ("solemn ", "荘重な"), ("light ", "軽妙な"), ("ribald ", "猥雑な"),
       ("reflective ", "内省的な"), ("dramatic ", "劇的な")]
for aen, aja in ADJ:
  for ken, kja in [("form", "詩の形式"), ("riddle", "なぞなぞ詩"), ("narrative", "物語詩")]:
    for intended in (0, 1):
        for orig in (0, 1):
            for grew in (0, 1):
                for devised in (0, 1):
                    n = 1  # {1}=形式名
                    en = "{1} is a " + aen + "poetic " + ken
                    purpose = place = group = person = None
                    if intended:
                        n += 1
                        purpose = "{%d}" % n
                        en += " intended " + purpose
                    if orig:
                        n += 1
                        place = "{%d}" % n
                        en += ", originating in " + place
                    if grew:
                        n += 1
                        group = "{%d}" % n
                        en += " which grew out of the performances of " + group
                    if devised:
                        n += 1
                        person = "{%d}" % n
                        en += " originally devised by " + person
                    en += "."
                    mods = []
                    if place:
                        mods.append(f"{place}で生まれ")
                    if group:
                        mods.append(f"{group}の演奏から育ち")
                    if person:
                        mods.append(f"もともと{person}が考案した")
                    head = "、".join(mods)
                    if head:
                        head += "、"
                    body = head + (purpose or "") + aja + kja
                    ja = "{1}は" + ("、" if head or purpose else "") + body + "です。"
                    s_(en, ja)

# ねらい（主題を伴う形）。差し込みの中でもう一度このテンプレートが使われる
PURPOSE = [
    ("to describe", "描写しようとする"), ("to satirize", "風刺しようとする"),
    ("to amuse the audience", "聴衆を楽しませようとする"), ("to complain about", "不満を述べようとする"),
    ("to renounce", "放棄しようとする"), ("to make an apology", "謝罪しようとする"),
    ("to express pleasure with", "喜びを表そうとする"), ("to express grief over", "嘆きを表そうとする"),
    ("to praise", "称賛しようとする"), ("to beseech", "懇願しようとする"),
    ("to teach a moral lesson", "道徳的な教訓を伝えようとする"), ("to make an assertion", "主張しようとする"),
    ("to make a concession", "譲歩しようとする"), ("to console the audience", "聴衆を慰めようとする"),
    ("to refuse consolation", "慰めを拒もうとする"), ("to make a counter-assertion", "反論しようとする"),
    ("to synthesize previous ideas", "それまでの着想をまとめようとする"),
    ("to develop the previous idea", "前の着想を発展させようとする"),
    ("to invert the previous assertion", "前の主張を反転させようとする"),
    ("to undercut the previous assertion", "前の主張を切り崩そうとする"),
    ("to move away from previous ideas", "それまでの着想から離れようとする"),
    ("to reflect on previous ideas", "それまでの着想を省みようとする"),
    ("to offer a different perspective", "異なる見方を示そうとする"),
]
for pen, pja in PURPOSE:
    s_(f"{pen} concerning {{1}}", f"{{1}}について{pja}")
    s_(f"{pen} {{1}}", f"{{1}}について{pja}")

# ---------------- 詩の組み立て ----------------
s("The poem is divided into {1} distinct parts: {2}.", "詩は{1}つの異なる部に分かれます。{2}。")
s("The poem is divided into two distinct {1}.", "詩は、異なる二つの{1}に分かれます。")
s("The poem is divided into {1}.", "詩は{1}に分かれます。")
s("The poem is a single {1}.", "詩は一つの{1}から成ります。")
s("The poem is a series of {1}.", "詩は一連の{1}から成ります。")
s("The poem is an extremely long series of {1}.", "詩は非常に長く続く{1}から成ります。")
s("The poem is numerous series of {1}.", "詩はいくつもの一連の{1}から成ります。")
s("{1} is always written from the perspective of {2}.", "{1}はつねに{2}の視点から書かれます。")
s("Use of {1} is characteristic of the form.", "{1}を用いるのが、この形式の特徴です。")
for fen, fja in [("Forms of parallelism are", "対句法"), ("A form of parallelism is", "一つの対句法")]:
    for wen, wja in [("certain lines", "特定の行が"), ("they", "行どうしが")]:
        s(f"{fen} common throughout the poem, in that {wen} {{1}}.", f"{fja}が詩の全体に見られ、{wja}{{1}}ます。")
s("Linguistic skill is required in the visual presentation as well, as {1} must feature {2}.",
  "見た目の上でも言葉の技量が求められ、{1}は{2}を備えなければなりません。")

# ---------------- 韻律 ----------------
PAT = [
    ("a tone pattern of {P}", "{P}の声調型", ""),
    ("a syllable weight pattern of {P} (quantitative {F} {M})", "{P}の音節量型", "（量的な{F}{M}）"),
    ("an accent pattern of {P} (qualitative {F} {M})", "{P}の強勢型", "（質的な{F}{M}）"),
]
METER_SUBJ = [
    ("The poem", "詩の各行は", 0), ("Each line", "各行は", 0), ("It", "この行は", 0),
    ("The {1} part", "{1}の部の各行は", 1), ("The {1} line", "{1}の行は", 1),
]
for sen, sja, used in METER_SUBJ:
    for verb_en, verb_ja in [(" has ", ""), (" has lines with ", "")]:
        if verb_en == " has lines with " and sen in ("Each line", "It", "The {1} line"):
            continue
        for foot_en in ("foot", "feet"):
            for pen, pja, pnote in PAT:
                n = used
                n += 1
                cnt = "{%d}" % n
                en = f"{sen}{verb_en}{cnt} {foot_en} with "
                ja = f"{sja}{cnt}音歩で、"
                body_en, body_ja, note = pen, pja, pnote
                for key in ("{P}", "{F}", "{M}"):
                    if key in body_en:
                        n += 1
                        body_en = body_en.replace(key, "{%d}" % n)
                        body_ja = body_ja.replace(key, "{%d}" % n)
                        note = note.replace(key, "{%d}" % n)
                s_(en + body_en + ".", ja + body_ja + note + "を持ちます。")
for sen, sja, used in [("The poem", "詩は", 0), ("Each line", "各行は", 0), ("It", "この行は", 0),
                       ("The {1} part", "{1}の部の各行は", 1), ("The {1} line", "{1}の行は", 1)]:
    cnt = "{%d}" % (used + 1)
    s_(f"{sen} has {cnt} syllables.", f"{sja}{cnt}音節です。")
    if used == 1 and sen == "The {1} part":
        s_(f"{sen} has lines with {cnt} syllables.", f"{sja}{cnt}音節です。")

CAESURA = [("a terminal caesura", "行末の切れ目"), ("a medial caesura", "行中の切れ目"), ("an initial caesura", "行頭の切れ目")]
for cen, cja in CAESURA:
    s_(f"The poem has {cen}.", f"詩には{cja}があります。")
    s_(f"The poem has {cen} in each line.", f"詩はどの行にも{cja}があります。")
    s_(f"Every line of the poem has {cen}.", f"詩のどの行にも{cja}があります。")
    s_(f"It has {cen}.", f"これには{cja}があります。")
    s_(f"It has {cen} in each line.", f"どの行にも{cja}があります。")
    s_(f"The {{1}} part has {cen}.", f"{{1}}の部には{cja}があります。")
    s_(f"The {{1}} part has {cen} in each line.", f"{{1}}の部はどの行にも{cja}があります。")
    s_(f"The {{1}} line has {cen}.", f"{{1}}の行には{cja}があります。")

# ---------------- 韻 ----------------
SCOPE = [
    ("of the poem", "詩の"),
    ("of this part", "この部の"),
    ("of the {X} part", "{X}の部の"),
]
for sc_en, sc_ja in SCOPE:
    n = 1
    en = sc_en.replace("{X}", "{1}")
    ja = sc_ja.replace("{X}", "{1}")
    nxt = 2 if "{X}" in sc_en else 1
    s(f"The ending of each line {en} shares the same rhyme.", f"{ja}どの行も、行末が同じ韻を踏みます。")
    s(f"The ending of each line {en} shares the same rhyme, though the rhyming doesn't have to be perfect.",
      f"{ja}どの行も、行末が同じ韻を踏みます。ただし韻は完全でなくてもかまいません。")
    s(f"The ending of each line {en} shares the same rhyme, though rhymes at the end of lines in the {{{nxt}}} section don't need to match perfectly.",
      f"{ja}どの行も、行末が同じ韻を踏みます。ただし{{{nxt}}}節の行末の韻は、完全に一致しなくてもかまいません。")
RSCOPE = [
    ("of the poem", "詩の"),
    ("repeating in each stanza", "どの連でも繰り返される"),
    ("within each stanza", "各連の中での"),
    ("within this stanza", "この連の中での"),
    ("respecting the full poem", "詩全体にわたる"),
    ("repeating in each stanza of the {X} part", "{X}の部のどの連でも繰り返される"),
    ("within each stanza of the {X} part", "{X}の部の各連の中での"),
    ("within the {X} part", "{X}の部の中での"),
    ("of the {X} part", "{X}の部の"),
]
for sc_en, sc_ja in RSCOPE:
    n = 1
    en = sc_en
    ja = sc_ja
    if "{X}" in en:
        en, ja = en.replace("{X}", "{1}"), ja.replace("{X}", "{1}")
        n = 2
    s(f"The rhyme scheme {en} is {{{n}}}.", f"{ja}押韻構成は{{{n}}}です。")
    s(f"The rhyme scheme {en} is {{{n}}}, where numbers indicate a refrain.",
      f"{ja}押韻構成は{{{n}}}です（数字は折り返しを表します）。")
s("The rhyme at the end of the {1} line doesn't need to match perfectly.", "{1}の行の行末の韻は、完全に一致しなくてもかまいません。")
s("The rhymes at the end of the {1} lines don't need to match perfectly.", "{1}の行の行末の韻は、完全に一致しなくてもかまいません。")

# ---------------- 折り返し ----------------
s("The refrain occurs as lines {1}.", "折り返しは{1}行目に現れます。")
s("The refrain occurs as lines {1} and {2}.", "折り返しは{1}行目と{2}行目に現れます。")
s("The {1} refrain occurs as lines {2} and {3}.", "{1}の折り返しは{2}行目と{3}行目に現れます。")
s("The refrain occurs as line {1}.", "折り返しは{1}行目に現れます。")
s("The {1} refrain occurs as lines {2}.", "{1}の折り返しは{2}行目に現れます。")
s("The {1} refrain occurs as line {2}.", "{1}の折り返しは{2}行目に現れます。")
s("The {1} refrain occurs as line {2} and the {3} refrain occurs as line {4}.",
  "{1}の折り返しは{2}行目に、{3}の折り返しは{4}行目に現れます。")
s("The {1} refrain occurs as lines {2} of the {3} part.", "{1}の折り返しは、{3}の部の{2}行目に現れます。")
s("The {1} refrain occurs as line {2} of the {3} part.", "{1}の折り返しは、{3}の部の{2}行目に現れます。")

# ---------------- 部・行ごとの決まり ----------------
for sen, sja in [("The {1} part", "{1}の部は"), ("The {1} line", "{1}の行は"), ("It", "これは")]:
    k = 2 if "{1}" in sen else 1
    a, b, c = "{%d}" % k, "{%d}" % (k + 1), "{%d}" % (k + 2)
    # 性格は決まった語なので、差し込みにせず文に書く（"The {1} part {2}." は広く当たりすぎる）
    for _cen, _cja in [("is dramatic", "劇的です"), ("is reflective", "内省的です"), ("is ribald", "猥雑です"),
                       ("is light", "軽妙です"), ("is solemn", "荘重です"), ("is a riddle", "なぞなぞです"),
                       ("is a narrative", "物語です")]:
        s(f"{sen} {_cen} and is intended {a} concerning {b}.", f"{sja}{_cja}。また、{b}について{a}ものです。")
        s(f"{sen} {_cen} and is intended {a}.", f"{sja}{_cja}。また、{a}ものです。")
        s(f"{sen} {_cen}.", f"{sja}{_cja}。")
    for _ren, _rja in [
        ("can be read backwards as well as forwards", "前からも後ろからも読めます"),
        ("has different readings depending on word breaks", "語の区切りによって読みが変わります"),
    ]:
        s(f"{sen} {_ren}.", f"{sja}{_rja}。")
    s(f"{sen} can be read backwards as well as forwards and has different readings depending on word breaks.",
      f"{sja}前からも後ろからも読め、語の区切りによって読みが変わります。")
    s(f"{sen} is intended {a} concerning {b}.", f"{sja}{b}について{a}ものです。")
    s(f"{sen} is intended {a}.", f"{sja}{a}ものです。")
    s(f"{sen} is written from the perspective of {a}.", f"{sja}{a}の視点から書かれます。")
    s(f"{sen} must make use of {a}.", f"{sja}{a}を用いなければなりません。")
    s(f"{sen} includes {a}.", f"{sja}{a}を含みます。")
    s(f"{sen} concerns {a}.", f"{sja}{a}を扱います。")
s("Certain lines of the {1} part {2}.", "{1}の部の特定の行は{2}ます。")
s("Certain lines {1}.", "特定の行は{1}ます。")
for ren, rja in REL:
    s(f"In the {{1}} part, the {{2}} line of each {{3}} {ren} the {{4}} line.",
      f"{{1}}の部では、どの{{3}}でも{{2}}の行が{{4}}の行{rja}。")
    s(f"In the {{1}} part, the {{2}} line of the {{3}} {ren} the {{4}} line.",
      f"{{1}}の部では、{{3}}の{{2}}の行が{{4}}の行{rja}。")
    s(f"The {{1}} line of each {{2}} {ren} the {{3}} line.", f"どの{{2}}でも、{{1}}の行が{{3}}の行{rja}。")
    s(f"The {{1}} line of the {{2}} {ren} the {{3}} line.", f"{{2}}の{{1}}の行が、{{3}}の行{rja}。")

# ---------------- 書き出し ----------------
old = FIX.read_text(encoding="utf-8")
if MARK in old:
    old = old[: old.index(MARK)].rstrip("\n") + "\n"
lines = [MARK, "# scratchpad/gen_poem.py で作った。語句は translations/art-forms.tsv"]
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
