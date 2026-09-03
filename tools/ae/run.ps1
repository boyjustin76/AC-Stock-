<#
    애프터이펙트를 BridgeTalk 으로 조종한다.

        .\tools\ae\run.ps1 -Job a1_smoke

    tools/premiere/run.ps1 을 그대로 베낀 것이다. 전송로도 같다:

        PowerShell → Photoshop.Application(COM) → bridge.jsx → BridgeTalk → aftereffects-**

    타깃 이름은 config.json 에 비워 두면 bridge.jsx 가 getSpecifier 로 실측한다.
    실측값과 전체 타깃 목록은 <labDir>/_target.txt 에 떨어진다.

    AE 가 안 떠 있으면 BridgeTalk 이 띄운다. **첫 실행은 사람이 화면을 보는 상태에서 해라** —
    홈 화면·로그인·업데이트 대화상자가 뜨면 모달이고, 모달은 세션을 조용히 죽인다(매뉴얼 §6).

    설정은 tools/ae/config.json, 잡은 tools/ae/jobs/<이름>.jsx.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Job
)

$ErrorActionPreference = 'Stop'
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$jobPath = Join-Path $here "jobs\$Job.jsx"
if (-not (Test-Path $jobPath)) { throw "잡이 없습니다: $jobPath" }

$cfgPath = Join-Path $here 'config.json'
if (-not (Test-Path $cfgPath)) { throw "config.json 이 없습니다: $cfgPath" }
$cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json

$lab = $cfg.labDir
if (-not (Test-Path $lab)) { New-Item -ItemType Directory $lab | Out-Null }
$labLog = Join-Path $lab 'log'
if (-not (Test-Path $labLog)) { New-Item -ItemType Directory $labLog | Out-Null }

# 잡 경로는 슬래시로 (JSX 문자열에서 역슬래시는 이스케이프로 먹힌다)
# BOM 없는 UTF-8 로 쓴다. 저장소 경로에 한글이 있어 ASCII 로는 안 되고, BOM 이 붙으면 JSX 가 경로를 못 찾는다.
$jobFwd = ((Resolve-Path $jobPath).Path).Replace([char]92, [char]47)
[System.IO.File]::WriteAllText((Join-Path $lab '_job.txt'), $jobFwd, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "  잡:  $jobFwd"
Write-Host "  랩:  $lab"
Write-Host "  포토샵 연결 중... (BridgeTalk 전송로)"
$ps = New-Object -ComObject Photoshop.Application
Write-Host "  Photoshop $($ps.Version)"
$ps.DisplayDialogs = 3      # psDisplayNoDialogs

$t = if ($cfg.target) { $cfg.target } else { "(getSpecifier 로 실측)" }
Write-Host "  AE 로 전송: $t  (안 떠 있으면 여기서 뜬다)"
$started = Get-Date
$r = $ps.DoJavaScriptFile((Join-Path $here 'bridge.jsx'))
Write-Host "  bridge: $r"
Write-Host "  걸린 시간: $([math]::Round(((Get-Date) - $started).TotalSeconds, 1))s"

foreach ($n in @('_target.txt', '_result.txt')) {
    $f = Join-Path $lab $n
    if (Test-Path $f) {
        Write-Host ""
        Write-Host "  ---- $n ----"
        Get-Content $f -Encoding UTF8 | ForEach-Object { "    $_" }
    }
}

# 잡이 남긴 로그를 그대로 보여 준다
Get-ChildItem $labLog -Filter '*.txt' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $started.AddMinutes(-1) } |
    ForEach-Object {
        Write-Host ""
        Write-Host "  ---- log\$($_.Name) ----"
        Get-Content $_.FullName -Encoding UTF8 | ForEach-Object { "    $_" }
    }
