# 配布用の zip を作る。
#
#   powershell -ExecutionPolicy Bypass -File tools\package.ps1
#
# できるもの: dist\dfint-ja-<版>.zip
# 中身は、ゲームフォルダにそのまま重ねてコピーすれば動く形:
#
#   dfhooks.dll           … 橋渡し役（同じフォルダの dfhooks_*.dll をすべて読み込む）
#   dfhooks_dfint_ja.dll  … 日本語化の本体
#   dfint-data\           … 辞書・フォント・設定
#   はじめにお読みください.txt
#   LICENSE\              … エンジンとフォントのライセンス
#
# 先に engine と chainloader をビルドしておくこと（-Build を付ければここでやる）
param(
  [switch]$Build,
  [string]$Version
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root 'dist'

if (-not $Version) {
  # engine/Cargo.toml の version を使う
  $line = Select-String -Path (Join-Path $root 'engine\Cargo.toml') -Pattern '^version\s*=\s*"(.+)"' | Select-Object -First 1
  $Version = if ($line) { $line.Matches[0].Groups[1].Value } else { '0.0.0' }
}

if ($Build) {
  Write-Host "ビルドします…（版: $Version）"
  # 画面の左下に出る版の文字列。付けないと「開発版」になる
  $env:HOOK_VERSION = $Version
  Push-Location (Join-Path $root 'engine');      cargo build --release; if ($LASTEXITCODE) { throw 'engine のビルドに失敗' };      Pop-Location
  Push-Location (Join-Path $root 'chainloader'); cargo build --release; if ($LASTEXITCODE) { throw 'chainloader のビルドに失敗' }; Pop-Location
  Push-Location $root; python -I -X utf8 tools\build.py; if ($LASTEXITCODE) { throw 'tools\build.py に失敗' }; Pop-Location
}

$engineDll = Join-Path $root 'engine\target\release\dfint_hook.dll'
$chainDll  = Join-Path $root 'chainloader\target\release\dfhooks.dll'
foreach ($f in @($engineDll, $chainDll)) {
  if (-not (Test-Path $f)) { throw "ビルド結果がありません: $f（-Build を付けるか、先に cargo build --release）" }
}

$stage = Join-Path $dist "dfint-ja-$Version"
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force $stage | Out-Null

Copy-Item -Force $chainDll  (Join-Path $stage 'dfhooks.dll')
Copy-Item -Force $engineDll (Join-Path $stage 'dfhooks_dfint_ja.dll')

$data = Join-Path $stage 'dfint-data'
New-Item -ItemType Directory -Force $data | Out-Null
Copy-Item -Recurse -Force (Join-Path $root 'data\lookups')      (Join-Path $data 'lookups')
Copy-Item -Recurse -Force (Join-Path $root 'data\dictionaries') (Join-Path $data 'dictionaries')
New-Item -ItemType Directory -Force (Join-Path $data 'fonts') | Out-Null
Copy-Item -Force (Join-Path $root 'fonts\NotoSansMonoCJKjp-Bold.otf') (Join-Path $data 'fonts')
foreach ($f in 'config.txt', 'offsets.txt', 'simple-dictionary.csv', 'legacy-dictionary.csv',
               'no-translate-callers.txt', 'context-dictionary.csv', 'paragraph-dictionary.csv',
               'sentence-templates.csv') {
  Copy-Item -Force (Join-Path $root "data\$f") $data
}

$lic = Join-Path $stage 'LICENSE'
New-Item -ItemType Directory -Force $lic | Out-Null
foreach ($f in (Join-Path $root 'engine\LICENSE'), (Join-Path $root 'fonts\OFL-LICENSE.txt')) {
  if (Test-Path $f) { Copy-Item -Force $f $lic }
}

Copy-Item -Force (Join-Path $root 'docs\はじめにお読みください.txt') $stage

$zip = Join-Path $dist "dfint-ja-$Version.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip
$size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "できました: $zip （$size MB）"
Write-Host "中身を確かめるには: $stage"
