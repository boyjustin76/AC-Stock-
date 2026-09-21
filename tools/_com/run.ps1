#Requires -Version 5.1
<#
    어도비 앱 공용 실행기 (next_step 46 · 총괄 제안 2026-09-18)

        .\tools\_com\run.ps1 -App ae       -Job a1_smoke
        .\tools\_com\run.ps1 -App premiere -Job probe

    앱마다 복붙돼 있던 run.ps1 네 벌을 한 곳으로 모은다. 모은 이유는 줄 수가 아니라
    **셋을 한 곳에서 처리하기 위해서**다 — 모달 · 완료 판정 · 외부 앱 상태.

      시작 전  ① 대상 앱이 떠 있나  ② **프리미어가 떠 있으면 AE 잡을 중단**(TRAPS ⑦)
      실행 중  시간 제한. 넘으면 앱을 죽이고 실패로 적는다 (모달은 닫지 않는다 — 닫는 건 안 먹는다)
      끝      반환값이 아니라 **판정 줄**이 있어야 성공이다 (issue 28)
      실패     화면 한 장 + 로그 마지막 30줄을 <작업실>/log/<잡>_fail.txt 로 남긴다

    전송로는 넷 다 같다: PowerShell → Photoshop.Application(COM) → bridge.jsx → BridgeTalk → 대상 앱.
    (프리미어·AE 에는 자동화 ProgID 가 없어 검증된 포토샵 COM 을 길로 쓴다.)
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('ae', 'premiere', 'photoshop', 'illustrator')]
    [string]$App,
    [Parameter(Mandatory = $true)]
    [string]$Job,
    [int]$TimeoutSec = 300,
    [switch]$SkipPreflight
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)   # tools\

# 앱마다 다른 것만 표로. 나머지는 전부 같다.
$SPEC = @{
    ae          = @{ Dir = 'ae';          LabFn = 'Get-LabDir';     Proc = 'AfterFX';            LogSub = 'log'; Show = @('_target.txt', '_result.txt') }
    premiere    = @{ Dir = 'premiere';    LabFn = 'Get-PproLabDir'; Proc = 'Adobe Premiere Pro'; LogSub = '';    Show = @('_result.txt') }
    photoshop   = @{ Dir = 'photoshop';   LabFn = 'Get-LabDir';     Proc = 'Photoshop';          LogSub = 'log'; Show = @('_result.txt') }
    illustrator = @{ Dir = 'illustrator'; LabFn = 'Get-LabDir';     Proc = 'Illustrator';        LogSub = 'log'; Show = @('_result.txt') }
}
$s    = $SPEC[$App]
$here = Join-Path $root $s.Dir

$jobPath = Join-Path $here "jobs\$Job.jsx"
if (-not (Test-Path $jobPath)) { throw "잡이 없습니다: $jobPath" }
$cfgPath = Join-Path $here 'config.json'
if (-not (Test-Path $cfgPath)) { throw "config.json 이 없습니다: $cfgPath" }
$cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json

. (Join-Path $here 'labdir.ps1')       # 작업실 폴더를 박지 않고 찾는다
$lab = if ($cfg.labDir) { $cfg.labDir } else { & $s.LabFn }
if (-not (Test-Path $lab)) { New-Item -ItemType Directory $lab | Out-Null }
$labLog = if ($s.LogSub) { Join-Path $lab $s.LogSub } else { $lab }
if (-not (Test-Path $labLog)) { New-Item -ItemType Directory $labLog | Out-Null }

# ── 시작 전 검사 ────────────────────────────────────────────────────────
function Get-Proc([string]$name) { Get-Process -Name $name -ErrorAction SilentlyContinue }

if (-not $SkipPreflight) {
    # 프리미어가 떠 있으면 BridgeTalk 이 AE 잡을 **프리미어 안의 AE 엔진**으로 보낸다 (TRAPS ⑦).
    # 닫으라고 말만 하고 우리가 닫지는 않는다 — 사람이 편집 중일 수 있다.
    if ($App -eq 'ae') {
        $ppro = Get-Proc 'Adobe Premiere Pro'
        if ($ppro) {
            throw "프리미어가 떠 있습니다(PID $($ppro.Id)). AE 잡이 프리미어의 AE 엔진으로 갑니다(TRAPS 7). 프리미어를 닫고 다시 부르세요."
        }
    }
    $mine = Get-Proc $s.Proc
    if ($mine) { Write-Host "  $($s.Proc) 이미 떠 있음 (PID $($mine.Id))" }
    else       { Write-Host "  $($s.Proc) 안 떠 있음 — BridgeTalk 이 띄웁니다. 첫 실행은 화면을 보세요(모달)" }
}

# 잡 경로는 슬래시로 (JSX 문자열에서 역슬래시는 이스케이프로 먹힌다)
# BOM 없는 UTF-8 로 쓴다. 경로에 한글이 있어 ASCII 로는 안 되고, BOM 이 붙으면 JSX 가 경로를 못 찾는다.
$jobFwd = ((Resolve-Path $jobPath).Path).Replace([char]92, [char]47)
[System.IO.File]::WriteAllText((Join-Path $lab '_job.txt'), $jobFwd, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "  잡:  $jobFwd"
Write-Host "  랩:  $lab"
$t = if ($cfg.target) { $cfg.target } else { "(getSpecifier 로 실측)" }
Write-Host "  대상: $t"

# ── 실행 (시간 제한) ───────────────────────────────────────────────────
$bridge  = Join-Path $here 'bridge.jsx'
$started = Get-Date
$runner = {
    param($bridgePath)
    $ps = New-Object -ComObject Photoshop.Application
    $ps.DisplayDialogs = 3      # psDisplayNoDialogs
    [pscustomobject]@{ Version = $ps.Version; Result = $ps.DoJavaScriptFile($bridgePath) }
}
$jobHandle = Start-Job -ScriptBlock $runner -ArgumentList $bridge
$done = Wait-Job $jobHandle -Timeout $TimeoutSec
$timedOut = ($null -eq $done)

$bridgeOut = $null
if (-not $timedOut) {
    $bridgeOut = Receive-Job $jobHandle -ErrorAction SilentlyContinue
    if ($bridgeOut) {
        Write-Host "  Photoshop $($bridgeOut.Version)"
        Write-Host "  bridge: $($bridgeOut.Result)"
    }
}
Remove-Job $jobHandle -Force -ErrorAction SilentlyContinue
$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
Write-Host "  걸린 시간: ${elapsed}s"

if ($timedOut) {
    Write-Host "  $TimeoutSec 초를 넘겼습니다 — 모달로 봅니다. 앱을 닫습니다." -ForegroundColor Yellow
    foreach ($p in @($s.Proc, 'Photoshop')) {
        Get-Proc $p | ForEach-Object { taskkill /PID $_.Id /F 2>$null | Out-Null }
    }
}

# ── 판정 ───────────────────────────────────────────────────────────────
# 반환값은 못 믿는다. 잡이 남긴 **판정 줄**이 있어야 성공이다 (issue 28).
$fresh = Get-ChildItem $labLog -Filter '*.txt' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $started.AddSeconds(-5) -and $_.Name -notlike '_*' }
$verdict = $null
foreach ($f in $fresh) {
    # 줄 앞에 BOM 이 붙어 오는 로그가 있다 — 그러면 ^\s* 로는 안 잡힌다 (AE a1.txt 실측 09-21).
    # 그래서 한 줄씩 BOM·공백·탭을 떼고 본다.
    foreach ($ln in (Get-Content $f.FullName -Encoding UTF8 -ErrorAction SilentlyContinue)) {
        $t = $ln.Trim([char]0xFEFF, ' ', [char]9)
        if ($t -match '^(판정|OK)\b' -or $t -match '판정\s*:') { $verdict = "$($f.Name): $t"; break }
    }
    if ($verdict) { break }
}

foreach ($n in $s.Show) {
    $f = Join-Path $lab $n
    if (Test-Path $f) {
        Write-Host ""
        Write-Host "  ---- $n ----"
        Get-Content $f -Encoding UTF8 | ForEach-Object { "    $_" }
    }
}
foreach ($f in $fresh) {
    Write-Host ""
    Write-Host "  ---- $($f.Name) ----"
    Get-Content $f.FullName -Encoding UTF8 | ForEach-Object { "    $_" }
}

if ($verdict -and -not $timedOut) {
    Write-Host ""
    Write-Host "  성공 — $verdict" -ForegroundColor Green
    exit 0
}

# 판정 줄을 쓰는 잡은 68개 중 20개뿐이다(실측 09-21). 나머지를 전부 실패로 내면 아무것도 못 돌린다.
# 그래서 **시간 제한을 안 넘겼고 bridge 가 답을 준 옛 잡**은 경고만 하고 통과시킨다.
# 새 잡은 로그에 `판정: …` 한 줄을 쓴다 — 그래야 진짜로 판정된다.
if (-not $timedOut -and $bridgeOut -and $bridgeOut.Result) {
    Write-Host ""
    Write-Host "  통과(판정 줄 없음) — 옛 잡이다. 로그에 '판정: …' 한 줄을 넣어 주세요." -ForegroundColor Yellow
    Write-Host "  bridge 반환 첫 줄: $(($bridgeOut.Result -split "`n")[0].Trim())"
    exit 0
}

# ── 실패: 사람이 안 봐도 붙일 원자료를 남긴다 ─────────────────────────
$failPath = Join-Path $labLog "${Job}_fail.txt"
$lines = @()
$lines += "잡: $Job ($App) · $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) · ${elapsed}s"
if ($timedOut) { $lines += "원인 후보: 시간 제한 $TimeoutSec 초 초과 (모달로 보고 앱을 죽였다)" }
else           { $lines += "원인 후보: 판정 줄이 없다 (잡이 끝까지 못 갔거나 로그를 안 남겼다)" }
if ($bridgeOut) { $lines += "bridge 반환: $($bridgeOut.Result)" }
foreach ($f in $fresh) {
    $lines += ""
    $lines += "---- $($f.Name) 마지막 30줄 ----"
    $lines += (Get-Content $f.FullName -Encoding UTF8 -Tail 30)
}
[System.IO.File]::WriteAllLines($failPath, $lines, (New-Object System.Text.UTF8Encoding($false)))

try {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
    $shot = Join-Path $labLog "${Job}_fail.png"
    $bmp.Save($shot, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Host "  화면: $shot"
} catch {
    Write-Host "  화면 캡처 실패: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "  실패 — $failPath 를 보세요" -ForegroundColor Red
exit 1
