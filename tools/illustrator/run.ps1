<#
    일러스트레이터를 COM 으로 띄워 같은 폴더의 .jsx 를 실행한다.
    tools/photoshop/run.ps1 과 같은 구조다.

        .\tools\illustrator\run.ps1 dump_ai
        .\tools\illustrator\run.ps1 build_live

    경로는 박지 않는다 (labdir.ps1). jsx 는 PowerShell 함수를 못 부르니 환경변수로 넘긴다.

    주의 — 남이 쓰는 중인 앱은 건드리지 않는다. 켜져 있으면 먼저 확인한다.
#>
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [switch]$Force        # 남의 문서가 열려 있어도 진행
)

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
# BOM 없이 쓴다 — PS 5.1 의 Set-Content -Encoding UTF8 은 BOM 을 붙이는데 jsx 는 eval 전에 떼지 않는다
# (총괄 개선안 B-1, 2026-09-17). tools/ae/run.ps1 과 같은 방식.
[System.IO.File]::WriteAllText((Join-Path $here '_paths.json'), $paths, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "  참고자료: $lab"
Write-Host "  결과 자리: $out"
Write-Host "  저장소: $repo"

<#  남이 쓰는 중인 앱은 건드리지 않는다 (EXTENDSCRIPT-TRAPS ⑥).
    2026-09-16: 사용자가 직접 쓰려고 띄워 둔 인스턴스에 빌드를 던져 일러스트레이터가 멈췄다.
    24.7MB 원본을 열고 문서 간 복사를 시키는 잡이라 남의 문서와 엉킨다.
    떠 있으면 열린 문서를 세어 보고, 사람이 쓰던 흔적이 있으면 멈춘다.
    -Force 를 주면 그래도 진행한다.                                            #>
$ill = Get-Process -Name Illustrator -ErrorAction SilentlyContinue
if ($ill -and -not $Force) {
    $docs = -1
    try {
        $probe = New-Object -ComObject Illustrator.Application
        $docs = $probe.Documents.Count
    } catch { }
    if ($docs -gt 0) {
        $names = @()
        try { for ($i = 1; $i -le $docs; $i++) { $names += "    - " + $probe.Documents.Item($i).Name } } catch { }
        $msg = "일러스트레이터가 이미 떠 있고 문서 $docs 개가 열려 있습니다."
        if ($names) { $msg += [Environment]::NewLine + ($names -join [Environment]::NewLine) }
        $msg += [Environment]::NewLine + "  이 잡은 원본 .ai 를 열고 문서 사이로 항목을 복사합니다 - 남의 문서와 엉켜 멈춥니다."
        $msg += [Environment]::NewLine + "  쓰고 계신 것이 없다면 일러스트레이터를 닫고 다시 실행하세요."
        $msg += [Environment]::NewLine + "  '[복구됨]' 이 붙어 있으면 크래시 잔재입니다 - 저장하지 말고 닫으세요."
        $msg += [Environment]::NewLine + "  그래도 진행하려면 -Force 를 주세요."
        throw $msg
    }
    if ($docs -lt 0) { Write-Host "  (일러스트레이터가 떠 있지만 상태를 못 읽었습니다 — 바쁜 중일 수 있습니다)" }
}

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
