"""怪物の見た目の説明文の英語の部品を、Lua と raw から取り出す。

世界生成のとき Lua は「An enormous serpent composed of sandy loam. It has wings ...」のような
説明文を組み立てる（shared_info.lua の build_description）。この文を日本語にするには、
組み立てに使われる英語の部品（大きさ・形容・体の名前・様子・素材・色など）を一覧にしておく必要がある。
このスクリプトは、その部品を Lua のテキストとして正規表現で読み出し、分類つきの表にする。

Lua は実行しない。行を読んで、ブロック（tweaks={ ... } や function ... end など）の範囲を
字下げで見分け、その範囲の中の文字列リテラルを拾う。訳はしない。
空白は勝手に削らない（" long, curving" のように先頭に空白がある語は、そのまま出す）。
重複は残す（同じ語が複数の箇所で使われていれば、その分だけ行が出る）。

掛け合わせについて:
  角（horn）と尾（tail）は「数 × 形 × 名詞」を、Lua 側で文字列を連結して作っている。
  そこで数（horn_count / tail_count）、形（horn_shape / tail_shape）、名詞（horn_noun / tail_noun）を
  別々の分類で出し、掛け合わせはしない。

分類:
  size          大きさ（build_description）
  adj           形容（tweaks の adj=）
  body          体の名前（name_string=。rcp.lua と creatures.lua）
  form          「in humanoid form」など（form_desc= / twisted_desc=）
  with          「with lidless eyes」など（with_desc=）
  material      固定の素材（post_mat_adj="composed of X" の X）
  feature       「It has 〜」の中身と翼の語
  horn_count    角の数（a / two / three / four）
  horn_shape    角の形（HORN=... の return）
  horn_noun     角の名詞（horn / horns）
  tail_count    尾の数（a / two / three）
  tail_shape    尾の形（pick_random の一覧）
  tail_noun     尾の名詞（tail / tails）
  manner        様子（default/good/evil の desc_adds、creatures.lua の add= と return）
  beware        「Beware its 〜!」の中身
  color         色の名前（descriptor_color_standard.txt の [NAME:...]）
  texture       質感（color_desc の一覧）
  closing       種類ごとの締めの文（end_phrase=）
  closing_frag  締めの文を組み立てる断片（add_desc / end_str の文字列）
  eadj          名前の後ろにつく句（potential_end_phrase / night_troll_end_phrases）

使い方: python -I -X utf8 tools/beast_desc_extract.py
出力: work/beast_parts.tsv（1行目は見出し「# 分類<TAB>英語<TAB>出どころ」。以後はタブ区切り3列）
"""
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
GAME = ROOT.parent
GEN = GAME / "data" / "vanilla" / "vanilla_procedural" / "scripts" / "generators"
SHARED = GEN / "creatures" / "shared_info.lua"
CREATURES = GEN / "creatures.lua"
RCP = GEN / "creatures" / "rcp.lua"
COLOR = GAME / "data" / "vanilla" / "vanilla_descriptors" / "objects" / "descriptor_color_standard.txt"
OUT = ROOT / "work" / "beast_parts.tsv"

# Lua の "..." リテラル（エスケープは使われていない前提で、そのまま拾う）
LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')
# 1行に文字列だけが並んでいる形（pick_random の一覧の中など）
STANDALONE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)",?\s*$')

CATEGORY_ORDER = [
    "size", "adj", "body", "form", "with", "material", "feature",
    "horn_count", "horn_shape", "horn_noun", "tail_count", "tail_shape", "tail_noun",
    "manner", "beware", "color", "texture", "closing", "closing_frag", "eadj",
]

rows = []  # (分類, 英語, 出どころ)


class Src:
    """ファイル1つ分の行。出どころは「ファイル名:行番号」で示す。"""

    def __init__(self, path):
        self.name = path.name
        self.lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    def where(self, k):
        return f"{self.name}:{k + 1}"

    def is_comment(self, k):
        return self.lines[k].lstrip().startswith("--")


def lits(text):
    """行の中の "..." を、中身のまま（空白も含め）全部返す。"""
    return [m.group(1) for m in LIT.finditer(text)]


def add(cat, text, src, k):
    rows.append((cat, text, src.where(k)))


def find_line(src, pattern, start=0):
    rx = re.compile(pattern)
    for k in range(start, len(src.lines)):
        if rx.search(src.lines[k]):
            return k
    raise SystemExit(f"見つからない: {pattern} ({src.name})")


def block(src, pattern):
    """pattern の行から、同じ字下げの閉じ（} または end）の行までの範囲 (開始, 終了) を返す。"""
    i = find_line(src, pattern)
    indent = len(src.lines[i]) - len(src.lines[i].lstrip())
    close = re.compile(r"^" + " " * indent + r"(\}|end)(?![A-Za-z_])")
    for j in range(i + 1, len(src.lines)):
        if close.match(src.lines[j]):
            return i, j
    raise SystemExit(f"閉じが見つからない: {pattern} ({src.name})")


def scan(src, cat, rx, group=1, start=0, end=None, skip=None):
    """範囲の中で rx に合う行から、group の文字列を拾う。"""
    end = len(src.lines) if end is None else end
    for k in range(start, end):
        if skip and skip(src, k):
            continue
        m = re.search(rx, src.lines[k])
        if m:
            add(cat, m.group(group), src, k)


def main():
    sh = Src(SHARED)
    cr = Src(CREATURES)
    rcp = Src(RCP)
    colfile = Src(COLOR)

    # --- size: build_description の「大きさ」の部分（"Adjective done" の行まで）---
    b_start, _ = (find_line(sh, r"^function build_description\("), None)
    b_end = find_line(sh, r'l2\("Adjective done"\)', b_start)
    for k in range(b_start, b_end + 1):
        line = sh.lines[k]
        if "desc=desc" in line and "l2(" not in line:
            for s in lits(line):
                if s.strip() and not s.startswith("["):
                    add("size", s, sh, k)

    # --- adj: 形容（tweaks の adj=） ---
    scan(sh, "adj", r'\badj="([^"]*)"')

    # --- body: 体の名前（rcp.lua と creatures.lua の name_string=） ---
    scan(rcp, "body", r'\bname_string="([^"]*)"')
    scan(cr, "body", r'\bname_string="([^"]*)"')

    # --- form / with / material（shared_info の固定の句） ---
    scan(sh, "form", r'\b(?:form_desc|twisted_desc)="([^"]*)"')
    scan(sh, "with", r'\bwith_desc="([^"]*)"')
    scan(sh, "material", r'post_mat_adj="composed of ([^"]+)"')

    # --- tweaks の表（feature / 角 / 尾 / texture） ---
    t_start, t_end = block(sh, r"^tweaks=\{")
    # feature: 「It has 〜」の中身（末尾が空白の「It has a 」「It has two 」は数の部品なので除く）と翼の語
    for k in range(t_start, t_end + 1):
        for s in lits(sh.lines[k]):
            m = re.match(r"^\s?It has (.+)$", s)
            if m and m.group(1).strip() and not m.group(1).endswith(" "):
                add("feature", m.group(1), sh, k)
            elif "wings" in s:
                add("feature", s, sh, k)

    # horn: HEAD_HORNS の中の数・形・名詞
    h_start, h_end = block(sh, r"^    HEAD_HORNS=\{")
    scan(sh, "horn_count", r'str=str\.\."((?:two|three|four|a) )"', start=h_start, end=h_end + 1)
    scan(sh, "horn_shape", r'HORN="[A-Z_]+" return "([^"]*)"', start=h_start, end=h_end + 1)
    scan(sh, "horn_noun", r'str=str\.\."( horns?)"', start=h_start, end=h_end + 1)

    # tail: TAIL の中の数・形・名詞
    a_start, a_end = block(sh, r"^    TAIL=\{")
    scan(sh, "tail_count", r'It has ((?:two|three|a) )"', start=a_start, end=a_end + 1)
    scan(sh, "tail_noun", r'str=str\.\."( tails?)"', start=a_start, end=a_end + 1)
    for k in range(a_start, a_end + 1):
        m = STANDALONE.match(sh.lines[k])
        if m:
            add("tail_shape", m.group(1), sh, k)

    # texture: 「. Its 〜 is 」の後の pick_random の一覧（毛・羽・鱗・皮膚・外骨格）
    # 「. Its ...」の行の後の pick_random({ ... }) の一覧。鱗は2つの一覧が「}).. and ..pick_random({」でつながる
    state = 0
    for k in range(t_start, t_end + 1):
        line = sh.lines[k]
        if '". Its "' in line:
            state = 1
        if state and "pick_random({" in line:
            state = 2
            continue
        if state == 2:
            m = STANDALONE.match(line)
            if m:
                add("texture", m.group(1), sh, k)
            if re.match(r"^\s*\}\)", line):
                state = 0

    # --- manner: shared_info の default / good / evil の説明の追加（pref_str と lines[ は除く） ---
    def not_manner_code(src, k):
        line = src.lines[k]
        return ("pref_str" in line or "lines[" in line or "odor" in line
                or src.is_comment(k))

    for name in ("default_desc_adds", "good_desc_adds", "evil_desc_adds"):
        m_start, m_end = block(sh, rf"^{name}=\{{")
        for k in range(m_start, m_end + 1):
            if not_manner_code(sh, k):
                continue
            for s in lits(sh.lines[k]):
                if s[:1].islower():
                    add("manner", s, sh, k)

    # --- beware: attack_tweaks の「Beware its 〜!」 ---
    w_start, w_end = block(sh, r"^attack_tweaks=\{")
    scan(sh, "beware", r'"Beware its ([^"]*)!"', start=w_start, end=w_end + 1)

    # --- color: 色の名前 ---
    for k, line in enumerate(colfile.lines):
        for m in re.finditer(r"\[NAME:([^\]]+)\]", line):
            add("color", m.group(1), colfile, k)

    # --- creatures.lua: 様子（add=、return "it ..." / "with ..."）、締めの文、断片 ---
    scan(cr, "manner", r'\badd="([^"]*)"')
    scan(cr, "manner", r'return "((?:it|with) [^"]*)"')
    scan(cr, "closing", r'\bend_phrase="([^"]*)"')
    for k, line in enumerate(cr.lines):
        if cr.is_comment(k):
            continue
        if "add_desc(" in line or "end_str=" in line:
            for s in lits(line):
                if s.strip():
                    add("closing_frag", s, cr, k)

    # --- eadj: 名前の後ろにつく句 ---
    scan(sh, "eadj", r'potential_end_phrase\[#options\.potential_end_phrase\+1\]="([^"]*)"')
    n_start = find_line(cr, r"night_troll_end_phrases=night_troll_end_phrases or \{")
    for k in range(n_start + 1, len(cr.lines)):
        m = STANDALONE.match(cr.lines[k])
        if m:
            add("eadj", m.group(1), cr, k)
        if "}" in cr.lines[k]:
            break

    # --- 書き出し ---
    for s_name, text, _ in rows:
        if "\t" in text or "\n" in text:
            raise SystemExit(f"タブ・改行を含む語: {text!r}")

    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    rows.sort(key=lambda r: order[r[0]])  # 同じ分類の中は拾った順（ファイル順）のまま

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# 分類\t英語\t出どころ（ファイル名:行番号）\n")
        for cat, text, where in rows:
            f.write(f"{cat}\t{text}\t{where}\n")

    # --- 件数の報告（標準出力） ---
    counts = Counter(cat for cat, _, _ in rows)
    for cat in CATEGORY_ORDER:
        dup = counts[cat] - len({t for c, t, _ in rows if c == cat})
        print(f"{cat:13s} {counts[cat]:4d}  (重複 {dup})")
    print(f"合計 {len(rows)} 行 -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
