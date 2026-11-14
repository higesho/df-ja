"""未訳の文の部品（work/untranslated_msgids.json のうち前後に空白があるもの）を参照する関数を一括で探す。
使い方（dfint-ja で）: python -I tools/re/frag_xref.py "../Dwarf Fortress.exe"  → work/frag/refs.json
"""
import sys, json
EXE = sys.argv.pop(1)
import sys, re, bisect, struct, collections, pefile, pathlib
sys.path.insert(0, 'tools/ui')
import importlib.util
spec = importlib.util.spec_from_file_location('p', 'tools/ui/prepare.py'); p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
exe = EXE
items = json.load(open('work/untranslated_msgids.json', encoding='utf-8'))
frag = [x for x in set(items) if not p.selectable(x) and (x.startswith(' ') or x.endswith(' ')) and re.search('[A-Za-z]{2}', x)]
pe = pefile.PE(exe, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
funcs = sorted({(e.struct.BeginAddress, e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION})
starts = [f[0] for f in funcs]
img = pe.get_memory_mapped_image()
text = next(s for s in pe.sections if s.Name.startswith(b".text"))
t0, t1 = text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize
def func_of(rva):
    i = bisect.bisect_right(starts, rva) - 1
    while i >= 0 and not (funcs[i][0] <= rva < funcs[i][1]): i -= 1
    return funcs[i][0] if i >= 0 else None
# 文字列 → RVA（完全一致、NUL 終端）
want = {}
for x in frag:
    b = x.encode('latin-1', 'ignore')
    pos = img.find(b'\0' + b + b'\0')
    while pos != -1:
        want.setdefault(pos + 1, x)
        pos = img.find(b'\0' + b + b'\0', pos + 1)
code = bytes(img[t0:t1])
refs = collections.defaultdict(set)
for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]', code):
    i = m.start()
    disp = struct.unpack_from('<i', code, i + 3)[0]
    tgt = t0 + i + 7 + disp
    if tgt in want:
        f = func_of(t0 + i)
        if f is not None: refs[want[tgt]].add(f)
done = set(k.split('.')[0] for k in json.load(open('work/sentences/all_paths.json', encoding='utf-8')))
byf = collections.Counter()
for x, fs in refs.items():
    for f in fs: byf[f] += 1
nores = [x for x in frag if x not in refs]
covered = [x for x, fs in refs.items() if any(f'{f:x}' in done for f in fs)]
print('frag', len(frag), 'found str', len(set(want.values())), 'with xref', len(refs), 'in analyzed funcs', len(covered), 'no xref', len(nores))
print('funcs', len(byf), 'new funcs', sum(1 for f in byf if f'{f:x}' not in done))
print(byf.most_common(30))
json.dump({'refs': {x: sorted(f'{f:x}' for f in fs) for x, fs in refs.items()}, 'nores': nores}, __import__('os').makedirs('work/frag', exist_ok=True) or open('work/frag/refs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
