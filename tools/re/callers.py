"""関数 RVA を call している箇所を数え、いくつか表示する。
使い方: python callers.py <exe> <rva> [表示数]
"""
import sys, struct, bisect, pefile

exe, tgt = sys.argv[1], int(sys.argv[2], 16)
show = int(sys.argv[3]) if len(sys.argv) > 3 else 15
pe = pefile.PE(exe, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
starts = [f[0] for f in funcs]
img = pe.get_memory_mapped_image()
text = next(s for s in pe.sections if s.Name.startswith(b".text"))
t0, t1 = text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize
code = img[t0:t1]
hits = []
i = code.find(b"\xe8")
while i != -1 and i < len(code) - 5:
    disp = struct.unpack_from("<i", code, i + 1)[0]
    if t0 + i + 5 + disp == tgt:
        hits.append(t0 + i)
    i = code.find(b"\xe8", i + 1)
def func_of(rva):
    j = bisect.bisect_right(starts, rva) - 1
    return funcs[j][0] if j >= 0 else None
print(f"{len(hits)} call sites; in {len({func_of(h) for h in hits})} functions")
for h in hits[:show]:
    print(f"  {h:#x} in {func_of(h):#x}")
