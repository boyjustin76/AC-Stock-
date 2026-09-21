#Requires -Version 5.1
<#
    프리미어를 BridgeTalk 으로 조종한다.

        .\tools\premiere\run.ps1 -Job probe

    알맹이는 `tools/_com/run.ps1` 로 옮겼다 (next_step 46). 여기는 부르는 자리만 남긴다.

    프리미어에는 Photoshop.Application 에 해당하는 COM 자동화 ProgID 가 없다(레지스트리 실측).
    그래서 검증된 포토샵 COM 드라이버를 전송로로 재사용한다:

        PowerShell → Photoshop.Application(COM) → bridge.jsx → BridgeTalk → premierepro-26.0

    프리미어가 안 떠 있으면 BridgeTalk 이 띄운다. 첫 실행은 사람이 화면을 보는 상태에서 해라
    (미디어 연결 대화상자가 뜬다 — 프리셋 미디어는 D:\ 를 가리키는데 이 PC 는 G:\ 다).

    설정은 tools/premiere/config.json, 잡은 tools/premiere/jobs/<이름>.jsx.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Job,
    [int]$TimeoutSec = 300,
    [switch]$SkipPreflight
)

$common = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) '_com\run.ps1'
& $common -App premiere -Job $Job -TimeoutSec $TimeoutSec -SkipPreflight:$SkipPreflight
exit $LASTEXITCODE
