"""名簿に載っていない「中央寄せで描いている呼び出し元」をログから探す。

ゲームは英語の文字数（en）から描き始めの位置（x）を決めるので、
中央寄せの見出しは文字列が変わっても「枠の中心」が動かない。
中心の2倍は mid = x * 2 + en で表せるので、

- 中央寄せの呼び出し元: mid が一定（x は文字列ごとにばらつく）
- 左寄せの呼び出し元:   x が一定（mid がばらつく）

という違いで見分ける。MOD のエンジンは名簿に載っていない呼び出し元について
次の形の行をログに出す。

    [00:01:23.456] (1234) DEBUG  centerscan ^263a90 x=123 y=40 en=16 mid=262

判定の手順:
1. ログの centerscan 行を1行ずつ読み、(呼び出し元, y) ごとに (x, en) の組を集める
   （毎フレーム同じ文字が描かれるので、同じ組は1回だけ数える）
2. 呼び出し元ごとに en の種類が2種類以上あるものだけを判定の対象にする
3. 同じ y の中で en が2種類以上ある組だけを判定する（下の「y の扱い」を参照）
4. 組ごとに x のばらつき（x_spread）と mid のばらつき（mid_spread）を比べる
     - x_spread >= 2 かつ mid_spread <= max(1, x_spread * 0.25) → 中央寄せ
     - x_spread == 0 かつ mid_spread >= 2                       → 左寄せ
     - それ以外                                                 → 判定保留
   mid は中心の2倍なので、きちんと中央寄せならばらつきは丸めの1だけになる。
5. 呼び出し元の判定:
     - 中央寄せの組があり、左寄せの組が1つもない → 「中央寄せの疑い」
     - 中央寄せと左寄せの組が両方ある           → 「混在（要確認）」
     - 判定できる組がない                       → 「判定不能」
     - 左寄せの組しかない                       → 表示しない（件数だけ出す）
6. 名簿（data/no-translate-callers.txt）に載っている呼び出し元は除く

y の扱い:
同じ呼び出し元でも、行（y）が違えば別の画面の要素なので、混ぜて比べると
行の違いを中心のずれと取り違える。そのため既定では (呼び出し元, y) ごとに判定する。
`--ignore-y` を付けると y を無視して呼び出し元全体で判定する（比べ用）。

使い方:
    python -I -X utf8 tools/center_scan.py [ログのパス] [--ignore-y]
既定のログ: dfint-data/dfint-log.log
"""
import argparse
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LOG = ROOT.parent / "dfint-data" / "dfint-log.log"
NAMES = ROOT / "data" / "no-translate-callers.txt"

# centerscan の行。呼び出し元は ^ の後の16進数
LINE_RE = re.compile(
    r"centerscan\s+\^([0-9a-fA-F]+)\s+x=(-?\d+)\s+y=(-?\d+)\s+en=(-?\d+)\s+mid=(-?\d+)"
)


def load_names():
    """名簿に載っている呼び出し元（小文字の16進数）の集合を返す。

    行の形は「^263a90 center  # コメント」。# 以降はコメントとして捨てる。
    """
    found = set()
    if not NAMES.exists():
        return found
    for line in NAMES.read_text(encoding="utf-8", errors="replace").splitlines():
        body = line.split("#", 1)[0].strip()
        if not body.startswith("^"):
            continue
        words = body[1:].split()
        if words:
            found.add(words[0].lower())
    return found


def read_samples(path):
    """ログを1行ずつ読み、{(呼び出し元, y): {(x, en, mid), ...}} を返す。

    壊れた文字は errors="replace" で読み、centerscan 行以外は無視する。
    mid != 2*x+en の行は数が合わないので捨て、件数を返す。
    """
    groups = collections.defaultdict(set)
    total = 0
    broken = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if "centerscan" not in line:
                continue
            m = LINE_RE.search(line)
            if not m:
                continue
            total += 1
            caller = m.group(1).lower()
            x, y, en, mid = (int(m.group(i)) for i in (2, 3, 4, 5))
            if mid != 2 * x + en:
                broken += 1
                continue
            groups[(caller, y)].add((x, en, mid))
    return groups, total, broken


def spread(values):
    """値の最大と最小の差"""
    return max(values) - min(values)


def judge_group(samples):
    """1つの組（同じ呼び出し元・同じ y）を判定する。

    戻り値: (判定, x_spread, mid_spread, en_kinds, 件数)
    判定は "center" / "left" / "unknown"（判定保留）。
    """
    ens = {en for _, en, _ in samples}
    xs = [x for x, _, _ in samples]
    mids = [mid for _, _, mid in samples]
    x_sp = spread(xs)
    mid_sp = spread(mids)
    if len(ens) < 2:
        return "unknown", x_sp, mid_sp, len(ens), len(samples)
    if x_sp >= 2 and mid_sp <= max(1, x_sp * 0.25):
        verdict = "center"
    elif x_sp == 0 and mid_sp >= 2:
        verdict = "left"
    else:
        verdict = "unknown"
    return verdict, x_sp, mid_sp, len(ens), len(samples)


def judge_callers(groups, ignore_y):
    """呼び出し元ごとに判定する。

    ignore_y が True なら y を無視して呼び出し元全体で1つの組として扱う。
    戻り値: {呼び出し元: {"kind": ..., "groups": [...], "ens": 種類数, "samples": 件数}}
    """
    # 判定の単位（ラベル, 件の集合）を呼び出し元ごとに作る
    per_caller = collections.defaultdict(list)
    if ignore_y:
        merged = collections.defaultdict(set)
        for (caller, _y), samples in groups.items():
            merged[caller].update(samples)
        for caller, samples in merged.items():
            per_caller[caller].append(("全行", samples))
    else:
        for (caller, y), samples in groups.items():
            per_caller[caller].append((f"y={y}", samples))

    result = {}
    for caller, units in per_caller.items():
        # en の種類が2種類以上あるかは呼び出し元全体で見る（条件1）
        all_ens = set()
        all_samples = 0
        for _, s in units:
            all_ens.update(en for _, en, _ in s)
            all_samples += len(s)
        if len(all_ens) < 2:
            continue

        judged = []
        for label, s in units:
            verdict, x_sp, mid_sp, en_kinds, n = judge_group(s)
            if verdict == "unknown" and en_kinds < 2:
                # 同じ行の en が1種類だけなら判定の対象外（情報不足）
                continue
            judged.append((label, verdict, x_sp, mid_sp, en_kinds, n))

        result[caller] = {
            "ens": len(all_ens),
            "samples": all_samples,
            "groups": judged,
        }
    return result


def classify(info):
    """呼び出し元の判定を1語にまとめる。"""
    verdicts = {g[1] for g in info["groups"]}
    if not info["groups"] or verdicts == {"unknown"}:
        return "判定不能"
    if "center" in verdicts and "left" not in verdicts:
        return "中央寄せの疑い"
    if "center" in verdicts and "left" in verdicts:
        return "混在（要確認）"
    if verdicts == {"left"}:
        return "左寄せ"
    return "判定不能"


def describe_groups(info):
    """根拠を人が確かめられる形にする。"""
    parts = []
    for label, verdict, x_sp, mid_sp, en_kinds, n in info["groups"]:
        name = {"center": "中央", "left": "左", "unknown": "保留"}[verdict]
        parts.append(
            f"[{label}] {name}: en {en_kinds}通り, 件数{n}, "
            f"x の差{x_sp}, mid の差{mid_sp}"
        )
    return " / ".join(parts)


def main():
    ap = argparse.ArgumentParser(description="名簿にない中央寄せの呼び出し元を探す")
    ap.add_argument("log", nargs="?", default=str(DEFAULT_LOG), help="ログのパス")
    ap.add_argument("--ignore-y", action="store_true", help="y を無視して呼び出し元全体で判定する")
    args = ap.parse_args()

    path = pathlib.Path(args.log)
    if not path.exists():
        print(f"ログが見つからない: {path}", file=sys.stderr)
        return 1

    names = load_names()
    groups, total, broken = read_samples(path)
    results = judge_callers(groups, args.ignore_y)

    suspects, mixed, unknown, left_count, skipped_names = [], [], [], 0, []
    for caller, info in results.items():
        if caller in names:
            skipped_names.append(caller)
            continue
        kind = classify(info)
        row = (caller, kind, info)
        if kind == "中央寄せの疑い":
            suspects.append(row)
        elif kind == "混在（要確認）":
            mixed.append(row)
        elif kind == "判定不能":
            unknown.append(row)
        else:
            left_count += 1

    # 確からしさの高い順: en の種類が多い、件数が多い、mid の差が小さい
    def score(row):
        info = row[2]
        best_mid = min((g[3] for g in info["groups"] if g[1] == "center"), default=999)
        return (-info["ens"], -info["samples"], best_mid)

    suspects.sort(key=score)
    mixed.sort(key=score)

    print(f"ログ: {path}")
    print(f"centerscan 行: {total}件 （mid が 2*x+en と合わない行: {broken}件は除外）")
    print(f"判定方式: {'呼び出し元全体（y を無視）' if args.ignore_y else '呼び出し元 × y の行ごと'}")
    print(f"名簿に載っていて除外した呼び出し元: {len(skipped_names)}件")
    print(f"左寄せと判定した呼び出し元: {left_count}件（表示しない）")
    print()

    print("== 中央寄せの疑いあり（確からしい順）==")
    if not suspects:
        print("  （なし）")
    for caller, kind, info in suspects:
        print(
            f"  ^{caller}  en {info['ens']}通り / 件数{info['samples']}  "
            f"根拠: {describe_groups(info)}"
        )
    print()

    print("== 混在（要確認）: 同じ呼び出し元に中央と左の組がある ==")
    if not mixed:
        print("  （なし）")
    for caller, kind, info in mixed:
        print(
            f"  ^{caller}  en {info['ens']}通り / 件数{info['samples']}  "
            f"根拠: {describe_groups(info)}"
        )
    print()

    print("== 判定不能（en は2種類以上あるが、組の判定ができない）==")
    if not unknown:
        print("  （なし）")
    for caller, kind, info in unknown:
        print(
            f"  ^{caller}  en {info['ens']}通り / 件数{info['samples']}  "
            f"根拠: {describe_groups(info) or '同じ行で en が1種類だけ'}"
        )
    print()

    print("== 名簿にそのまま貼れる形（疑いのあるもの）==")
    if not suspects:
        print("  （なし）")
    for caller, kind, info in suspects:
        print(f"^{caller} center  # 候補 (en {info['ens']}通り)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
