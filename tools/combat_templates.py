"""戦闘の文（"The kea bites the stray dog in the left front leg, denting the skin and bruising the fat!"）の文テンプレートを作る。
使い方（dfint-ja で）: python -I -X utf8 tools/combat_templates.py  → translations/combat.tsv（build.py が読む）

ゲームは「主語 + 攻撃の動詞 + 相手 in the 部位 (with 武器), 傷の列挙!」を1文に組み立てて addst で描く。
動詞は生物・アイテムの RAW の ATTACK_VERB / ATTACK（"bite:bites" など）。主語が You のときは原形、それ以外は三人称形。
傷の列挙（"denting the skin and bruising the fat"）は、訳では文の後ろに（皮膚にへこみ、脂肪に打撲）とまとめる。
（"… with his hand and the injured part …" の " and the injured part" は、エンジンが ", the injured part" に直してから照合する）
"""
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "translations" / "combat.tsv"

# 原形, 三人称形, 訳（過去形。「相手の部位」の後ろに付く）
VERBS = [
    ("bite", "bites", "に噛みついた"),
    ("scratch", "scratches", "を引っかいた"),
    ("kick", "kicks", "を蹴った"),
    ("slap", "slaps", "を平手打ちした"),
    ("punch", "punches", "を殴った"),
    ("snatch at", "snatches at", "につかみかかった"),
    ("snatch", "snatches", "につかみかかった"),
    ("gore", "gores", "を角で突いた"),
    ("stab", "stabs", "を刺した"),
    ("stab at", "stabs at", "を突いた"),
    ("slice", "slices", "を切り裂いた"),
    ("lash", "lashes", "を打ちすえた"),
    ("claw", "claws", "を爪で裂いた"),
    ("sting", "stings", "を刺した"),
    ("bash", "bashes", "を殴りつけた"),
    ("drill", "drills", "に穴をあけた"),
    ("hack", "hacks", "を叩き斬った"),
    ("saw", "saws", "を挽き切った"),
    ("slash", "slashes", "を斬りつけた"),
    ("stick", "sticks", "を突き刺した"),
    ("strike", "strikes", "を打った"),
    ("hit", "hits", "に命中した"),
    ("shove", "shoves", "を突き飛ばした"),
    ("push", "pushes", "を押した"),
    ("headbutt", "headbutts", "に頭突きした"),
]

# 体の部位で攻撃するときの手足（"with his first toe, right foot"）
LIMBS = [(f"{lr} {p}", f"{lj}{pj}") for lr, lj in (("left", "左"), ("right", "右")) for p, pj in (
    ("foot", "足"), ("hand", "手"), ("front paw", "前足"), ("rear paw", "後足"), ("front foot", "前足"), ("rear foot", "後足"), ("wing", "翼"))]

# 「, but …!」の結び（攻撃が通らなかったとき）
BUTS = [
    ("but the attack glances away", "攻撃はそれた"),
    ("but the attack passes right through", "攻撃は素通りした"),
    ("but there is no force", "力がこもっていなかった"),
    ("but the attack is deflected by {9}", "{9}に防がれた"),
    ("lightly tapping the target", "軽く触れただけだった"),
]

# 傷の列挙の項目（値として訳す。" and " と ", " で分けた1つずつ）
EFFECTS = [
    ("bruising the {1}", "{1}に打撲"),
    ("denting the {1}", "{1}にへこみ"),
    ("tearing the {1}", "{1}に裂傷"),
    ("tearing apart the {1}", "{1}がずたずたに"),
    ("tearing through the {1}", "{1}を引き裂く"),
    ("fracturing the {1}", "{1}を骨折"),
    ("shattering the {1}", "{1}を粉砕"),
    ("chipping the {1}", "{1}が欠ける"),
    ("breaking away the {1}", "{1}がはがれる"),
    ("jamming the {1} through the {2}", "{1}が{2}を貫く"),
    ("the severed part sails off in an arc", "切断された部位が弧を描いて飛んだ"),
    ("the injured part is cloven asunder", "負傷した部位が真っ二つになった"),
    ("the injured part is ripped into loose shreds", "負傷した部位がずたずたになった"),
    ("the injured part is crushed", "負傷した部位が潰れた"),
    ("the injured part collapses", "負傷した部位が崩れた"),
    ("the injured part is torn apart", "負傷した部位が引きちぎられた"),
    ("the injured part explodes into gore", "負傷した部位が血肉となって飛び散った"),
    ("the injured part is smashed into the body, an unrecognizable mass", "負傷した部位が体にめり込み、原形をとどめない"),
    ("the injured part splits in gore", "負傷した部位が血まみれに裂けた"),
    ("the injured part collapses into a lump of gore", "負傷した部位が血肉の塊になった"),
    ("it is mostly cut away from the rest of the torso", "胴体からほとんど切り離された"),
    ("spilling his guts", "はらわたが飛び出した"),
    ("spilling her guts", "はらわたが飛び出した"),
    ("spilling its guts", "はらわたが飛び出した"),
    ("spilling their guts", "はらわたが飛び出した"),
]

# 1文の戦闘の知らせ（主語は {1}。You の形も作る）
SIMPLE = [
    ("{1} attacks {2} but {3} jumps away!", "You attack {2} but {3} jumps away!", "{1}は{2}に攻撃したが、かわされた！"),
    ("{1} misses {2}!", "You miss {2}!", "{1}の攻撃は{2}に外れた！"),
    ("{1} is knocked over!", "You are knocked over!", "{1}は倒された！"),
    ("{1} has been knocked unconscious!", "You have been knocked unconscious!", "{1}は気絶した！"),
    ("{1} has been stunned!", "You have been stunned!", "{1}は朦朧としている！"),
    ("{1} has been stunned again!", "You have been stunned again!", "{1}はまた朦朧としている！"),
    ("{1} is having trouble breathing!", "You are having trouble breathing!", "{1}は息が苦しそうだ！"),
    ("{1} is having more trouble breathing!", "You are having more trouble breathing!", "{1}はさらに息が苦しそうだ！"),
    ("{1} looks sick!", "You feel sick!", "{1}は具合が悪そうだ！"),
    ("{1} looks even more sick!", "You feel even more sick!", "{1}はさらに具合が悪そうだ！"),
    ("{1} gives in to pain.", "You give in to pain.", "{1}は痛みに屈した。"),
    ("{1} falls over.", "You fall over.", "{1}は倒れた。"),
    ("{1} regains consciousness.", "You regain consciousness.", "{1}は意識を取り戻した。"),
    ("{1} is no longer stunned.", "You are no longer stunned.", "{1}の朦朧状態が解けた。"),
    ("{1} stands up.", "You stand up.", "{1}は立ち上がった。"),
    ("{1} vomits.", "You vomit.", "{1}は嘔吐した。"),
    ("{1} has bled to death.", "You have bled to death.", "{1}は失血死した。"),
    ("{1} is propelled away by the force of the blow!", "You are propelled away by the force of the blow!", "{1}は打撃の勢いで吹き飛ばされた！"),
    ("{1} latches on firmly!", "You latch on firmly!", "{1}はしっかりと食らいついた！"),
    ("{1} become enraged!", "You become enraged!", "{1}は激怒した！"),
    ("{1} becomes enraged!", "You become enraged!", "{1}は激怒した！"),
    ("{1} jumps away from {2}!", "You jump away from {2}!", "{1}は{2}をかわした！"),
    ("{1} jumps away from the flying {2}!", "You jump away from the flying {2}!", "{1}は飛んできた{2}をかわした！"),
    ("{1} blocks the flying {2} with {3}!", "You block the flying {2} with {3}!", "{1}は飛んできた{2}を{3}で防いだ！"),
    ("{1} blocks {2} with {3}!", "You block {2} with {3}!", "{1}は{2}を{3}で防いだ！"),
    ("{1} parries {2} with {3}!", "You parry {2} with {3}!", "{1}は{2}を{3}で受け流した！"),
    ("{1} has become enraged!", "You have become enraged!", "{1}は激怒した！"),
    ("{1} bounces backward!", "You bounce backward!", "{1}は後ろに跳ね返された！"),
    ("{1} collides with {2}!", "You collide with {2}!", "{1}は{2}にぶつかった！"),
    ("{1} jumps out of {2}'s flight path!", "You jump out of {2}'s flight path!", "{1}は飛んでくる{2}をよけた！"),
    ("{1} is knocked over and tumbles backward!", "You are knocked over and tumble backward!", "{1}は倒されて後ろに転がった！"),
    ("{1} slams into an obstacle!", "You slam into an obstacle!", "{1}は障害物に激突した！"),
    ("{1} slams into {2}!", "You slam into {2}!", "{1}は{2}に激突した！"),
    ("{1} skids along the ground!", "You skid along the ground!", "{1}は地面を滑った！"),
    ("{1} skids along the ground, {2}!", "You skid along the ground, {2}!", "{1}は地面を滑った（{2}）！"),
    ("{1} grabs {2} by the {3} with {4}!", "You grab {2} by the {3} with {4}!", "{1}は{4}で{2}の{3}をつかんだ！"),
    ("{1} grabs {2} by the {3} with {4}, but the attack glances away!", "You grab {2} by the {3} with {4}, but the attack glances away!", "{1}は{4}で{2}の{3}をつかもうとしたが、それた！"),
    ("{1} releases the grip of {2} on {3}.", "You release the grip of {2} on {3}.", "{1}は{3}をつかんでいた{2}を放した。"),
    ("{1} breaks the grip of {2} on {3}.", "You break the grip of {2} on {3}.", "{1}は{3}をつかんでいた{2}を振りほどいた。"),
    ("{1} attacks {2} but {3} scrambles away!", "You attack {2} but {3} scrambles away!", "{1}は{2}に攻撃したが、逃げられた！"),
    ("{1} scrambles away from {2}!", "You scramble away from {2}!", "{1}は{2}から逃れた！"),
    ("{1} locks {2}'s {3} with {4}!", "You lock {2}'s {3} with {4}!", "{1}は{4}で{2}の{3}を極めた！"),
    ("{1} bends {2}'s {3} with {4}!", "You bend {2}'s {3} with {4}!", "{1}は{4}で{2}の{3}をひねった！"),
    ("{1} strangles {2}'s {3} with {4}!", "You strangle {2}'s {3} with {4}!", "{1}は{4}で{2}の{3}を絞めた！"),
    ("{1} struggles in vain against the grip of {2}!", "You struggle in vain against the grip of {2}!", "{1}は{2}に組みつかれて抜け出せない！"),
    ("{1} struggles in vain against the grip of {2} on {3}.", "You struggle in vain against the grip of {2} on {3}.", "{1}は{3}をつかむ{2}を振りほどけない。"),
    ("{1} struggles in vain against the grip of {2} on {3}!", "You struggle in vain against the grip of {2} on {3}!", "{1}は{3}をつかむ{2}を振りほどけない！"),
    ("{1} is unable to break the grip of {2} on {3}!", "You are unable to break the grip of {2} on {3}!", "{1}は{3}をつかむ{2}を振りほどけない！"),
    ("{1} is unable to break the grip of {2} on {3}.", "You are unable to break the grip of {2} on {3}.", "{1}は{3}をつかむ{2}を振りほどけない。"),
    ("{1} breaks the grip of {2} from {3}!", "You break the grip of {2} from {3}!", "{1}は{3}をつかんでいた{2}を振りほどいた！"),
    ("{1} releases the grip of {2} from {3}!", "You release the grip of {2} from {3}!", "{1}は{3}をつかんでいた{2}を放した！"),
    ("{1}'s {2} takes the full force of the impact!", "Your {2} takes the full force of the impact!", "{1}の{2}が衝撃をまともに受けた！"),
    ("{1}'s {2} takes the full force of the impact, {3}!", "Your {2} takes the full force of the impact, {3}!", "{1}の{2}が衝撃をまともに受けた（{3}）！"),
    ("{1} retches.", "You retch.", "{1}はえずいた。"),
    ("{1} retches!", "You retch!", "{1}はえずいた！"),
    ("{1} struggles in vain against the grip of {2}'s {3}!", "You struggle in vain against the grip of {2}'s {3}!", "{1}は{2}の{3}に組みつかれて抜け出せない！"),
    ("{1} shakes {2} around by the {3}!", "You shake {2} around by the {3}!", "{1}は{2}の{3}をつかんで振り回した！"),
    ("{1} shakes {2} around by the {3}, {4}!", "You shake {2} around by the {3}, {4}!", "{1}は{2}の{3}をつかんで振り回した（{4}）！"),
    ("{1} throws {2} by the {3}!", "You throw {2} by the {3}!", "{1}は{2}の{3}をつかんで投げた！"),
    ("{1} releases the grip of {2}'s {3} on {4}'s {5}.", "You release the grip of {2}'s {3} on {4}'s {5}.", "{1}は{4}の{5}をつかんでいた{2}の{3}を放した。"),
    ("{1} breaks the grip of {2}'s {3} on {4}'s {5}.", "You break the grip of {2}'s {3} on {4}'s {5}.", "{1}は{4}の{5}をつかんでいた{2}の{3}を振りほどいた。"),
    ("{1}'s attack is interrupted!", "Your attack is interrupted!", "{1}の攻撃は中断された！"),
    ("{1} is struck down!", "You are struck down!", "{1}は打ち倒された！"),
]
OTHER = [
    ("A major artery in the {1} has been opened by the attack!", "{1}の大動脈が裂けた！"),
    ("An artery in the {1} has been opened by the attack!", "{1}の動脈が裂けた！"),
    ("A tendon in the {1} has been torn!", "{1}の腱が切れた！"),
    ("A ligament in the {1} has been torn!", "{1}の靭帯が切れた！"),
    ("A tendon in the {1} has been strained!", "{1}の腱を痛めた！"),
    ("A ligament in the {1} has been sprained!", "{1}の靭帯を捻挫した！"),
    ("A motor nerve in the {1} has been severed!", "{1}の運動神経が切れた！"),
    ("A sensory nerve in the {1} has been severed!", "{1}の感覚神経が切れた！"),
    ("Many nerves in the {1} have been severed!", "{1}の多くの神経が切れた！"),
    ("{1} has lodged firmly in the wound!", "{1}が傷口にしっかり刺さった！"),
    ("{1} is sucked out of the wound!", "{1}が傷口から吸い出された！"),
    ("{1} pours out of the wound!", "{1}が傷口から流れ出た！"),
    ("The force bends the {1}!", "衝撃で{1}が曲がった！"),
    ("The force bends the {1}, {2}!", "衝撃で{1}が曲がった（{2}）！"),
    ("The force pulls the {1}!", "衝撃で{1}が引っ張られた！"),
    ("The force pulls the {1}, {2}!", "衝撃で{1}が引っ張られた（{2}）！"),
    ("The force twists the {1}!", "衝撃で{1}がねじれた！"),
    ("The force twists the {1}, {2}!", "衝撃で{1}がねじれた（{2}）！"),
    ("A ligament has been torn and a tendon has been torn!", "靭帯と腱が切れた！"),
    ("A tendon has been torn and a ligament has been torn!", "腱と靭帯が切れた！"),
    ("A ligament has been sprained and a tendon has been strained!", "靭帯を捻挫し、腱を痛めた！"),
    ("A tendon has been strained and a ligament has been sprained!", "腱を痛め、靭帯を捻挫した！"),
    ("A major artery has been opened by the attack!", "大動脈が裂けた！"),
    ("An artery has been opened by the attack!", "動脈が裂けた！"),
    ("A tendon has been torn!", "腱が切れた！"),
    ("A ligament has been torn!", "靭帯が切れた！"),
    ("A tendon has been strained!", "腱を痛めた！"),
    ("A ligament has been sprained!", "靭帯を捻挫した！"),
    ("A motor nerve has been severed!", "運動神経が切れた！"),
    ("A sensory nerve has been severed!", "感覚神経が切れた！"),
    ("Many nerves have been severed!", "多くの神経が切れた！"),
    ("It is a gelding strike!", "去勢の一撃だ！"),
    ("It is a gelding blow!", "去勢の一撃だ！"),
]

# 靭帯・腱の傷が2つ並ぶ形（"A ligament in the left ankle has been torn and a tendon has been torn!"）
TISSUE = [("ligament", "靭帯"), ("tendon", "腱")]
TISSUE_HURT = [("torn", "が切れた"), ("bruised", "に打撲"), ("sprained", "を捻挫した"), ("strained", "を痛めた")]
for _a, _aj in TISSUE:
    for _h, _hj in TISSUE_HURT:
        OTHER.append((f"A {_a} has been {_h}!", f"{_aj}{_hj}！"))
        OTHER.append((f"A {_a} in the {{1}} has been {_h}!", f"{{1}}の{_aj}{_hj}！"))
        for _b, _bj in TISSUE:
            for _h2, _hj2 in TISSUE_HURT:
                OTHER.append((f"A {_a} has been {_h} and a {_b} has been {_h2}!", f"{_aj}{_hj}、{_bj}{_hj2}！"))
                OTHER.append((f"A {_a} in the {{1}} has been {_h} and a {_b} has been {_h2}!", f"{{1}}の{_aj}{_hj}、{_bj}{_hj2}！"))


def main():
    rows = []
    for en2, en3, ja in VERBS:
        for subj, who in ((f"{{1}} {en3}", "{1}は"), (f"You {en2}", "あなたは")):
            # 主語が You のときは相手 {2} 以降の番号はそのまま（{1} を使わないので、訳でも {1} を使わない）。
            # 文末の ! はエンジンが「！」にして付けるので、訳の末尾には付けない
            # 武器が体の部位の "first toe, right foot" の形（間に ", " が入る）は、手足の名前ごとに別に作る
            weapons = [("{4}", "{4}")] + [(f"{{4}}, {limb}", f"{{4}}（{lj}）") for limb, lj in LIMBS]
            if who == "あなたは":
                # "with your iron axe" の「あなたの」は主語と重なるので付けない
                weapons = [("your " + w, j) for w, j in weapons] + weapons
            for wen, wja in weapons:
                rows.append((f"{subj} {{2}} in the {{3}} with {wen}, {{5}}!", f"{who}{wja}で{{2}}の{{3}}{ja}（{{5}}）"))
                rows.append((f"{subj} {{2}} in the {{3}} with {wen}!", f"{who}{wja}で{{2}}の{{3}}{ja}"))
                for but, bj in BUTS:
                    rows.append((f"{subj} {{2}} in the {{3}} with {wen}, {but}!", f"{who}{wja}で{{2}}の{{3}}{ja}が、{bj}"))
            rows.append((f"{subj} {{2}} in the {{3}}, {{5}}!", f"{who}{{2}}の{{3}}{ja}（{{5}}）"))
            rows.append((f"{subj} {{2}} in the {{3}}!", f"{who}{{2}}の{{3}}{ja}"))
            for but, bj in BUTS:
                rows.append((f"{subj} {{2}} in the {{3}}, {but}!", f"{who}{{2}}の{{3}}{ja}が、{bj}"))
    # 傷が2つ並ぶ形（"tearing apart the muscle and bruising the bone"）。
    # 1つずつの形だけだと "tearing apart the {1}" が " and " の後ろまで飲み込んで語順が崩れるので、
    # 2つ並んだ形そのものを作っておく（こちらのほうが文字が長いので先に照合される）
    slot_effects = [(en, ja) for en, ja in EFFECTS if "{1}" in en and "{2}" not in en]
    def shift(text, start):
        """差し込みの番号を start からに振り直す（{1},{2} → {2},{3} のように重ならないよう2段で置く）"""
        for i in (2, 1):
            text = text.replace("{%d}" % i, "<%d>" % (i + start - 1))
        return text.replace("<", "{").replace(">", "}")

    # 防具越しの傷（"jamming the right true ribs through the heart"）が並ぶ形も作る
    jam_en, jam_ja = "jamming the {1} through the {2}", "{1}が{2}を貫く"
    for a_en, a_ja in slot_effects:
        rows.append((f"{a_en} and {shift(jam_en, 2)}", f"{a_ja}、{shift(jam_ja, 2)}"))
        rows.append((f"{jam_en} and {shift(a_en, 3)}", f"{jam_ja}、{shift(a_ja, 3)}"))
    for a_en, a_ja in slot_effects:
        # 同じ傷が2つ続くときは動詞を繰り返さない（"bruising the muscle and the bone"）
        suffix = a_ja.replace("{1}", "")
        rows.append((f"{a_en} and the {{2}}", f"{{1}}、{{2}}{suffix}"))
        for b_en, b_ja in slot_effects:
            rows.append((f"{a_en} and {b_en.replace('{1}', '{2}')}", f"{a_ja}、{b_ja.replace('{1}', '{2}')}"))
    for en, ja in EFFECTS:
        rows.append((en, ja))
        # 防具越しの傷（"bruising the skin through the (copper helm)"）。
        # "{1} through the {2}" のように差し込みで始まる形にすると、ふつうの文まで飲み込むので、傷ごとに作る
        if "{1}" in en and "{2}" not in en:
            rows.append((f"{en} through the ({{2}})", f"{{2}}越しに{ja}"))
            rows.append((f"{en} through the {{2}}", f"{{2}}越しに{ja}"))
    for en, you, ja in SIMPLE:
        rows.append((en, ja))
        rows.append((you, ja.replace("{1}", "あなた")))
    rows += OTHER
    out = ["# 戦闘の文テンプレート（tools/combat_templates.py が作る。直すときはスクリプトを直す）"]
    seen = set()
    for en, ja in rows:
        if en in seen:
            continue
        seen.add(en)
        # {9}（"but the attack is deflected by {9}"）は番号を詰める
        nums = sorted({int(x) for x in __import__("re").findall(r"\{(\d+)\}", en)})
        ren = {n: i + 1 for i, n in enumerate(nums)}
        fix = lambda s: __import__("re").sub(r"\{(\d+)\}", lambda m: "{%d}" % ren[int(m.group(1))], s)
        out.append(f"manual\tcore\t{fix(en)}\t{fix(ja)}")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(out) - 1} 件")


if __name__ == "__main__":
    main()
