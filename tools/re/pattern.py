"""関数先頭のバイト列を表示し、パターン（?? はワイルドカード）がファイル内で一意か確かめる。
使い方: python pattern.py <exe> dump <rva> <len>
        python pattern.py <exe> check "<pattern>"
"""
import sys, re, pefile

exe, mode = sys.argv[1], sys.argv[2]
data = open(exe, "rb").read()
pe = pefile.PE(exe, fast_load=True)
if mode == "dump":
    rva, n = int(sys.argv[3], 16), int(sys.argv[4])
    off = pe.get_offset_from_rva(rva)
    print(" ".join(f"{b:02x}" for b in data[off:off + n]))
else:
    toks = sys.argv[3].split()
    rx = b"".join(b"." if t == "??" else re.escape(bytes([int(t, 16)])) for t in toks)
    hits = [m.start() for m in re.finditer(rx, data, re.S)]
    print(len(hits), [hex(pe.get_rva_from_offset(h)) for h in hits[:5]])
