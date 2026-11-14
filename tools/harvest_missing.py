"""ゲームのログ（dfint-data/dfint-log.log）から、未翻訳のまま表示された文字列を集める。

LOG_LEVEL を Debug にしてしばらく遊んだあとに実行すると、
work/missing.tsv に「英語<TAB>（空欄）<TAB>出現回数」の形で書き出す。
訳を埋めた行を translations/harvested.tsv に追記し、tools/build.py → install.ps1 で反映する。
文章（単語ごとに折り返して描くテキスト）は work/missing-paragraphs.tsv に書き出す。
訳は translations/paragraphs.tsv に追記する。

使い方: python tools/harvest_missing.py [ログファイル]
"""
import collections
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LOG = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "dfint-data" / "dfint-log.log"
OUT = ROOT / "work" / "missing.tsv"

PATTERN = re.compile(r'missing translation for (\w+):\n[^\n]*:\n("(?:[^"\\]|\\.)*")')
PARA_PATTERN = re.compile(r'missing paragraph translation:\n("(?:[^"\\]|\\.)*")')
PARA_OUT = ROOT / "work" / "missing-paragraphs.tsv"


def done_paras():
    p = ROOT / "translations" / "paragraphs.tsv"
    if not p.exists():
        return set()
    return {line.split("\t", 1)[0] for line in p.read_text(encoding="utf-8").splitlines()}


def unescape(s):
    """Rust の {:?} 形式の文字列を元に戻す。"""
    body = s[1:-1]
    body = re.sub(r"\\u\{([0-9a-fA-F]+)\}", lambda m: chr(int(m.group(1), 16)), body)
    return (body.replace('\\"', '"').replace("\\'", "'").replace("\\n", "\n")
            .replace("\\t", "\t").replace("\\\\", "\\"))


def known():
    seen = set()
    for p in (ROOT / "translations").glob("*.tsv"):
        for line in p.read_text(encoding="utf-8").splitlines():
            seen.add(line.split("\t", 1)[0].lower())
    return seen


def main():
    text = LOG.read_text(encoding="utf-8", errors="replace")
    counts = collections.Counter()
    for func, raw in PATTERN.findall(text):
        s = unescape(raw)
        if "\n" in s or "\t" in s or not re.search(r"[A-Za-z]{2}", s):
            continue
        counts[s] += 1
    done = known()
    rows = [(s, n) for s, n in counts.most_common() if s.lower() not in done]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # 既存の missing.tsv に訳が書いてあれば消さない
    old = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")
            if len(p) >= 2 and p[1]:
                old[p[0]] = p[1]
    OUT.write_text("".join(f"{s}\t{old.get(s, '')}\t{n}\n" for s, n in rows), encoding="utf-8")
    print(f"未翻訳 {len(rows)} 種類（のべ {sum(counts.values())} 回）→ {OUT}")

    # 文章（単語ごとに折り返して描くテキスト）
    paras = []
    for raw in PARA_PATTERN.findall(text):
        s = unescape(raw)
        if s not in paras and s not in done_paras():
            paras.append(s)
    PARA_OUT.write_text("".join(f"{s}\t\n" for s in paras), encoding="utf-8")
    print(f"未翻訳の文章 {len(paras)} 件 → {PARA_OUT}"
          "（名前などが変わる部分は {1} {2} … に置き換えて translations/paragraphs.tsv に追記）")


if __name__ == "__main__":
    main()
