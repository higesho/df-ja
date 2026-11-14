"""指定範囲の関数のうち、[reg+0x28] と [reg+0x2c] にレジスタ値を書く関数を探す（単語の px/py を決めるレイアウト関数の候補）。
使い方: python findlayout.py <exe> <from_rva> <to_rva>
"""
import sys, re, pefile, capstone

exe, lo, hi = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
pe = pefile.PE(exe, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
img = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
w28 = re.compile(r"^dword ptr \[r\w+ \+ 0x28\], e|^dword ptr \[r\w+ \+ 0x28\], r\d+d")
w2c = re.compile(r"^dword ptr \[r\w+ \+ 0x2c\], e|^dword ptr \[r\w+ \+ 0x2c\], r\d+d")
for b, e in funcs:
    if not (lo <= b < hi):
        continue
    a = c = 0
    for ins in md.disasm(img[b:e], base + b):
        if ins.mnemonic == "mov":
            if w28.search(ins.op_str):
                a += 1
            if w2c.search(ins.op_str):
                c += 1
    if a and c:
        print(f"{b:#x}-{e:#x} size {e-b:#x}: writes+0x28={a} +0x2c={c}")
