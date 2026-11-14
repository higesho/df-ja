"""RVA から n 命令を逆アセンブルする。文字列参照は中身も表示。
使い方: python dis.py <exe> <rva> [count]
"""
import sys, re, pefile, capstone

exe, rva, n = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 80
pe = pefile.PE(exe, fast_load=True)
img = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = False
count = 0
for ins in md.disasm(img[rva: rva + n * 16], base + rva):
    note = ""
    m = re.search(r"\[rip \+ (0x[0-9a-f]+)\]", ins.op_str)
    if m:
        tgt = ins.address + ins.size + int(m.group(1), 16) - base
        if 0 <= tgt < len(img):
            s = img[tgt:tgt + 60].split(b"\0")[0]
            if len(s) >= 4 and all(32 <= c < 127 for c in s):
                note = f'   ; "{s.decode()}"'
            else:
                note = f"   ; -> {tgt:#x}"
    if ins.mnemonic == "call":
        try:
            note += f"   ; call {int(ins.op_str, 16) - base:#x}"
        except ValueError:
            pass
    print(f"{ins.address - base:#x}: {ins.mnemonic} {ins.op_str}{note}")
    count += 1
    if count >= n:
        break
