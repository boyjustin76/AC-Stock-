#Requires -Version 5.1
<#
    어도비 앱 공용 실행기 (next_step 46 · 총괄 제안 2026-09-18)

        .\tools\_com\run.ps1 -App ae          -Job a1_smoke
        .\tools\_com\run.ps1 -App premiere    -Job probe
        .\tools\_com\run.ps1 -App illustrator -Job build_live
        .\tools\_com\run.ps1 -App photoshop   -Job dump_episodes

    앱마다 복붙돼 있던 run.ps1 네 벌을 한 곳으로 모은다. 모은 이유는 줄 수가 아니라
    **셋을 한 곳에서 처리하기 위해서**다 — 모달 · 완료 판정 · 외부 앱 상태.

      시작 전  ① 대상 앱이 떠 있나  ② 남의 문서가 열려 있나(일러)  ③ **프리미어가 떠 있으면 AE 잡 중단**(TRAPS ⑦)
      실행 중  시간 제한. 넘으면 **먼저 찍고** 앱을 죽인다 (모달은 닫지 않는다 — 닫는 건 안 먹는다)
      끝      반환값이 아니라 **판정 줄**이 있어야 성공이다 (issue 28)
      실패     모달 그림·글자 + 문구 분류 + 로그 마지막 30줄을 <로그자리>/<잡>_fail.txt 로 남긴다

    전송로는 둘이다.
      bridge (ae·premiere)          PowerShell → Photoshop.Application(COM) → bridge.jsx → BridgeTalk → 대상 앱
                                    프리미어·AE 에는 자동화 ProgID 가 없어 검증된 포토샵 COM 을 길로 쓴다.
                                    잡은 <앱>/jobs/<잡>.jsx.
      direct (illustrator·photoshop) PowerShell → <앱>.Application(COM) → DoJavaScriptFile(잡)
                                    제 ProgID 가 있으니 남의 앱을 거치지 않는다. 잡은 <앱>/<잡>.jsx.

    이 파일은 한글이 들어 있으니 **UTF-8 with BOM** 으로 쓴다 (constraint 63).
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('ae', 'premiere', 'photoshop', 'illustrator')]
    [string]$App,
    [Parameter(Mandatory = $true)]
    [string]$Job,
    [int]$TimeoutSec = 300,
    [switch]$SkipPreflight,
    [switch]$SkipDocGuard,      # 남의 문서가 열려 있어도 진행 (옛 -Force)
    [switch]$NoJev              # 모달 문구 분류에서 표만 본다 (키 없이·값 없이)
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)   # tools\

# 앱마다 다른 것만 표로. 나머지는 전부 같다.
$SPEC = @{
    ae          = @{ Dir = 'ae';          Transport = 'bridge'; Proc = 'AfterFX';            LabFn = 'Get-LabDir';     LogSub = 'log'; Show = @('_target.txt', '_result.txt') }
    premiere    = @{ Dir = 'premiere';    Transport = 'bridge'; Proc = 'Adobe Premiere Pro'; LabFn = 'Get-PproLabDir'; LogSub = '';    Show = @('_result.txt') }
    photoshop   = @{ Dir = 'photoshop';   Transport = 'direct'; Proc = 'Photoshop';          ProgId = 'Photoshop.Application';   Prep = 'Prep-Photoshop';   DocGuard = $false; Show = @() }
    illustrator = @{ Dir = 'illustrator'; Transport = 'direct'; Proc = 'Illustrator';        ProgId = 'Illustrator.Application'; Prep = 'Prep-Illustrator'; DocGuard = $true;  Show = @() }
}
$s    = $SPEC[$App]
$here = Join-Path $root $s.Dir

$jobPath = if ($s.Transport -eq 'bridge') { Join-Path $here "jobs\$Job.jsx" } else { Join-Path $here "$Job.jsx" }
if (-not (Test-Path $jobPath)) { throw "잡이 없습니다: $jobPath" }
$cfgPath = Join-Path $here 'config.json'
if (-not (Test-Path $cfgPath)) { throw "config.json 이 없습니다: $cfgPath" }
$cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json

. (Join-Path $here 'labdir.ps1')       # 작업실 폴더를 박지 않고 찾는다

# ── 앱마다 다른 준비 (direct 전송로만) ────────────────────────────────
#    돌려주는 것은 @{ Lab = 작업 기준 폴더; Log = 잡이 로그를 남기는 폴더 }.

function Prep-Illustrator {
    param([string]$Here, $Cfg)
    # jsx 에 경로를 넘기는 길 — 환경변수는 못 쓴다. $.getenv 는 일러스트레이터가 '떠 있던 시점'의
    # 환경만 본다. 앱이 이미 켜져 있으면 나중에 set 한 변수가 안 간다(2026-09-16 실측).
    # BOM 없이 쓴다 — jsx 는 eval 전에 BOM 을 떼지 않는다 (총괄 개선안 B-1. .ps1 은 반대다 — constraint 63).
    $lab  = Get-LiveDir    $Cfg.labDir
    $out  = Get-DeliverDir $Cfg.outDir
    $repo = (Resolve-Path (Join-Path $Here '..\..')).Path
    $paths = @{ liveframeDir = $lab; outDir = $out; repoDir = $repo } | ConvertTo-Json
    [System.IO.File]::WriteAllText((Join-Path $Here '_paths.json'), $paths, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "  참고자료: $lab"
    Write-Host "  결과 자리: $out"
    Write-Host "  저장소: $repo"
    return @{ Lab = $lab; Log = $out }
}

function Prep-Photoshop {
    param([string]$Here, $Cfg)
    $lab      = Get-CmgWorkDir $Cfg.labDir
    $template = Resolve-UnderLab $Cfg.template $lab
    $out      = Resolve-UnderLab $Cfg.outDir   $lab
    Write-Host "  작업실: $lab"
    if (-not (Test-Path $template)) {
        throw "템플릿을 찾을 수 없습니다: $template`n   작업실 폴더는 '$lab' 로 잡혔습니다. 여기가 아니면 CMGWORK_DIR 환경변수나 config.json 의 labDir 을 주세요.`n   원본 .psd 는 저장소에 없습니다(180MB)."
    }
    return @{ Lab = $lab; Log = $out }
}

if ($s.Transport -eq 'bridge') {
    $lab = if ($cfg.labDir) { $cfg.labDir } else { & $s.LabFn }
    if (-not (Test-Path $lab)) { New-Item -ItemType Directory $lab | Out-Null }
    $labLog = if ($s.LogSub) { Join-Path $lab $s.LogSub } else { $lab }
} else {
    $prep   = & $s.Prep $here $cfg
    $lab    = $prep.Lab
    $labLog = $prep.Log
}
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
    else       { Write-Host "  $($s.Proc) 안 떠 있음 — COM 이 띄웁니다. 첫 실행은 화면을 보세요(모달)" }

    <#  떠 있는데 COM 이 답하지 않으면 **스플래시에서 굳은 것**이다 (2026-09-21 B 실측).
        일러스트레이터를 taskkill 한 직후 다시 부르니 시작 화면에서 멈췄고, 그 위로 잡을 던져
        제한 시간 600초를 통째로 태웠다. CPU 는 5분에 4초밖에 안 늘었다.
        죽이지는 않는다 — 사람이 막 띄운 중일 수도 있다. 말하고 멈춘다. #>
    $probe = $null
    if ($mine -and $s.ProgId) {
        try { $probe = New-Object -ComObject $s.ProgId; $null = $probe.Version } catch { $probe = $null }
        if (-not $probe) {
            throw "$($s.Proc) 가 떠 있는데(PID $($mine.Id)) COM 이 답하지 않습니다.`n   뜨는 중이거나 시작 화면에서 굳었습니다. 잠시 뒤 다시 부르고, 그래도 같으면 앱을 닫고 다시 부르세요.`n   지금 화면을 보려면: python tools/_com/shot_window.py --proc $($s.Proc) --out shot.png"
        }
    }

    <#  남이 쓰는 중인 앱은 건드리지 않는다 (EXTENDSCRIPT-TRAPS ⑥).
        2026-09-16: 사용자가 직접 쓰려고 띄워 둔 일러스트레이터에 빌드를 던져 앱이 멈췄다.
        24.7MB 원본을 열고 문서 간 복사를 시키는 잡이라 남의 문서와 엉킨다.
        포토샵은 반대다 — 템플릿을 연 채로 두는 것이 정상이라(둘째 실행부터 빠르다) 검사하지 않는다. #>
    if ($s.DocGuard -and $probe -and -not $SkipDocGuard) {
        $docs = -1
        try { $docs = $probe.Documents.Count } catch { }
        if ($docs -gt 0) {
            $names = @()
            try { for ($i = 1; $i -le $docs; $i++) { $names += "    - " + $probe.Documents.Item($i).Name } } catch { }
            $msg = "$($s.Proc) 가 이미 떠 있고 문서 $docs 개가 열려 있습니다."
            if ($names) { $msg += [Environment]::NewLine + ($names -join [Environment]::NewLine) }
            $msg += [Environment]::NewLine + "  이 잡은 원본 .ai 를 열고 문서 사이로 항목을 복사합니다 - 남의 문서와 엉켜 멈춥니다."
            $msg += [Environment]::NewLine + "  쓰고 계신 것이 없다면 앱을 닫고 다시 실행하세요."
            $msg += [Environment]::NewLine + "  '[복구됨]' 이 붙어 있으면 크래시 잔재입니다 - 저장하지 말고 닫으세요."
            $msg += [Environment]::NewLine + "  그래도 진행하려면 -SkipDocGuard 를 주세요."
            throw $msg
        }
        if ($docs -lt 0) { Write-Host "  ($($s.Proc) 가 떠 있지만 상태를 못 읽었습니다 — 바쁜 중일 수 있습니다)" }
    }
}

# 잡 경로는 슬래시로 (JSX 문자열에서 역슬래시는 이스케이프로 먹힌다)
$jobFwd = ((Resolve-Path $jobPath).Path).Replace([char]92, [char]47)
if ($s.Transport -eq 'bridge') {
    # BOM 없는 UTF-8 로 쓴다. 경로에 한글이 있어 ASCII 로는 안 되고, BOM 이 붙으면 JSX 가 경로를 못 찾는다.
    [System.IO.File]::WriteAllText((Join-Path $lab '_job.txt'), $jobFwd, (New-Object System.Text.UTF8Encoding($false)))
}

Write-Host "  잡:  $jobFwd"
Write-Host "  랩:  $lab"
Write-Host "  로그 자리: $labLog"
if ($s.Transport -eq 'bridge') {
    $t = if ($cfg.target) { $cfg.target } else { "(getSpecifier 로 실측)" }
    Write-Host "  대상: $t"
}

# ── 실행 (시간 제한) ───────────────────────────────────────────────────
$started = Get-Date
if ($s.Transport -eq 'bridge') {
    $runner = {
        param($bridgePath)
        $ps = New-Object -ComObject Photoshop.Application
        $ps.DisplayDialogs = 3      # psDisplayNoDialogs
        [pscustomobject]@{ Version = $ps.Version; Result = $ps.DoJavaScriptFile($bridgePath) }
    }
    $runArg = Join-Path $here 'bridge.jsx'
} else {
    $runner = {
        # 잡을 그대로 던진다. 알림 끄기는 잡이 스스로 한다 —
        # 일러스트레이터의 userInteractionLevel 은 COM 쪽 이름이 판마다 달라 여기서 건드리지 않는다.
        param($progId, $jsxPath)
        $app = New-Object -ComObject $progId
        if ($progId -like 'Photoshop*') { $app.DisplayDialogs = 3 }     # psDisplayNoDialogs
        [pscustomobject]@{ Version = $app.Version; Result = $app.DoJavaScriptFile($jsxPath) }
    }
    $runArg = @($s.ProgId, (Resolve-Path $jobPath).Path)
}
$jobHandle = Start-Job -ScriptBlock $runner -ArgumentList $runArg
$done = Wait-Job $jobHandle -Timeout $TimeoutSec
$timedOut = ($null -eq $done)

# 시간은 **여기서** 잰다. `Remove-Job -Force` 는 COM 에 붙잡힌 잡을 끝내려고 한참 기다린다 —
# 45초 제한을 걸고 165초가 찍혔다(2026-09-21 B 실측). 잡 치우기는 앱을 죽인 뒤로 미룬다.
$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)

$bridgeOut = $null
if (-not $timedOut) {
    $bridgeOut = Receive-Job $jobHandle -ErrorAction SilentlyContinue
    if ($bridgeOut) {
        Write-Host "  $($s.Proc) $($bridgeOut.Version)"
        Write-Host "  결과: $($bridgeOut.Result)"
    }
    Remove-Job $jobHandle -Force -ErrorAction SilentlyContinue
}
Write-Host "  걸린 시간: ${elapsed}s"

# ── 모달을 뜬다 — **죽이기 전에** ──────────────────────────────────────
#    앱을 먼저 죽이면 창이 사라져 원인도 같이 사라진다. 1단계는 죽인 뒤에 찍고 있었다(09-21 B 발견).
$shot      = Join-Path $labLog "${Job}_fail.png"
$modalJson = Join-Path $labLog "${Job}_modal.json"
$classJson = Join-Path $labLog "${Job}_modal_class.json"
$modalFound = $false
$modalProc = $null
$failPath  = Join-Path $labLog "${Job}_fail.txt"
# 지난번 실패 자취를 먼저 지운다 — 안 지우면 이번에 안 찍혔을 때 **옛 모달을 이번 것으로 읽는다.**
foreach ($stale in @($shot, $modalJson, $classJson, $failPath)) {
    Remove-Item $stale -Force -ErrorAction SilentlyContinue
}

function Read-Modal {
    # 돌려주는 것: 모달을 가진 프로세스 이름, 못 찾으면 $null.
    # bridge 는 대상 앱 다음에 포토샵도 본다. AE 잡의 alert() 는 AE 에 떴고 포토샵은 깨끗했다(09-22 D 실측) —
    # 그래도 포토샵이 시작 화면 등에서 막히면 DoJavaScriptFile 부터 멈추니 한 번 더 본다.
    $py = Join-Path $PSScriptRoot 'modal_text.py'
    $procs = if ($s.Transport -eq 'bridge') { @($s.Proc, 'Photoshop') } else { @($s.Proc) }
    foreach ($p in $procs) {
        & python $py --proc $p --out $shot --json $modalJson 2>&1 | ForEach-Object { Write-Host "    modal_text($p): $_" }
        if ($LASTEXITCODE -eq 0) { return $p }
    }
    Remove-Item $modalJson -Force -ErrorAction SilentlyContinue   # 못 찾은 쪽이 남긴 빈 기록
    # 모달을 못 찾았다 — 앱 창 전체라도 찍어 둔다 (shot_window.py, PrintWindow)
    $py2 = Join-Path $PSScriptRoot 'shot_window.py'
    & python $py2 --proc $s.Proc --out $shot 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Add-Type -AssemblyName System.Windows.Forms, System.Drawing
        $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
        $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
        $bmp.Save($shot, [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose(); $bmp.Dispose()
        Write-Host "    (창을 못 찾아 화면 전체를 찍었다)"
    }
    return $null
}

if ($timedOut) {
    Write-Host "  $TimeoutSec 초를 넘겼습니다 — 모달로 봅니다. 먼저 찍고 앱을 닫습니다." -ForegroundColor Yellow
    try { $modalProc = Read-Modal } catch { Write-Host "  모달 읽기 실패: $($_.Exception.Message)" }
    $modalFound = [bool]$modalProc

    # bridge 전송로는 포토샵을 길로 쓰므로 포토샵도 같이 죽인다. direct 는 제 앱만 죽인다 —
    # 일러스트레이터 잡이 남의 포토샵을 죽이면 안 된다.
    $kill = if ($s.Transport -eq 'bridge') { @($s.Proc, 'Photoshop') } else { @($s.Proc) }
    foreach ($p in $kill) {
        Get-Proc $p | ForEach-Object { taskkill /PID $_.Id /F 2>$null | Out-Null }
    }
    # 앱이 죽어야 COM 호출이 풀린다 — 그래야 이 줄이 바로 끝난다
    Remove-Job $jobHandle -Force -ErrorAction SilentlyContinue
}

# ── 판정 ───────────────────────────────────────────────────────────────
# 반환값은 못 믿는다. 잡이 남긴 **판정 줄**이 있어야 성공이다 (issue 28).
$fresh = Get-ChildItem $labLog -Filter '*.txt' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $started.AddSeconds(-5) }
if ($s.Transport -eq 'bridge') {
    # bridge 는 `_job.txt` 같은 건네주기 파일을 같은 폴더에 둔다 — 그것은 잡의 로그가 아니다.
    $fresh = $fresh | Where-Object { $_.Name -notlike '_*' }
}
$fresh = $fresh | Where-Object { $_.Name -notlike '*_fail.txt' }
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

# 판정 줄을 쓰는 잡은 몇 개 안 된다(09-21 실측: 없는 것 56). 나머지를 전부 실패로 내면 아무것도 못 돌린다.
# 그래서 **시간 제한을 안 넘겼고 잡이 답을 준 옛 잡**은 경고만 하고 통과시킨다 (decision 36).
# 새 잡은 로그에 `판정: …` 한 줄을 쓴다 — 그래야 진짜로 판정된다. 래칫 tests/test_verdict_lines.py.
#
# bridge 의 '답' 은 **OK 로 시작할 때만** 답이다. bridge.jsx 는 실패도 문자열로 돌려준다(FAIL TIMEOUT ·
# FAIL NO_TARGET · 본문 안 JOBERR). 09-22 D 실측: AE 잡이 alert 에 막혀 있는데 BridgeTalk 이 74초에
# 'FAIL TIMEOUT' 을 돌려주자 비어 있지 않다는 이유로 통과(exit 0)했고, 모달도 안 찍혔다.
$answered = $bridgeOut -and $bridgeOut.Result
if ($answered -and $s.Transport -eq 'bridge') {
    $r = [string]$bridgeOut.Result
    $answered = ($r -match '^\s*OK\b') -and ($r -notmatch 'JOBERR')
}
if (-not $timedOut -and $answered) {
    Write-Host ""
    Write-Host "  통과(판정 줄 없음) — 옛 잡이다. 로그에 '판정: …' 한 줄을 넣어 주세요." -ForegroundColor Yellow
    Write-Host "  반환 첫 줄: $(($bridgeOut.Result -split "`n")[0].Trim())"
    exit 0
}

# ── 실패: 사람이 안 봐도 붙일 원자료를 남긴다 ─────────────────────────
if (-not $timedOut) {
    # 시간은 안 넘겼는데 판정도 성공 답도 없다 — 잡이 중간에 죽었거나 bridge 가 FAIL 을 돌려줬다.
    # 앱은 아직 살아 있으니 지금 찍는다.
    try { $modalProc = Read-Modal } catch { Write-Host "  모달 읽기 실패: $($_.Exception.Message)" }
    $modalFound = [bool]$modalProc
    if ($modalProc) {
        # 모달이 떠 있으면 그 앱은 막혀 있다. 두면 다음 잡도 같은 창에 걸린다 — 찍었으니 닫는다.
        Write-Host "  $modalProc 에 모달이 떠 있습니다 — 찍었고, 앱을 닫습니다." -ForegroundColor Yellow
        Get-Proc $modalProc | ForEach-Object { taskkill /PID $_.Id /F 2>$null | Out-Null }
        if ($s.Transport -eq 'bridge' -and $modalProc -ne 'Photoshop') {
            Get-Proc 'Photoshop' | ForEach-Object { taskkill /PID $_.Id /F 2>$null | Out-Null }   # 시간 초과 경로와 같게
        }
    }
}

# 모달 문구 분류 — 아는 문구면 표대로, 아니면 '모름'. **닫지는 않는다** (총괄 2026-09-21, 문 0.8).
$classLine = $null
if (Test-Path $modalJson) {
    try {
        $pyArgs = @((Join-Path $PSScriptRoot 'modal_class.py'), '--from', $modalJson, '--json', $classJson)
        if ($NoJev) { $pyArgs += '--no-jev' }
        & python @pyArgs 2>&1 | ForEach-Object { Write-Host "    modal_class: $_" }
        if (Test-Path $classJson) {
            $c = Get-Content $classJson -Raw -Encoding UTF8 | ConvertFrom-Json
            $classLine = "모달 분류: $($c.처리)  ($($c.근거))"
            Write-Host "  $classLine" -ForegroundColor Yellow
            foreach ($h in $c.힌트) { Write-Host "  힌트: $h" -ForegroundColor Yellow }
        }
    } catch { Write-Host "  문구 분류 실패: $($_.Exception.Message)" }
}

$lines = @()
$lines += "잡: $Job ($App) · $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) · ${elapsed}s"
if ($timedOut) { $lines += "원인 후보: 시간 제한 $TimeoutSec 초 초과 (모달로 보고 앱을 죽였다)" }
else           { $lines += "원인 후보: 판정 줄도 성공 답(OK)도 없다 (잡이 끝까지 못 갔거나 bridge 가 FAIL 을 돌려줬다)" }
$lines += "모달 창: $(if ($modalFound) { "찾았다($modalProc, 찍고 앱을 닫았다) — " + $shot } else { '못 찾았다 (앱 창이나 화면 전체를 찍었다) — ' + $shot })"
if ($classLine) { $lines += $classLine }
if (Test-Path $classJson) {
    $c = Get-Content $classJson -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($c.문구) { $lines += "모달 문구: $($c.문구)" }
    foreach ($h in $c.힌트) { $lines += "힌트: $h" }
}
if ($bridgeOut) { $lines += "반환: $($bridgeOut.Result)" }
foreach ($f in $fresh) {
    $lines += ""
    $lines += "---- $($f.Name) 마지막 30줄 ----"
    $lines += (Get-Content $f.FullName -Encoding UTF8 -Tail 30)
}
[System.IO.File]::WriteAllLines($failPath, $lines, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "  화면: $shot"

Write-Host ""
Write-Host "  실패 — $failPath 를 보세요" -ForegroundColor Red
exit 1
