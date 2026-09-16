<#
    일러스트레이터를 COM 으로 띄워 같은 폴더의 .jsx 를 실행한다.
    tools/photoshop/run.ps1 과 같은 구조다.

        .	ools\illustrator
un.ps1 dump_ai
        .	ools\illustrator
un.ps1 build_live

    경로는 박지 않는다 (labdir.ps1). jsx 는 PowerShell 함수를 못 부르니 환경변수로 넘긴다.

    주의 — 남이 쓰는 중인 앱은 건드리지 않는다. 켜져 있으면 먼저 확인한다.
#>
param([Parameter(Mandatory = $true)][string]$Script)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$jsx  = Join-Path $here "$Script.jsx"
if (-not (Test-Path $jsx)) { throw "스크립트가 없습니다: $jsx" }

$cfgPath = Join-Path $here 'config.json'
if (-not (Test-Path $cfgPath)) { throw "config.json 이 없습니다: $cfgPath" }
$cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json

. (Join-Path $here 'labdir.ps1')
$lab = Get-LiveDir     $cfg.labDir
$out = Get-DeliverDir  $cfg.outDir

# 저장소 뿌리 — 한지 결 사진 같은 소재를 jsx 가 여기 기준으로 찾는다
$repo = (Resolve-Path (Join-Path $here '..\..')).Path

# jsx 에 경로를 넘기는 길 — 환경변수는 못 쓴다.
# $.getenv 는 일러스트레이터가 '떠 있던 시점'의 환경만 본다. 앱이 이미 켜져 있으면
# 나중에 set 한 변수가 안 간다(2026-09-16 실측). 그래서 파일로 넘긴다.
$paths = @{
    liveframeDir = $lab
    outDir       = $out
    repoDir      = $repo
} | ConvertTo-Json
Set-Content -Path (Join-Path $here '_paths.json') -Value $paths -Encoding UTF8
Write-Host "  참고자료: $lab"
Write-Host "  결과 자리: $out"
Write-Host "  저장소: $repo"

Write-Host "  일러스트레이터 연결 중..."
$ai = New-Object -ComObject Illustrator.Application
Write-Host "  Illustrator $($ai.Version)"

Write-Host "  실행: $Script.jsx"
$result = $ai.DoJavaScriptFile($jsx)
Write-Host "  결과: $result"

foreach ($name in 'ai_tree.txt', 'build_log.txt') {
    $log = Join-Path $out $name
    if ((Test-Path $log) -and ((Get-Item $log).LastWriteTime -gt (Get-Date).AddMinutes(-10))) {
        Write-Host ""
        Write-Host "  ---- $name ----"
        Get-Content $log -Encoding UTF8 | ForEach-Object { "    $_" }
    }
}
