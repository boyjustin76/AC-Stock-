#Requires -Version 5.1
<#
    애프터이펙트를 BridgeTalk 으로 조종한다.

        .\tools\ae\run.ps1 -Job a1_smoke

    알맹이는 `tools/_com/run.ps1` 로 옮겼다 (next_step 46). 여기는 부르는 자리만 남긴다.
    전송로는 그대로다:

        PowerShell → Photoshop.Application(COM) → bridge.jsx → BridgeTalk → aftereffects-**

    공용 실행기가 대신 봐 주는 것 — **프리미어가 떠 있으면 중단**(TRAPS 7),
    시간 제한을 넘기면 앱을 죽이고, 반환값이 아니라 **판정 줄**로 성공을 정하고,
    실패하면 화면 한 장과 로그 30줄을 `<작업실>/log/<잡>_fail.txt` 로 남긴다.

    타깃 이름은 config.json 에 비워 두면 bridge.jsx 가 getSpecifier 로 실측한다.
    AE 가 안 떠 있으면 BridgeTalk 이 띄운다. **첫 실행은 사람이 화면을 보는 상태에서 해라** —
    홈 화면·로그인·업데이트 대화상자가 뜨면 모달이고, 모달은 세션을 조용히 죽인다(매뉴얼 §6).

    설정은 tools/ae/config.json, 잡은 tools/ae/jobs/<이름>.jsx.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Job,
    [int]$TimeoutSec = 300,
    [switch]$SkipPreflight
)

$common = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) '_com\run.ps1'
& $common -App ae -Job $Job -TimeoutSec $TimeoutSec -SkipPreflight:$SkipPreflight
exit $LASTEXITCODE
