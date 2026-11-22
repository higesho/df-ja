"""ゲームを起動せずに、翻訳の抜けを探して回帰を見る。

エンジンそのもの（engine の dfint-check）を使うので、辞書・ルックアップ・文テンプレートの
すべてを通した結果が見られる。tools/sentences/test.py は文テンプレートだけを再現したものなので、
品物名のように組み立て型のルックアップを使うものはそちらでは測れない。

使い方（dfint-ja の中で実行する）:
  python -I -X utf8 tools/check.py                 work/check/*.txt を訳して前回と比べる
  python -I -X utf8 tools/check.py --update        比較用の控えを今回の結果で更新する
  python -I -X utf8 tools/check.py --miss          訳せなかった行だけを出す
  python -I -X utf8 tools/check.py ファイル…       そのファイルだけを見る

準備:
  cd engine && cargo build --release --features offline --bin dfint-check
  （ゲームフォルダの dfint-data を読むので、インストール済みの辞書が対象になる）
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME = ROOT.parent
EXE = ROOT / "engine" / "target" / "release" / "dfint-check.exe"
CASES = ROOT / "work" / "check"

# 訳せたかどうかの判定。小文字の英単語が3文字以上残っていたら訳せていないとみなす。
# 固有名詞は英語のままでよいので、次のものは数えない:
#   ・大文字で始まる語（Urist、Bronzecrow）
#   ・アクセント付きの字を含む語（Thîkut、Bëmbul。ドワーフ語の名前はこの形が多い）
#   ・引用符の中（二つ名）と [ ] のマークアップ
#   ・英語の機能語（the / of / and。名前の中に出てくる）
LATIN = re.compile(r"[A-Za-zÀ-ɏ'\-]+")
FUNCTION_WORDS = {"the", "of", "and", "in", "to", "a", "an"}


def translated(ja):
    s = re.sub(r"\[[^\]]*\]", "", ja)
    s = re.sub(r'"[^"]*"', "", s)
    for word in LATIN.findall(s):
        bare = word.strip("'-")
        if len(bare) < 3 or bare[:1].isupper() or bare.lower() in FUNCTION_WORDS:
            continue
        if any(ord(ch) > 127 for ch in bare):  # アクセント付き = 固有名詞
            continue
        return False
    return True


def run(path):
    if not EXE.exists():
        sys.exit(f"{EXE} がありません。engine で cargo build --release --features offline --bin dfint-check")
    # lines_*.txt は、ゲームが自分で折り返して1行ずつ描く文章（性格の説明など）。
    # 同じ呼び出し元から続けて来た行をつないで訳すので、行の並びとして渡す（dfint-check lines）
    if is_lines(path):
        args = [str(EXE), "lines"]
    elif is_paragraph(path):
        args = [str(EXE), "paragraph"]
    else:
        args = [str(EXE)]
    out = subprocess.run(args, stdin=path.open("rb"), capture_output=True, cwd=str(GAME))
    rows = []
    for line in out.stdout.decode("utf-8", "replace").splitlines():
        en, _, ja = line.partition("\t")
        if en:
            rows.append((en, ja))
    return rows


def is_lines(path):
    return path.name.startswith("lines_")


def is_paragraph(path):
    """para_*.txt は、ゲームが単語ごとに折り返して描く文章（芸術の形式の説明など）。

    1行を1つの文章として markup_process_string の経路で訳す"""
    return path.name.startswith("para_")


def last_pass(rows):
    """行の並びの検査では、最後の描画（最後の "=====" より後ろ）の段落ごとに訳をつないで数える。

    それより前の描画は、段落を覚える途中の結果。控えとの比較には全部の行を使う。
    訳は英語より短く、後ろの行が空になるので、行ごとではなく段落（英語が文末で終わるところまで）で見る。
    """
    passes = [[]]
    for row in rows:
        if row[0] == "=====":
            passes.append([])
        else:
            passes[-1].append(row)
    last = next((p for p in reversed(passes) if p), [])
    blocks, en_acc, ja_acc = [], "", ""
    for en, ja in last:
        en_acc += en
        ja_acc += ja
        if en.rstrip().endswith((".", "!", "?")):
            blocks.append((en_acc, ja_acc))
            en_acc, ja_acc = "", ""
    if en_acc:
        blocks.append((en_acc, ja_acc))
    return blocks


def main(argv):
    update = "--update" in argv
    miss_only = "--miss" in argv
    names = [a for a in argv if not a.startswith("-")]
    files = [pathlib.Path(n) for n in names] if names else sorted(p for p in CASES.glob("*.txt") if not p.name.endswith(".base.txt"))
    if not files:
        sys.exit(f"調べるファイルがありません: {CASES}")
    total = miss = diff = 0
    for path in files:
        rows = run(path)
        counted = last_pass(rows) if is_lines(path) else rows
        missing = [(en, ja) for en, ja in counted if not translated(ja)]
        total += len(counted)
        miss += len(missing)
        base = path.with_suffix(".base.txt")
        text = "".join(f"{en}\t{ja}\n" for en, ja in rows)
        if update or not base.exists():
            base.write_text(text, encoding="utf-8", newline="\n")
            mark = "控えを更新"
        else:
            old = base.read_text(encoding="utf-8").splitlines()
            new = text.splitlines()
            d = sum(1 for a, b in zip(old, new) if a != b) + abs(len(old) - len(new))
            diff += d
            mark = "前回と同じ" if d == 0 else f"前回と違う行 {d}"
        print(f"{path.name:24} {len(counted):6} 行 / 未訳 {len(missing):4} / {mark}")
        if miss_only:
            for en, ja in missing:
                print(f"    {en}")
    print(f"合計 {total} 行 / 未訳 {miss} / 前回と違う行 {diff}")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
