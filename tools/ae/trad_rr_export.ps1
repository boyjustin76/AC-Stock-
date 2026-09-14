<#
    손익비 (전통) mogrt 내보내기 — 내보내기 → zip 검사 → 누락 난 것만 다시(최대 3회) → 13개 전부 통과 + aep 그대로일 때만 팩으로.

        powershell -ExecutionPolicy Bypass -File tools\ae\trad_rr_export.ps1 [-Fresh]

    -Fresh  : 밖 폴더를 비우고 13개를 처음부터 내보낸다 (기본은 밖 폴더에 있는 것을 먼저 검사).
    AE 잡은 한 번에 하나만 보낸다. 잡이 멈추면 강제 종료하지 않고 여기서 멈춘다(2026-09-14 비정상 종료 뒤 원칙).
    ※ 이 파일은 UTF-8 BOM 으로 저장해야 PowerShell 5.1 이 한글을 읽는다.
#>
param([switch]$Fresh)
$ErrorActionPreference = 'Continue'
$env:PYTHONIOENCODING = "utf-8"
$repo    = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$checker = Join-Path $repo "tools\ae\trad_rr_mogrt_check.py"
$outDir  = "C:\aelab\trad_rr_mogrt_out"
$packMog = "C:\aelab\pack\trad_rr\mogrt"
$aepPath = "C:\aelab\pack\trad_rr\trad_rr.aep"
$jobLog  = "C:\aelab\log\c5x.txt"
Set-Location $repo

function Send-Export {
    if (Test-Path $jobLog) { [System.IO.File]::Delete($jobLog) }
    try { powershell -ExecutionPolicy Bypass -File tools\ae\run.ps1 -Job c5x_trad_rr_export | Out-Null } catch {}
    $deadline = (Get-Date).AddMinutes(7)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path $jobLog) -and ((Get-Content $jobLog -Raw -Encoding UTF8) -match "판정")) { return "끝" }
        Start-Sleep -Seconds 4
    }
    return "시간 초과"
}

New-Item -ItemType Directory -Force $outDir | Out-Null
$aepBefore = (Get-Item $aepPath).LastWriteTime
if ($Fresh) {
    foreach ($f in (Get-ChildItem $outDir -File)) { [System.IO.File]::Delete($f.FullName) }
    $state = Send-Export
    "처음 내보내기: $state"
    if ($state -ne "끝") { "AE 잡 미완 — 여기서 멈춤 (강제 종료 안 함)"; exit 2 }
}
for ($round = 1; $round -le 3; $round++) {
    "== 검사 $round =="
    python $checker --out $outDir
    if ($LASTEXITCODE -eq 0) { break }
    $state = Send-Export
    "다시 내보내기 $round : $state"
    if (Test-Path $jobLog) { Get-Content $jobLog -Encoding UTF8 | Select-String -Pattern "대상|true|false|ERR|판정" | ForEach-Object { $_.Line } }
    if ($state -ne "끝") { "AE 잡 미완 — 여기서 멈춤 (강제 종료 안 함)"; exit 2 }
}
"== 최종 검사 =="
python $checker --out $outDir
$final = $LASTEXITCODE
$aepAfter = (Get-Item $aepPath).LastWriteTime
if ($aepBefore -eq $aepAfter) { "aep 그대로: $aepAfter" } else { "aep 바뀜: $aepBefore -> $aepAfter" }
if ($final -eq 0 -and $aepBefore -eq $aepAfter) {
    [System.IO.File]::Delete((Join-Path $outDir "_only.txt"))
    New-Item -ItemType Directory -Force $packMog | Out-Null
    foreach ($old in (Get-ChildItem $packMog -Filter *.mogrt)) { [System.IO.File]::Delete($old.FullName) }
    Copy-Item (Join-Path $outDir "*.mogrt") $packMog -Force
    "팩 mogrt 로 옮김: $((Get-ChildItem $packMog -Filter *.mogrt).Count)개"
    exit 0
}
"미통과 — 팩 mogrt 는 건드리지 않음"
exit 1
