"""文章を組み立てる関数の分岐をたどり、出来上がる英文のテンプレートを列挙する。

出力先の std::string（関数ごとに1つのレジスタ）に「文字列定数を追加」「別の関数で何かを追加」する操作を、
実行順に並べたものを1つのテンプレートとする。別の関数が追加する部分は {fXXXX}（呼び出し先の RVA）になる。

使い方: python paths.py <exe> <func_rva> [...]        テンプレートを表示
        python paths.py <exe> --json out.json <rva...>  JSON で保存
"""
import sys, re, json, bisect, collections, pefile, capstone
from capstone import x86

exe = sys.argv[1]
args = sys.argv[2:]
out_json = None
if args and args[0] == "--json":
    out_json, args = args[1], args[2:]

pe = pefile.PE(exe, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
starts = [f[0] for f in funcs]
img = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

# std::string の追加・構築・代入関数（バージョンごとに tools/re/version.json に書く）
_ver = json.load(open(__import__("pathlib").Path(__file__).with_name("version.json"), encoding="utf-8"))["string_ops"]
ADD_OPS = {int(x, 16) for x in _ver["append"]}
STR_OPS = ADD_OPS | {int(_ver["new"], 16), int(_ver["set"], 16)}
VOLATILE = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}
R64 = {}
for r in ["ax", "bx", "cx", "dx", "si", "di", "bp", "sp"]:
    R64["r" + r] = "r" + r; R64["e" + r] = "r" + r
for i in range(8, 16):
    R64[f"r{i}"] = f"r{i}"; R64[f"r{i}d"] = f"r{i}"
import os, time
# 上限は環境変数で変えられる（DFJA_MAX_PATHS など）
MAX_PATHS = int(os.environ.get("DFJA_MAX_PATHS", 400))
MAX_OPS = int(os.environ.get("DFJA_MAX_OPS", 40))
TIME_LIMIT = float(os.environ.get("DFJA_TIME_LIMIT", 40))  # 1関数あたりの秒数
MAX_OUTS = 6     # 1関数で調べる出力先の数


def func_range(rva):
    j = bisect.bisect_right(starts, rva) - 1
    while j >= 0 and not (funcs[j][0] <= rva < funcs[j][1]):
        j -= 1
    return funcs[j]


def cstr(tgt):
    if not (0 <= tgt < len(img)):
        return None
    s = img[tgt:tgt + 600].split(b"\0")[0]
    if s and all(32 <= c < 127 for c in s):
        return s.decode()
    return None


def rip_target(ins):
    m = re.search(r"\[rip \+ (0x[0-9a-f]+)\]", ins.op_str)
    return ins.address + ins.size + int(m.group(1), 16) - base if m else None


def candidates(start):
    """出力先の候補: 「mov rcx, REG」または「lea rcx, [rbp-..]」（スタック上の文字列）の後に append を呼ぶもの"""
    b, e = func_range(start)
    insns = list(md.disasm(img[b:e], base + b))
    votes = collections.Counter()
    for i in range(2, len(insns)):
        ins = insns[i]
        if ins.mnemonic == "call" and ins.op_str.startswith("0x") and int(ins.op_str, 16) - base in ADD_OPS:
            for p in reversed(insns[max(0, i - 4):i]):
                if p.op_str.startswith("rcx, "):
                    src = p.op_str[5:]
                    if p.mnemonic == "mov" and src in R64:
                        votes[R64[src]] += 1
                    elif p.mnemonic == "lea" and src.startswith("[r") and "rip" not in src:
                        votes[src] += 1
                    break
    return [o for i, (o, n) in enumerate(votes.most_common(MAX_OUTS)) if i == 0 or n >= 3]


def analyze(start, out):
    b, e = func_range(start)
    insns = list(md.disasm(img[b:e], base + b))

    # 基本ブロック
    leaders = {b}
    for i, ins in enumerate(insns):
        if ins.mnemonic.startswith("j") or ins.mnemonic == "ret":
            if i + 1 < len(insns):
                leaders.add(insns[i + 1].address - base)
            if ins.op_str.startswith("0x"):
                leaders.add(int(ins.op_str, 16) - base)
    blocks, cur = {}, None
    for ins in insns:
        rva = ins.address - base
        if rva in leaders:
            cur = rva
            blocks[cur] = []
        blocks[cur].append(ins)
    order = sorted(blocks)
    nxt = {order[i]: order[i + 1] if i + 1 < len(order) else None for i in range(len(order))}

    # ブロックを、入ってくるレジスタの状態から評価する（分岐をまたいで渡される文字列を拾うため）
    cache = {}

    def eval_block(bb, regs_in):
        key = (bb, regs_in)
        if key in cache:
            return cache[key]
        regs = dict(regs_in)  # reg -> ("lit", s) | ("out",)
        lst = []
        for ins in blocks[bb]:
            mn, opstr = ins.mnemonic, ins.op_str
            parts = [p.strip() for p in opstr.split(",", 1)]
            dst = R64.get(parts[0]) if parts else None
            if mn == "lea" and dst:
                if len(parts) == 2 and parts[1] == out:
                    regs[dst] = ("out",)
                    continue
                t = rip_target(ins)
                s = cstr(t) if t is not None else None
                regs[dst] = ("lit", s) if s is not None else None
            elif mn == "mov" and dst and len(parts) == 2:
                src = R64.get(parts[1])
                if src == out:
                    regs[dst] = ("out",)
                elif src and src in regs:
                    regs[dst] = regs[src]
                else:
                    regs[dst] = None
            elif mn == "call" or (mn == "jmp" and opstr.startswith("0x") and int(opstr, 16) - base in STR_OPS):
                # jmp で文字列操作に飛ぶのは末尾呼び出し（call と同じ扱い）
                callee = int(opstr, 16) - base if opstr.startswith("0x") else None
                rcx, rdx = regs.get("rcx"), regs.get("rdx")
                if callee in STR_OPS and rcx == ("out",):
                    if rdx and rdx[0] == "lit":
                        if callee in ADD_OPS:
                            lst.append(("lit", rdx[1]))
                        else:
                            lst.append(("reset", rdx[1]))
                    else:
                        lst.append(("slot", f"str{callee:x}" if callee else "str"))
                elif callee is not None and (rdx == ("out",) or rcx == ("out",)):
                    lst.append(("slot", f"f{callee:x}"))
                for r in VOLATILE:
                    regs.pop(r, None)
            elif dst and mn not in ("cmp", "test", "push"):
                regs.pop(dst, None)
        res = (tuple(lst), tuple(sorted((k, v) for k, v in regs.items() if v is not None and k in ("rcx", "rdx", "r8", "r9"))))
        cache[key] = res
        return res

    ops, succ = {}, {}
    for bb in order:
        ops[bb] = eval_block(bb, ())[0]
        last = blocks[bb][-1]
        s = []
        if last.mnemonic == "ret":
            pass
        elif last.mnemonic == "jmp":
            if last.op_str.startswith("0x"):
                s.append(int(last.op_str, 16) - base)
        elif last.mnemonic.startswith("j"):
            if last.op_str.startswith("0x"):
                s.append(int(last.op_str, 16) - base)
            if nxt[bb]:
                s.append(nxt[bb])
        elif nxt[bb]:
            s.append(nxt[bb])
        succ[bb] = [x for x in s if x in blocks]

    # 入口: 関数の先頭と、直接の分岐で到達しないブロック（switch の case）
    preds = collections.Counter(x for v in succ.values() for x in v)
    cases = [bb for bb in order if bb != b and preds[bb] == 0]
    # 文字列を読み込んでから共通の追加処理へ飛ぶブロック（"lea rdx, 文字列; jmp ..."）も入口にする。
    # 大きな switch では経路の数の上限に届いて、ここまでたどり着かないことがあるため
    seen_cases = set(cases)
    for bb in order:
        first = blocks[bb][0]
        if bb in seen_cases or bb == b or first.mnemonic != "lea":
            continue
        t = rip_target(first)
        if t is not None and cstr(t) and re.search(r"[a-z]{2}", cstr(t)):
            cases.append(bb)
            seen_cases.add(bb)

    # 共通の後半（多くの case から合流するブロック）を見つける
    reach = collections.Counter()
    for ent in cases:
        seen, todo = set(), [ent]
        while todo:
            x = todo.pop()
            if x in seen:
                continue
            seen.add(x)
            todo.extend(succ[x])
        for x in seen:
            if x != ent:
                reach[x] += 1
    hub_min = max(3, len(cases) // 5)
    hubs = {x for x, n in reach.items() if n >= hub_min and ops[x] or n >= hub_min and x in preds and preds[x] >= 3}

    deadline = time.monotonic() + TIME_LIMIT

    def walk(ent, stop_at_hub):
        found = collections.OrderedDict()
        first_hubs = set()
        count = 0
        stack = [(ent, (), frozenset(), ())]
        while stack and count < MAX_PATHS and time.monotonic() < deadline:
            bb, acc, seen, regs = stack.pop()
            if bb in seen or len(acc) > MAX_OPS:
                continue
            bops, regs_out = eval_block(bb, regs)
            # 合流点で止める。ただし、手前から渡された文字列をここで使う場合は止めない
            carrying = any(v and v[0] == "lit" for _, v in regs)
            if stop_at_hub and bb in hubs and bb != ent and bops == ops[bb] and not carrying:
                count += 1
                first_hubs.add(bb)
                t = render(acc)
                if t is not None:
                    found[t] = 1
                continue
            acc2 = acc
            for op in bops:
                acc2 = (("lit", op[1]),) if op[0] == "reset" else acc2 + (op,)
            if not succ[bb]:
                count += 1
                t = render(acc2)
                if t is not None:
                    found[t] = 1
                continue
            for s in reversed(succ[bb]):
                stack.append((s, acc2, seen | {bb}, regs_out))
        return list(found), first_hubs

    cores, tail_starts = [], set()
    for ent in cases:
        ts, fh = walk(ent, True)
        cores += [t for t in ts if t not in cores and re.search(r"[a-z]{2}", t)]
        tail_starts |= fh
    prefixes, _ = walk(b, True)
    suffixes = []
    for h in sorted(tail_starts):
        ts, _ = walk(h, False)
        suffixes += [t for t in ts if t not in suffixes]
    return b, out, {"prefix": prefixes, "core": cores, "suffix": suffixes}


def render(acc):
    text = ""
    for kind, v in acc:
        text += v if kind == "lit" else "{" + v + "}"
    return text


results = {}
for n_, a in enumerate(args):
    if out_json and n_ % 25 == 0:
        print(f"{n_}/{len(args)}", file=sys.stderr, flush=True)
    try:
        outs = candidates(int(a, 16))
    except Exception as ex:
        print("error", a, ex, file=sys.stderr)
        continue
    for oi, out in enumerate(outs):
        try:
            fb, out, parts = analyze(int(a, 16), out)
        except Exception as ex:
            print("error", a, out, ex, file=sys.stderr)
            continue
        if not parts["core"]:
            continue
        # 出力先が複数ある関数は group を分ける（例: 1a7220, 1a7220.1）
        gid = f"{fb:x}" if oi == 0 else f"{fb:x}.{oi}"
        results[gid] = parts
        if not out_json:
            print(f"== {gid} out={out} prefix={len(parts['prefix'])} core={len(parts['core'])} suffix={len(parts['suffix'])}")
            for k in ("prefix", "core", "suffix"):
                for t in parts[k]:
                    print(f"  [{k}] {t!r}")
if out_json:
    json.dump(results, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(results), "functions;", sum(len(v["core"]) for v in results.values()), "cores")
