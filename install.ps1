# dfint-ja の導入用スクリプト。
#
# **このスクリプトは必須ではありません。** 置くファイルは状況によらず同じ3つなので、
# 配布物をゲームフォルダに重ねてコピーするだけで動きます（DFHack の有無も、入れる順番も関係ありません）。
#
#   dfhooks.dll           … 橋渡し役。同じフォルダの dfhooks_*.dll をすべて読み込む
#   dfhooks_dfint_ja.dll  … 日本語化の本体
#   dfint-data\           … 辞書・フォント・設定
#
# このスクリプトは、開発中にビルド結果を上の形に並べ直すための手間を省くものです。
#
# 使い方: PowerShell で  .\install.ps1            （インストール / 更新）
#                        .\install.ps1 -Uninstall （アンインストール）
param(
  [switch]$Uninstall,
  [string]$GameDir = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$chainDll = Join-Path $GameDir 'dfhooks.dll'
$dll = Join-Path $GameDir 'dfhooks_dfint_ja.dll'
$dataDir = Join-Path $GameDir 'dfint-data'
$marker = Join-Path $dataDir '.dfint-ja'

if (-not (Test-Path (Join-Path $GameDir 'Dwarf Fortress.exe'))) {
  throw "Dwarf Fortress.exe が見つかりません: $GameDir"
}

function Test-OurDll($path) {
  (Test-Path $path) -and (Select-String -Path $path -Pattern 'dfint-ja' -SimpleMatch -Quiet)
}

if ($Uninstall) {
  if (Test-Path $marker) {
    Remove-Item -Recurse -Force $dataDir
    Write-Host "dfint-data を削除しました"
  } elseif (Test-Path $dataDir) {
    Write-Warning "dfint-data は dfint-ja が作ったものではないため残します"
  }
  if (Test-OurDll $dll) {
    Remove-Item -Force $dll
    Write-Host "dfhooks_dfint_ja.dll を削除しました"
  }
  # dfhooks.dll は DFHack のものかもしれないので、自分のものだと分かるときだけ消す
  if (Test-OurDll $chainDll) {
    Remove-Item -Force $chainDll
    Write-Host "dfhooks.dll を削除しました"
  } elseif (Test-Path $chainDll) {
    Write-Host "dfhooks.dll は dfint-ja のものではないので残します（DFHack のものと思われます）"
  }
  return
}

$builtDll = Join-Path $here 'engine\target\release\dfint_hook.dll'
$builtChain = Join-Path $here 'chainloader\target\release\dfhooks.dll'
if (-not (Test-Path $builtDll)) { throw "engine のビルド結果がありません。engine で cargo build --release を実行してください" }
if (-not (Test-Path $builtChain)) { throw "chainloader のビルド結果がありません。chainloader で cargo build --release を実行してください" }

New-Item -ItemType Directory -Force $dataDir | Out-Null
New-Item -ItemType File -Force $marker | Out-Null

Copy-Item -Force $builtDll $dll
# DFHack が自分の橋渡し役を置いていたら、そのままにしておく（どちらの橋渡し役でも両方読み込まれる）。
# 日本語化の橋渡し役は、DFHack が居るときは DFHack のものに処理を丸ごと任せる作りになっている
if ((Test-Path $chainDll) -and -not (Test-OurDll $chainDll)) {
  Write-Host "ほかの dfhooks.dll（DFHack のものと思われます）があるので、そのままにしました"
} else {
  Copy-Item -Force $builtChain $chainDll
}

# ユーザー辞書（user-*.csv）とログは残して、それ以外を入れ替える
foreach ($sub in 'lookups', 'dictionaries', 'fonts') {
  $dst = Join-Path $dataDir $sub
  if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
}
Copy-Item -Recurse -Force (Join-Path $here 'data\lookups') (Join-Path $dataDir 'lookups')
Copy-Item -Recurse -Force (Join-Path $here 'data\dictionaries') (Join-Path $dataDir 'dictionaries')
# MOD 用の翻訳パック（dfint-ja が同梱するもの）。
# 利用者が自分で置いたパックを消さないよう、同梱分と同じ名前のフォルダだけ入れ替える
$modsSrc = Join-Path $here 'data\mods'
if (Test-Path $modsSrc) {
  $modsDst = Join-Path $dataDir 'mods'
  New-Item -ItemType Directory -Force $modsDst | Out-Null
  foreach ($pack in Get-ChildItem -Directory $modsSrc) {
    $dst = Join-Path $modsDst $pack.Name
    if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
    Copy-Item -Recurse -Force $pack.FullName $dst
  }
}
New-Item -ItemType Directory -Force (Join-Path $dataDir 'fonts') | Out-Null
Copy-Item -Force (Join-Path $here 'fonts\NotoSansMonoCJKjp-Bold.otf') (Join-Path $dataDir 'fonts')
foreach ($f in 'offsets.txt', 'simple-dictionary.csv', 'legacy-dictionary.csv', 'no-translate-callers.txt', 'context-dictionary.csv', 'paragraph-dictionary.csv', 'sentence-templates.csv') {
  Copy-Item -Force (Join-Path $here "data\$f") (Join-Path $dataDir $f)
}
# config.txt は利用者が編集している可能性があるので、無いときだけ置く
$cfg = Join-Path $dataDir 'config.txt'
if (-not (Test-Path $cfg)) { Copy-Item (Join-Path $here 'data\config.txt') $cfg }

Write-Host "dfint-ja をインストールしました: $GameDir"
Write-Host "ゲーム内では Ctrl+F2 で日本語化のオン/オフを切り替えられます"
