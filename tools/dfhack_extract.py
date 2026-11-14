"""DFHack が画面に出す文字列を集めて、訳す用の TSV（work/dfhack_todo.tsv）にする。

使い方: python -I -X utf8 tools/dfhack_extract.py
出てきた2列目を埋めて translations/dfhack.tsv に足す。
DFHack の置き場所は DFHACK で決め打ちしてあるので、違うときはここを直す。

集める先は「よく画面に出るもの」に絞ってある（操作パネル、建設の計画、隊商の取引）。
ヘルプ本文（hack/docs/）はここには入れていない。
"""
import pathlib
import re
import sys

DFHACK = pathlib.Path(r"L:\SteamLibrary\steamapps\common\DFHack\hack")
OUT = pathlib.Path(__file__).resolve().parents[1] / "work" / "dfhack_todo.tsv"
SPACE = re.compile(r"\s+")

# Lua の文字列（'…' と "…"）。逃がし文字つきも拾う
STR = r"""(?:'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")"""
PIECE = re.compile(r"""'((?:\\.|[^'\\])*)'|"((?:\\.|[^"\\])*)\"""")

# 画面に出る文字列が入っている場所。".." でつないだ複数行も1つにまとめる
KEYS = ("label", "desc", "text", "intro_text", "frame_title", "title", "tooltip", "key_sep", "option_gap")

# 集める対象のファイル（よく画面に出るものだけ）
SOURCES = [
    "scripts/gui/control-panel.lua",
    "scripts/internal/control-panel/registry.lua",
    "lua/plugins/buildingplan/planneroverlay.lua",
    "lua/plugins/buildingplan/itemselection.lua",
    "lua/plugins/buildingplan/filterselection.lua",
    "scripts/internal/caravan/trade.lua",
    "scripts/internal/caravan/movegoods.lua",
    "scripts/internal/caravan/tradeagreement.lua",
    "scripts/internal/caravan/common.lua",
]

# 訳さないもの（命令の名前、キーの名前、記号だけ）
SKIP = re.compile(
    r"^(?:[A-Z][a-z]*\+[A-Za-z0-9]+|[a-z]|Enter|Esc|Shift|Ctrl|Alt|"
    r"[\W\d]+|[a-z0-9_]+[./][a-z0-9_.\-]+|[a-z0-9_]+\.[a-z0-9_]+)$"
)


def strings(text, key):
    pat = re.compile(key + r"\s*=\s*(" + STR + r"(?:\s*\.\.\s*" + STR + r")*)")
    for m in pat.finditer(text):
        parts = PIECE.findall(m.group(1))
        s = "".join(a or b for a, b in parts)
        s = s.replace("\\'", "'").replace('\\"', '"')
        s = SPACE.sub(" ", s).strip()
        if s and re.search(r"[A-Za-z]{3}", s) and not SKIP.match(s):
            yield s


def main():
    if not DFHACK.exists():
        sys.exit(f"DFHack が見つかりません: {DFHACK}")
    out = []
    for rel in SOURCES:
        path = DFHACK / rel
        if not path.exists():
            print(f"（無い: {rel}）")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for key in KEYS:
            out += list(strings(text, key))
    # 上の取り出しでは拾えないが画面に出るもの
    out += [
        "DFHack Control Panel", "Enabled", "Autostart", "Automation", "Bug Fixes", "Gameplay",
        "UI Overlays", "Preferences", "No matches", "On", "Off", "Are you sure?",
        "Restore defaults", "Default preferences restored.", "Overlay defaults restored.",
        "Are you sure you want to restore default preferences?",
        "Are you sure you want to restore overlay defaults?",
        "show Planner", "hide Planner", "[any material]", "With filters",
    ]
    seen, rows = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            rows.append(s)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(s + "\t" for s in rows) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} 件 -> {OUT}")


if __name__ == "__main__":
    main()
