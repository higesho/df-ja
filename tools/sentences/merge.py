"""翻訳されたバッチ（work/sentences/out/NNN.tsv）を検査して translations/sentences.tsv にまとめる。

out の各行: group<TAB>kind<TAB>英語<TAB>日本語
検査:
  - 英語がバッチに存在する（書き換えられていない）
  - 日本語の {N} の集合が英語と同じ（core 以外で {REST} を使っていない）
  - 日本語が空でない（prefix / suffix で英語に単語が無い場合は空でもよい）
  - 英単語がそのまま残っていない（{N} の外に 3 文字以上の英単語があれば警告）
合格した行だけを translations/sentences.tsv に書く（既存の手直しは translations/sentences-fix.tsv が優先）。

使い方: python tools/sentences/merge.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / "work" / "sentences"
SLOT = re.compile(r"\{(\d+)\}")
WORD = re.compile(r"(?<![{A-Za-z])[A-Za-z]{3,}(?![A-Za-z}])")
KEEP_EN = {"DF", "FPS", "OK", "MOD", "ID"}
COLOR = re.compile(r"\[C:\d+:\d+:\d+\]")


def canon(text):
    """色の変更 [C:a:b:c] の違いは区別しない（エンジンが任意の色として照合する）"""
    return COLOR.sub("[C]", text)


def load_batches():
    """翻訳単位 (kind, 英語) と、それを使うすべての部品 (group, kind, 英語)"""
    known, units = {}, []
    for p in sorted((WORK / "batches").glob("*.json")):
        for it in json.loads(p.read_text(encoding="utf-8")):
            known[(it["kind"], canon(it["text"]))] = it
            if p.name.startswith("txt_"):
                units.append((it["group"], it["kind"], it["text"]))
    up = WORK / "units.json"
    if up.exists():
        units += [(u["group"], u["kind"], u["text"]) for u in json.loads(up.read_text(encoding="utf-8"))]
    return known, units


def check(kind, en, ja):
    if "\n" in ja:
        return "改行が入っている"
    en_slots = set(SLOT.findall(en))
    ja_slots = set(SLOT.findall(ja))
    if en_slots != ja_slots:
        return f"差し込み番号が違う 英{sorted(en_slots)} 日{sorted(ja_slots)}"
    if "{REST}" in ja and kind != "core":
        return "{REST} は core だけ"
    rest = re.sub(r"\{(\d+|REST)\}", "", ja)
    if re.search(r"\{[^}]*\}", rest):
        return "不明な {...} がある"
    if not ja.strip() and kind == "core":
        return "訳が空"
    # [..] のトークンと、英語の原文に大文字のまま出てくる語（方角 NSEW など）は残してよい
    rest = re.sub(r"\[[^\]]*\]", "", rest)
    # 原文に大文字で始まる形で出てくる語（キー名 Ctrl、固有名、方角 NSEW など）はそのまま残してよい
    allowed = {w for w in WORD.findall(en) if w[0].isupper()}
    left = [w for w in WORD.findall(rest) if w not in KEEP_EN and w not in allowed]
    if left:
        return "英単語が残っている: " + " ".join(left[:3])
    return None


def main():
    known, units = load_batches()
    ok, bad = {}, []
    for p in sorted((WORK / "out").glob("*.tsv")):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                if len(parts) == 3 and parts[1] in ("prefix", "suffix"):
                    parts.append("")
                else:
                    bad.append((p.name, n, "列が足りない", line))
                    continue
            group, kind, en, ja = parts[:4]
            if (kind, canon(en)) not in known:
                bad.append((p.name, n, "英語がバッチに無い", line))
                continue
            err = check(kind, en, ja)
            if err:
                bad.append((p.name, n, err, line))
                continue
            ok[(kind, canon(en))] = ja
    missing = [k for k in known if k not in ok]
    # 訳を、同じ部品を使うすべての関数に配る
    full = {(g, k, e): ok[(k, canon(e))] for g, k, e in units if (k, canon(e)) in ok}
    rows = sorted(full.items(), key=lambda kv: (kv[0][0], ["prefix", "core", "suffix"].index(kv[0][1]), kv[0][2]))
    (ROOT / "translations" / "sentences.tsv").write_text(
        "# 実行ファイルの文の部品の訳（tools/sentences/merge.py が生成。手直しは sentences-fix.tsv へ）\n"
        + "".join(f"{g}\t{k}\t{e}\t{j}\n" for (g, k, e), j in rows),
        encoding="utf-8",
    )
    (WORK / "rejected.tsv").write_text("".join(f"{a}\t{b}\t{c}\t{d}\n" for a, b, c, d in bad), encoding="utf-8")
    (WORK / "missing.json").write_text(json.dumps([known[k] for k in missing], ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"合格 {len(ok)} / 不合格 {len(bad)} / 未翻訳 {len(missing)}（全 {len(known)}）")


if __name__ == "__main__":
    main()
