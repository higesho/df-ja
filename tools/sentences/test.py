"""文テンプレートの照合をエンジン（src/sentence.rs）と同じ手順で再現し、英文を訳してみる。ゲームを起動せずに確かめる用。

使い方: python tools/sentences/test.py "In 125, Urist struck down Bomrek in Site."
        python tools/sentences/test.py -f 英文を1行ずつ書いたファイル
"""
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SLOT = re.compile(r"\{(\d+)\}")
COLOR = re.compile(r"\[C:\d+:\d+:\d+\]")
TOKEN = re.compile(r"\{\d+\}|\[C:\d+:\d+:\d+\]")


def strip_end(s):
    t = s.rstrip()
    if t.endswith("..."):
        return t[:-3], "…"
    for en, ja in ((".", "。"), ("!", "！"), ("?", "？")):
        if t.endswith(en):
            return t[:-1], ja
    return t, ""


# エンジンの SLOT_PATTERN と同じ（リンクを1かたまりとして扱う）
SLOT_PATTERN = r"((?:\[LPAGE:[^\]]*\][^\[]*\[/LPAGE\]|\[[^L/\]][^\]]*\]|[^\[])+?)"


def pattern(src):
    out, last = "", 0
    for m in TOKEN.finditer(src):
        out += re.escape(src[last:m.start()]) + (SLOT_PATTERN if m.group().startswith("{") else r"(\[C:\d+:\d+:\d+\])")
        last = m.end()
    return out + re.escape(src[last:])


def keyword(src):
    parts = [p for p in TOKEN.split(src) if len(p.strip()) >= 3 and re.search(r"[A-Za-z]", p)]
    return max(parts, key=len) if parts else None


def alpha_count(s):
    return len(re.findall(r"[A-Za-z]", re.sub(r"\[[^\]]*\]", "", s)))


def word_count(s):
    return len([w for w in re.split(r"[^A-Za-z]+", TOKEN.sub(" ", s)) if len(w) >= 2])


STOP = {"the", "and", "was", "were", "are", "his", "her", "its", "for", "with", "from", "into", "this", "that", "has", "had", "have",
        "not", "but", "who", "him", "she", "they", "them", "their", "then", "than", "there", "one", "all", "some"}


def enough_literal(srcs, body):
    lit = " ".join(TOKEN.sub(" ", x) for x in srcs)
    content = any(len(w) >= 3 and w.lower() not in STOP for w in re.split(r"[^A-Za-z]+", lit))
    return content and (word_count(lit) >= 2 or alpha_count(lit) * 10 >= alpha_count(body) * 3)


def on_word_boundary(body, a, b):
    w = lambda c: bool(c) and c.isascii() and c.isalnum()
    before = body[a - 1] if a > 0 else ""
    after = body[b] if b < len(body) else ""
    first = body[a] if b > a else ""
    last = body[b - 1] if b > a else ""
    return not (w(before) and w(first)) and not (w(last) and w(after))


SEASONS = {"early spring": "初春", "midspring": "仲春", "late spring": "晩春", "early summer": "初夏", "midsummer": "仲夏",
           "late summer": "晩夏", "early autumn": "初秋", "midautumn": "仲秋", "late autumn": "晩秋", "early winter": "初冬",
           "midwinter": "仲冬", "late winter": "晩冬"}


def split_season(s):
    m = re.match(r"In the (" + "|".join(SEASONS) + r") of (\d+), ", s)
    if not m:
        return None
    return "In %s, " % m.group(2) + s[m.end():], m.group(2), SEASONS[m.group(1)]


class Engine:
    def __init__(self):
        self.groups, self.cores = {}, []
        with (DATA / "sentence-templates.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                g = self.groups.setdefault(r["group"], {"prefix": [], "suffix": []})
                # 書き出しは後ろの空白も照合に使うので削らない（エンジンと同じ）
                text = r["text"] if r["kind"] == "prefix" else strip_end(r["text"])[0]
                ja = r["translation"].rstrip().rstrip("。！？")
                if r["kind"] in ("prefix", "suffix"):
                    g[r["kind"]].append((text, ja))
                else:
                    kw = keyword(text)
                    if kw:
                        self.cores.append((r["group"], text, kw, ja))
        for g in self.groups.values():
            for k in ("prefix", "suffix"):
                g[k].sort(key=lambda p: -len(SLOT.sub("", p[0])))
        self.cache = {}
        self.words = {}
        with (DATA / "simple-dictionary.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                self.words[r["text"].lower()] = r["translation"]

    def value(self, v, depth):
        t = v.strip()
        if not t:
            return v
        m0 = re.fullmatch(r"(?:the|a|an) (\[LPAGE:[^\]]*\][^\[]*\[/LPAGE\])", t)
        if m0:
            return self.value(m0.group(1), depth)
        m = re.fullmatch(r"(\[LPAGE:[^\]]*\])(.*)\[/LPAGE\]", t, re.S)
        if m and "[LPAGE" not in m.group(2):
            return m.group(1) + self.value(m.group(2), depth) + "[/LPAGE]"
        if t.lower() in self.words:
            return self.words[t.lower()]
        for art in ("the ", "The ", "a ", "an ", "A ", "An "):
            if t.startswith(art) and t[len(art):].lower() in self.words:
                return self.words[t[len(art):].lower()]
        if depth < 3 and (", " in t or " and " in t):
            ja = self.value_list(t, depth)
            if ja:
                return ja
        if depth < 3:
            ja = self.one(t, depth + 1, False)
            if ja and not (re.search("[。！？]", ja) and not re.search(r"[.!?]", t)):
                return ja
        bare = re.sub(r"^(a|an|the|A|An|The) ", "", t)
        ws = bare.split(" ")
        for k in range(len(ws) - 1, 0, -1):
            if (ws[k][:1].isupper() or (ws[k][:1] and not ws[k][:1].isascii())) and all(w[:1].islower() and w[:1].isascii() for w in ws[:k]):
                kind = self.creature_kind(" ".join(ws[:k]))
                if kind:
                    return kind + "の" + " ".join(ws[k:])
        if all(w[:1].isupper() or (w[:1] and not w[:1].isascii()) for w in ws):
            mn = 1 if t.startswith("the ") else 2
            for k in range(min(2, len(ws) - mn), 0, -1):
                key = " ".join(ws[:k]).lower()
                if key in self.words and not self.words[key].isascii():
                    return self.words[key] + "の" + " ".join(ws[k:])
        for art in ("a ", "an ", "the ", "some ", "The ", "A ", "An "):
            if t.startswith(art) and t[len(art):].lower() in self.words:
                return self.words[t[len(art):].lower()]
        if "'s " in t and depth < 3:
            q = t.rfind("'s ")
            owner, thing = t[:q], t[q + 3:]
            oj, tj = self.value(owner, depth + 1), self.value(thing, depth + 1)
            if oj != owner and tj != thing:
                return oj + "の" + tj
        for pos, pre in (("his ", ""), ("her ", ""), ("its ", ""), ("their ", ""), ("your ", "あなたの")):
            if t.startswith(pos) and depth < 3:
                rest = t[len(pos):]
                ja = self.value(rest, depth + 1)
                if ja != rest:
                    return pre + ja
        ja = self.compose_words(t)
        return ja if ja else t

    DEGREES = {"very": "とても", "quite": "かなり", "somewhat": "やや", "slightly": "わずかに", "extremely": "非常に",
               "incredibly": "信じられないほど", "extraordinarily": "並外れて", "nearly": "ほとんど", "sharply": "鋭く",
               "deeply": "深く", "a little": "少し", "fairly": "わりと"}

    def compose_words(self, t):
        """エンジンの compose_words と同じ"""
        if " " not in t or not re.fullmatch(r"[a-z' \-]+", t):
            return None
        ws = [w for w in t.split(" ") if w]
        if len(ws) < 2 or len(ws) > 8:
            return None
        noun = lambda c: "゠" <= c <= "ヿ" or "一" <= c <= "鿿"
        out, i = "", 0
        while i < len(ws):
            hit = None
            for j in range(len(ws), i, -1):
                if i == 0 and j == len(ws):
                    continue
                ph = " ".join(ws[i:j])
                ja = self.words.get(ph) or self.DEGREES.get(ph)
                if ja:
                    hit = (j, ja); break
            if not hit:
                return None
            j, ja = hit
            if out and noun(out[-1]) and not out.endswith("的") and noun(ja[0]):
                out += "の"
            out += ja; i = j
        return out

    KINDS = [(" fiend", "の悪鬼"), (" demon", "の悪魔"), (" devil", "の魔物"), (" spirit", "の霊"), (" monster", "の怪物"),
             (" brute", "の獣鬼"), (" creature", "の生き物"), (" titan", "のタイタン")]

    def creature_kind(self, s):
        """エンジンの creature_kind と同じ"""
        if s.lower() in self.words:
            return self.words[s.lower()]
        for en, ja in self.KINDS:
            if s.endswith(en) and s[: -len(en)].lower() in self.words:
                return self.words[s[: -len(en)].lower()] + ja
            if s.endswith(en):
                c = self.compose_words(s[: -len(en)])
                if c:
                    return c + ja
        return None

    def value_list(self, t, depth):
        """エンジンの value_list と同じ: ", " で分け、訳せない項目は " and " の位置で分けてみる"""
        if any(x.count("[LPAGE") != x.count("[/LPAGE]") for x in t.split(", ")):
            return None
        name_like = lambda s: re.sub(r"\[[^\]]*\]", "", s).strip()[:1].isupper()
        raw = [x.strip() for x in t.split(", ") if x.strip()]
        if len(raw) < 2 and " and " not in t:
            return None
        # エンジンと同じ: ", " を含む句は辞書にある最も長いつながりを1項目にする
        pieces, i = [], 0
        while i < len(raw):
            j = len(raw)
            while j > i + 1:
                key = ", ".join(raw[i:j])
                key = key[4:] if key.startswith("and ") else key
                if key.lower() in self.words or any(key[:m.start()].lower() in self.words for m in re.finditer(" and ", key)):
                    break
                j -= 1
            pieces.append(", ".join(raw[i:j])); i = j
        out, anyt = [], False
        for piece in pieces:
            piece = piece[4:] if piece.startswith("and ") else piece
            if piece.lower() in self.words:
                anyt = True; out.append(self.words[piece.lower()]); continue
            split = None
            for m in reversed(list(re.finditer(" and ", piece))):
                l, r = piece[:m.start()], piece[m.end():]
                lj, rj = self.value(l, depth + 1), self.value(r, depth + 1)
                if lj != l and rj != r:
                    split = [lj, rj]; break
            if split:
                anyt = True; out += split; continue
            ja = self.value(piece, depth + 1)
            if ja != piece:
                anyt = True; out.append(ja); continue
            done = False
            for m in reversed(list(re.finditer(" and ", piece))):
                l, r = piece[:m.start()], piece[m.end():]
                lj, rj = self.value(l, depth + 1), self.value(r, depth + 1)
                if (lj != l or name_like(l)) and (rj != r or name_like(r)) and (lj != l or rj != r):
                    anyt = True; out += [lj, rj]; done = True; break
            if not done:
                if not name_like(piece):
                    return None
                out.append(piece)
        return "、".join(out) if anyt and len(out) >= 2 else None

    def render(self, src, ja, caps, depth):
        kinds = [t.startswith("{") for t in TOKEN.findall(src)]
        vals = [self.value(v, depth) for v, k in zip(caps, kinds) if k]
        colors = iter([v for v, k in zip(caps, kinds) if not k])
        out = self.fill(ja, vals)
        return COLOR.sub(lambda m: next(colors, m.group()), out)

    @staticmethod
    def fill(ja, vals):
        return SLOT.sub(lambda c: vals[int(c.group(1)) - 1] if int(c.group(1)) <= len(vals) else "", ja)

    def one(self, sentence, depth=0, punct=True):
        body, end = strip_end(sentence) if punct else (sentence, "")
        cands = sorted({i for i, c in enumerate(self.cores) if c[2] in body}, key=lambda i: (self.cores[i][1].startswith("{") or any(p[0].startswith("{") for p in self.groups[self.cores[i][0]]["prefix"]), -len(SLOT.sub("", self.cores[i][1])), self.cores[i][0] != "manual"))
        for i in cands:
            group, text, kw, ja = self.cores[i]
            if "}{" in text:
                continue
            g = self.groups[group]
            for pre in g["prefix"] + [None]:
                for suf in g["suffix"] + [None]:
                    if (pre and pre[0].rstrip().endswith("}") and text.lstrip().startswith("{")) or \
                       (suf and text.rstrip().endswith("}") and suf[0].lstrip().startswith("{")):
                        continue
                    if (pre and "}{" in pre[0]) or (suf and "}{" in suf[0]):
                        continue
                    if group != "manual" and not enough_literal([x for x in (pre and pre[0], text, suf and suf[0]) if x], body):
                        continue
                    key = (i, pre and pre[0], suf and suf[0])
                    rx = self.cache.get(key)
                    if rx is None:
                        rx = self.cache[key] = re.compile(
                            "^" + (pattern(pre[0]) if pre else "") + pattern(text) + (pattern(suf[0]) if suf else "") + "$", re.S)
                    m = rx.match(body)
                    if not m:
                        continue
                    if any(not on_word_boundary(body, m.start(g), m.end(g)) or m.group(g).count("[LPAGE") != m.group(g).count("[/LPAGE]")
                           for g in range(1, len(m.groups()) + 1) if m.start(g) >= 0):
                        continue
                    caps = list(m.groups())
                    np_ = len(TOKEN.findall(pre[0])) if pre else 0
                    nc = len(TOKEN.findall(text))
                    pre_ja = self.render(pre[0], pre[1], caps[:np_], depth) if pre else ""
                    suf_ja = self.render(suf[0], suf[1], caps[np_ + nc:], depth) if suf else ""
                    main = self.render(text, ja, caps[np_:np_ + nc], depth)
                    main = main.replace("{REST}", suf_ja) if "{REST}" in main else main + suf_ja
                    if end:
                        main = main.rstrip().rstrip("。！？")
                    return pre_ja + main + end
        return None


    def text(self, t):
        """エンジンの translate_text と同じく、トークンで区切って文ごとに訳す。1文でも訳せたら結果を返す"""
        if " and the injured part " in t or " and the severed part " in t:
            return self.text(t.replace(" and the injured part ", ", the injured part ").replace(" and the severed part ", ", the severed part "))
        for en, ja in ((" from behind", "背後から"), (" from the side", "横から")):
            if " in the " in t and en in t:
                out = self.text(t.replace(en, "", 1))
                if not out:
                    return None
                p = out.find("は")
                return out[:p + 1] + ja + out[p + 1:] if p >= 0 else ja + out
        if ": " in t:
            who, line = t.split(": ", 1)
            line = line.strip()
            m = re.fullmatch(r"(.*) \(to (.*)\)", who)
            speaker, to = (m.group(1), m.group(2)) if m else (who, None)
            # 仕事の取り消しは会話ではないので話し手として扱わない（engine/src/sentence.rs と同じ）
            ok = lambda x: x and len(x) <= 60 and not re.search(r"[.!?\[(]", x) and len(x.split(" ")) <= 6 and " cancels " not in x
            if ok(speaker) and (to is None or ok(to)) and line and " " in line:
                lj = self.text(line) or self.words.get(line.lower())
                if lj:
                    person = lambda x: "あなた" if x in ("You", "you") else self.value(x, 0)
                    wj = person(speaker) + ("（" + person(to) + "へ）" if to else "")
                    return wj + "「" + lj.strip().rstrip("。") + "」"
        u = t.strip()
        if len(u) > 2 and u[0] == '"' and u[-1] == '"' and '"' not in u[1:-1]:
            ja = self.text(u[1:-1])
            return ja and "「" + ja.strip() + "」"
        out, any_ = "", False
        for piece in re.split(r"(\[(?:B|P|R|/?CHAR[^\]]*)\])", t):
            if piece.startswith("[") and piece.endswith("]"):
                out += piece
                continue
            # エンジンと同じく "etc." の後ろでは文を区切らない
            for m in [M(x.replace(chr(1), ".")) for x in re.findall(r'[^.!?]+(?:[.!?]+"?|$)\s*', re.sub(r"etc\. ([a-z])", lambda g: "etc" + chr(1) + " " + g.group(1), piece))]:
                ss = split_season(m.group().strip())
                if ss:
                    ja = self.one(ss[0])
                    ja = ja and ja.replace(ss[1] + "年、", ss[1] + "年の" + ss[2] + "、", 1)
                else:
                    ja = self.one(m.group().strip())
                ja = ja or self.words.get(m.group().strip().lower())
                if ja:
                    out += ja
                    any_ = True
                else:
                    out += m.group()
        return out.replace("の〔述〕", "だ").replace("な〔述〕", "だ").replace("〔述〕", "") if any_ else None


class M:
    """re.Match の代わり（group() だけ使う）"""
    def __init__(self, t):
        self.t = t

    def group(self):
        return self.t


def main():
    e = Engine()
    lines = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if sys.argv[1:2] == ["-f"] else sys.argv[1:]
    ok = 0
    for s in lines:
        ja = e.text(s)
        ok += ja is not None
        print(f"{s}\n  → {ja or '（訳せない）'}")
    print(f"{ok}/{len(lines)} 件を訳せた")


if __name__ == "__main__":
    main()
