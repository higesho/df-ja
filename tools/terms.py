"""raw の英語名を「翻訳が必要な基本語」と「規則で作れる派生語」に分ける共通処理。"""
import re

# 派生形の規則: (英語の正規表現, 日本語のテンプレート)。{0} に基本語の訳が入る
DERIVE_RULES = [
    (re.compile(r"^frozen (.+)$"), "凍った{0}"),
    (re.compile(r"^boiling (.+)$"), "沸騰した{0}"),
    (re.compile(r"^(.+) (?:man|men)$"), "{0}男"),
    (re.compile(r"^(.+) (?:woman|women)$"), "{0}女"),
    (re.compile(r"^giant (.+)$"), "巨大{0}"),
]


def singular_candidates(word):
    """英語の複数形らしき語から、単数形の候補を返す。"""
    c = []
    if word.endswith("ies"):
        c.append(word[:-3] + "y")
    if word.endswith("ves"):
        c += [word[:-3] + "f", word[:-3] + "fe"]
    if word.endswith("es"):
        c.append(word[:-2])
    if word.endswith("s"):
        c.append(word[:-1])
    if word.endswith("men"):
        c.append(word[:-3] + "man")
    if word.endswith("ice"):
        c.append(word[:-3] + "ouse")  # mice -> mouse
    if word.endswith("eese"):
        c.append(word[:-4] + "oose")
    if word.endswith("eeth"):
        c.append(word[:-4] + "ooth")
    if word.endswith("i"):
        c.append(word[:-1] + "us")
    if word.endswith("a"):
        c.append(word[:-1] + "um")
    if word.endswith("ae"):
        c.append(word[:-1])
    return c


def split_terms(terms):
    """terms: 英語名の集合。 (基本語の集合, {派生語: (基本語, テンプレート)}) を返す。"""
    terms = set(terms)
    derived = {}

    def base_of(t, depth=0):
        if depth > 4:
            return None
        for rx, tpl in DERIVE_RULES:
            m = rx.match(t)
            if m:
                inner = m.group(1)
                if inner in terms or base_of(inner, depth + 1):
                    return inner, tpl
        for s in singular_candidates(t):
            if s in terms and s != t:
                # 複数形の最後の単語だけが変化する（"battle axes" -> "battle axe"）
                return s, "{0}"
        # 複合語の最後の単語だけ複数形のケース
        if " " in t:
            head, last = t.rsplit(" ", 1)
            for s in singular_candidates(last):
                cand = f"{head} {s}"
                if cand in terms:
                    return cand, "{0}"
        return None

    for t in sorted(terms):
        b = base_of(t)
        if b:
            derived[t] = b
    base = terms - set(derived)
    return base, derived


def resolve(term, ja, derived, depth=0):
    """訳語辞書 ja と派生規則から term の訳を求める。見つからなければ None。"""
    if term in ja:
        return ja[term]
    if depth > 5 or term not in derived:
        return None
    inner, tpl = derived[term]
    inner_ja = resolve(inner, ja, derived, depth + 1)
    return tpl.format(inner_ja) if inner_ja is not None else None
