"""文字列を参照している命令（lea reg, [rip+disp]）を探し、その後の call を表示する。
使い方: python xref.py <exe> "<文字列の一部>"
"""
import sys, bisect, struct, pefile, capstone

exe, needle = sys.argv[1], sys.argv[2].encode("latin-1")
pe = pefile.PE(exe, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
starts = [f[0] for f in funcs]
img = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase
text = next(s for s in pe.sections if s.Name.startswith(b".text"))
t0, t1 = text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize

def func_of(rva):
    i = bisect.bisect_right(starts, rva) - 1
    while i >= 0 and not (funcs[i][0] <= rva < funcs[i][1]):
        i -= 1
    return funcs[i] if i >= 0 else None

# 文字列の先頭を探す（ヌル終端の直後から始まる位置まで戻る）
pos = img.find(needle)
targets = []
while pos != -1:
    s = pos
    while s > 0 and img[s - 1] != 0:
        s -= 1
    targets.append(s)
    pos = img.find(needle, pos + 1)
print("string RVAs:", [hex(t) for t in targets])
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
code = img[t0:t1]
for tgt in targets:
    # lea r64, [rip+disp32]: 48/4C 8D modrm(00 reg 101) disp32 — 7 bytes
    for i in range(len(code) - 7):
        if code[i] in (0x48, 0x4C) and code[i + 1] == 0x8D and (code[i + 2] & 0xC7) == 0x05:
            disp = struct.unpack_from("<i", code, i + 3)[0]
            if t0 + i + 7 + disp == tgt:
                rva = t0 + i
                f = func_of(rva)
                print(f"-- xref at {rva:#x} in func {f[0]:#x}" if f else f"-- xref at {rva:#x}")
                n = 0
                for ins in md.disasm(img[rva: rva + 0x60], base + rva):
                    print(f"   {ins.address - base:#x}: {ins.mnemonic} {ins.op_str}")
                    n += 1
                    if ins.mnemonic == "call" and n > 1:
                        break
