"""Dwarf Fortress.exe の .pdata から関数範囲を引き、指定 RVA を含む関数と呼び出し直前の命令を表示する。
使い方: python funcs.py <exe> <rva...>
"""
import sys, bisect, pefile, capstone

exe = sys.argv[1]
pe = pefile.PE(exe, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
starts = [f[0] for f in funcs]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
img = pe.get_memory_mapped_image()
base = pe.OPTIONAL_HEADER.ImageBase

def func_of(rva):
    i = bisect.bisect_right(starts, rva) - 1
    while i >= 0 and not (funcs[i][0] <= rva < funcs[i][1]):
        i -= 1
    return funcs[i] if i >= 0 else None

for a in sys.argv[2:]:
    rva = int(a, 16)
    f = func_of(rva)
    print(f"== RVA {rva:#x}: func {f[0]:#x}-{f[1]:#x} (size {f[1]-f[0]:#x})" if f else f"== {rva:#x}: no func")
    code = img[rva - 0x60: rva + 0x10]
    for ins in md.disasm(code, base + rva - 0x60):
        mark = "  <==" if ins.address == base + rva else ""
        print(f"  {ins.address - base:#x}: {ins.mnemonic} {ins.op_str}{mark}")
