"""Haiku の訳（work/ui2/out/*.tsv）を検査して translations/ui-extra.tsv にまとめる。
- 英語がバッチに無いもの、トークン（[C:..] %d など）が合わないもの、日本語が入っていないものは除く
- 日本語が "-" のものは「訳さない」（内部用）として記録だけする
- 訳が無かった英語は work/ui2/missing.json に書く（再実行用）

使い方: python tools/ui/merge.py                     work/ui2 → translations/ui-extra.tsv
        python tools/ui/merge.py ui3 raw-descriptions  work/ui3 → translations/raw-descriptions.tsv（raw の [DESCRIPTION]）
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
W = ROOT / "work" / (sys.argv[1] if len(sys.argv) > 1 else "ui2")
OUT_NAME = (sys.argv[2] if len(sys.argv) > 2 else "ui-extra") + ".tsv"
TOKEN = re.compile(r"\[[A-Z/][A-Z0-9_:/.\-]*\]|%[0-9.]*[sdif]|\{[^}]*\}")  # ゲームのトークン（[C:7:0:1] [B] など）。[Completed] のような普通の語は除く
JA = re.compile(r"[぀-ヿ㐀-鿿]")


def main():
    want = []
    for f in sorted((W / "batches").glob("b*.json")):
        want += json.load(open(f, encoding="utf-8"))
    wanted = set(want)
    got, skip, bad = {}, set(), []
    for f in sorted((W / "out").glob("*.tsv")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if "\t" not in line:
                continue
            en, ja = line.split("\t", 1)
            if en not in wanted:
                # 前後の空白が落ちた行は、空白を戻して照合する
                cand = [w for w in want if w.strip() == en.strip()]
                if len(cand) != 1:
                    bad.append(("not-in-batch", en, ja))
                    continue
                en = cand[0]
            ja = ja.strip("\t")
            if ja.strip() == "-":
                skip.add(en)
                continue
            if sorted(TOKEN.findall(en)) != sorted(TOKEN.findall(ja)):
                bad.append(("token", en, ja))
                continue
            if not JA.search(ja):
                bad.append(("no-japanese", en, ja))
                continue
            # 行末の空白は英語に合わせる（"Strongest Odor: " → "最も強い匂い: "）
            tail = en[len(en.rstrip()):]
            ja = ja.rstrip() + tail
            got[en] = ja
    missing = [w for w in want if w not in got and w not in skip]
    out = ROOT / "translations" / OUT_NAME
    out.write_text("# 実行ファイル内の UI 文字列のうち ui.tsv に無かったもの（tools/ui/merge.py が生成）\n"
                   + "".join(f"{en}\t{ja}\n" for en, ja in sorted(got.items(), key=lambda kv: kv[0].lower())),
                   encoding="utf-8")
    (W / "rejected.tsv").write_text("".join(f"{k}\t{e}\t{j}\n" for k, e, j in bad), encoding="utf-8")
    json.dump(missing, open(W / "missing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"合格 {len(got)} / 訳さない {len(skip)} / 不合格 {len(bad)} / 未出力 {len(missing)}（全 {len(want)}）")


if __name__ == "__main__":
    main()
