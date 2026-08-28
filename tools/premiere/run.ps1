<#
    프리미어를 BridgeTalk 으로 조종한다.

        .\tools\premiere\run.ps1 probe

    프리미어에는 Photoshop.Application 에 해당하는 COM 자동화 ProgID 가 없다(레지스트리 실측).
    그래서 검증된 포토샵 COM 드라이버를 전송로로 재사용한다:

        PowerShell → Photoshop.Application(COM) → bridge.jsx → BridgeTalk → premierepro-26.0

    프리미어가 안 떠 있으면 BridgeTalk 이 띄운다. 첫 실행은 사람이 화면을 보는 상태에서 해라
    (미디어 연결 대화상자가 뜬다 — 프리셋 미디어는 D:\ 를 가리키는데 이 PC 는 G:\ 다).

    설정은 tools/premiere/config.json, 잡은 tools/premiere/jobs/<이름>.jsx.
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

# 잡 경로는 슬래시로 (§6 — JSX 문자열에서 역슬래시는 이스케이프로 먹힌다)
# BOM 없는 UTF-8 로 쓴다. 저장소 경로에 한글이 있어 ASCII 로는 안 되고, BOM 이 붙으면 JSX 가 경로를 못 찾는다.
$jobFwd = ((Resolve-Path $jobPath).Path).Replace([char]92, [char]47)
[System.IO.File]::WriteAllText((Join-Path $lab '_job.txt'), $jobFwd, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "  잡:  $jobFwd"
Write-Host "  랩:  $lab"
Write-Host "  포토샵 연결 중... (BridgeTalk 전송로)"
$ps = New-Object -ComObject Photoshop.Application
Write-Host "  Photoshop $($ps.Version)"
$ps.DisplayDialogs = 3      # psDisplayNoDialogs

Write-Host "  프리미어로 전송: $($cfg.target)  (안 떠 있으면 여기서 뜬다)"
$started = Get-Date
$r = $ps.DoJavaScriptFile((Join-Path $here 'bridge.jsx'))
Write-Host "  bridge: $r"
Write-Host "  걸린 시간: $([math]::Round(((Get-Date) - $started).TotalSeconds, 1))s"

$res = Join-Path $lab '_result.txt'
if (Test-Path $res) {
    Write-Host ""
    Write-Host "  ---- _result.txt ----"
    Get-Content $res -Encoding UTF8 | ForEach-Object { "    $_" }
}

# 잡이 남긴 로그를 그대로 보여 준다 (밑줄로 시작하는 내부 파일은 뺀다)
Get-ChildItem $lab -Filter '*.txt' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $started.AddMinutes(-1) -and $_.Name -notlike '_*' } |
    ForEach-Object {
        Write-Host ""
        Write-Host "  ---- $($_.Name) ----"
        Get-Content $_.FullName -Encoding UTF8 | ForEach-Object { "    $_" }
    }
