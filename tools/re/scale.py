"""英文の部品になりそうな文字列の数と、それを参照する関数の数を数える（規模の見積もり用）。"""
import sys, re, struct, bisect, collections, pefile

exe = sys.argv[1]
pe = pefile.PE(exe, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
starts = [f[0] for f in funcs]
img = pe.get_memory_mapped_image()
rdata = next(s for s in pe.sections if s.Name.startswith(b".rdata"))
r0, r1 = rdata.VirtualAddress, rdata.VirtualAddress + rdata.Misc_VirtualSize
text = next(s for s in pe.sections if s.Name.startswith(b".text"))
t0, t1 = text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize

# 英語の部品らしい文字列: 小文字の英単語を含み、空白を含むか先頭/末尾が空白
frag = {}
for m in re.finditer(rb"[\x20-\x7e]{3,}\x00", img[r0:r1]):
    s = m.group()[:-1].decode()
    if not re.search(r"[a-z]{2}", s) or re.search(r"[_\\/%]|\.(txt|png|dll|cpp)|::|^[A-Z0-9_:]+$", s):
        continue
    if " " in s:
        frag[r0 + m.start()] = s

# lea r64,[rip+disp] で参照している関数
code = img[t0:t1]
def func_of(rva):
    j = bisect.bisect_right(starts, rva) - 1
    return funcs[j][0] if j >= 0 else None
refs = collections.defaultdict(set)
for i in range(len(code) - 7):
    if code[i] in (0x48, 0x4C) and code[i + 1] == 0x8D and (code[i + 2] & 0xC7) == 0x05:
        tgt = t0 + i + 7 + struct.unpack_from("<i", code, i + 3)[0]
        if tgt in frag:
            refs[func_of(t0 + i)].add(tgt)

used = set().union(*refs.values())
print("部品らしい文字列:", len(frag), "うちコードから参照:", len(used))
sizes = sorted(((len(v), f) for f, v in refs.items()), reverse=True)
print("参照する関数:", len(sizes))
for th in (5, 20, 50, 100):
    print(f"  部品を{th}個以上使う関数: {sum(1 for n, _ in sizes if n >= th)}")
print("上位:", [(hex(f), n) for n, f in sizes[:12]])
# 部品の例（歴史・伝説系）
ex = [s for a, s in frag.items() if a in used and re.search(r"^ ?(was|were|became|attacked|the )", s)]
print("例:", ex[:15])

import json as _j
_j.dump([f"{f:x}" for n, f in sizes if n >= 3 and f is not None], open(sys.argv[2] if len(sys.argv) > 2 else "funcs.json", "w"))
