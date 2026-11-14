"""実行ファイルから取り出した文の部品（paths.py の JSON）を、翻訳用のバッチに分ける。

入力: work/sentences/all_paths.json   {関数: {"prefix": [...], "core": [...], "suffix": [...]}}
出力: work/sentences/batches/NNN.json [{"group", "kind", "text", "slots"}...]
  text の {fXXXX} は {1} {2} … に番号を振り直し、slots に各番号の種類（呼び出し先）を入れる。

使い方: python tools/sentences/prepare.py [1バッチあたりの本体の数]
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / "work" / "sentences"
SLOT = re.compile(r"\{([^}]+)\}")
PER_BATCH = int(sys.argv[1]) if len(sys.argv) > 1 else 150

# 呼び出し先ごとの、差し込まれる語句の種類（分かっているものだけ）
SLOT_NAMES = {}
names_file = pathlib.Path(__file__).with_name("slot_names.tsv")
if names_file.exists():
    for line in names_file.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            k, v = line.split("\t")[:2]
            SLOT_NAMES[k] = v


def renumber(text):
    slots = []

    def sub(m):
        slots.append(SLOT_NAMES.get(m.group(1), m.group(1)))
        return "{" + str(len(slots)) + "}"

    return SLOT.sub(sub, text), slots


def useful(text, kind):
    lits = SLOT.sub("", text)
    if kind == "core":
        # 英単語が2つ以上あるもの（ラベル1語だけのものは単語辞書の担当）
        return len(re.findall(r"[A-Za-z]{2,}", lits)) >= 2
    return True


SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z{\"])")


COLOR = re.compile(r"\[C:\d+:\d+:\d+\]")
WORDTOK = re.compile(r"(\{[^}]+\}|\[[^\]]*\]|[A-Za-z]+(?:-[A-Za-z]+)*)")


def canon(text):
    """照合用の正規形: 色の変更 [C:a:b:c] はエンジンが任意の色として扱うので区別しない"""
    return COLOR.sub("[C]", text)


def collapse_words(pieces, min_variants=5):
    """1語だけ違う本体が多数あるとき（感情の語 × 同じ文など）、その語を差し込み {fWORD} にまとめる"""
    toks = [WORDTOK.split(canon(p)) for p in pieces]
    forms = {}
    for pi, ts in enumerate(toks):
        for i, t in enumerate(ts):
            if i % 2 == 1 and t[0].isalpha():
                key = tuple(ts[:i]) + ("{fWORD}",) + tuple(ts[i + 1:])
                forms.setdefault(key, {})[t.lower()] = pi
    chosen, used = [], set()
    for key, words in sorted(forms.items(), key=lambda kv: -len(kv[1])):
        if len(words) < min_variants:
            break
        idx = [pi for pi in words.values() if pi not in used]
        if len(idx) < min_variants:
            continue
        used.update(idx)
        chosen.append("".join(key))
    return [p for pi, p in enumerate(pieces) if pi not in used] + chosen


def split_sentences(t):
    """複数の文がつながった本体を文ごとに分ける（エンジンは文ごとに照合するため）"""
    return [p for p in SENT_SPLIT.split(t) if p.strip()]


def main():
    data = json.loads((WORK / "all_paths.json").read_text(encoding="utf-8"))
    units = []  # すべての (group, kind, text, slots)
    seen = set()
    for group, parts in data.items():
        # 文の境目をまたぐ部品は分ける: 書き出しは最後の文だけ、後ろの句は最初の文だけが他の部品とつながる。
        # 残りの文は独立した本体として扱う
        pieces_by_kind = {"prefix": [], "core": [], "suffix": []}
        for t in parts["core"]:
            pieces_by_kind["core"] += split_sentences(t)
        for t in parts["prefix"]:
            ps = split_sentences(t) or [t]
            pieces_by_kind["prefix"].append(ps[-1])
            pieces_by_kind["core"] += ps[:-1]
        for t in parts["suffix"]:
            ps = split_sentences(t) or [t]
            pieces_by_kind["suffix"].append(ps[0])
            pieces_by_kind["core"] += ps[1:]
        if not any(useful(p, "core") for p in pieces_by_kind["core"]):
            continue
        # 色の違いだけの重複を除き、1語違いの大量の変種をまとめる
        for kind in pieces_by_kind:
            dedup = {}
            for p in pieces_by_kind[kind]:
                dedup.setdefault(canon(p), p)
            pieces_by_kind[kind] = list(dedup.values())
        pieces_by_kind["core"] = collapse_words(pieces_by_kind["core"])
        for kind in ("prefix", "core", "suffix"):
            for piece in pieces_by_kind[kind]:
                if True:
                    if not useful(piece, kind):
                        continue
                    text, slots = renumber(piece)
                    key = (group, kind, text)
                    if key in seen:
                        continue
                    seen.add(key)
                    units.append({"group": group, "kind": kind, "text": text, "slots": slots})
    (WORK / "units.json").write_text(json.dumps(units, ensure_ascii=False, indent=0), encoding="utf-8")

    # 翻訳は (kind, 英語) ごとに1回（同じ部品が複数の関数に出てくるため）
    uniq, seen2 = [], set()
    for u in units:
        k = (u["kind"], canon(u["text"]))
        if k not in seen2:
            seen2.add(k)
            uniq.append(u)
    # 同じ関数の部品が同じバッチに入るよう、関数ごとにまとめてから切る
    batches, cur = [], []
    for u in uniq:
        cur.append(u)
        if len(cur) >= PER_BATCH:
            batches.append(cur)
            cur = []
    if cur:
        batches.append(cur)
    out = WORK / "batches"
    out.mkdir(parents=True, exist_ok=True)
    for p in out.glob("[0-9]*.json"):
        p.unlink()
    for i, b in enumerate(batches):
        (out / f"{i:03d}.json").write_text(json.dumps(b, ensure_ascii=False, indent=0), encoding="utf-8")
    kinds = {k: sum(1 for u in uniq if u["kind"] == k) for k in ("prefix", "core", "suffix")}
    print(f"部品 {len(units)} → 翻訳単位 {len(uniq)}（書き出し {kinds['prefix']} / 本体 {kinds['core']} / 後ろの句 {kinds['suffix']}）/ バッチ {len(batches)} 個")


if __name__ == "__main__":
    main()
