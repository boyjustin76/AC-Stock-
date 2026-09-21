<#
    포토샵 잡을 공용 실행기로 넘긴다 (next_step 46 · 2단계).

        .\tools\photoshop\run.ps1 build_thumb
        .\tools\photoshop\run.ps1 dump_episodes
        .\tools\photoshop\run.ps1 dump_layer_fx
        .\tools\photoshop\run.ps1 dump_text_runs

    부르는 법은 그대로다. 안에서 하는 일이 늘었다 — 시간 제한, 판정 줄로 성공 정하기,
    실패하면 **모달을 죽이기 전에 찍고 문구를 분류**해서 <out>/<잡>_fail.txt 에 남긴다.
    내용은 tools/_com/run.ps1 하나에 모여 있다(앱 넷이 같은 것을 쓴다).

    포토샵이 안 떠 있으면 알아서 뜬다. 템플릿이 180MB 라 첫 실행은 1~2분 걸린다.
    두 번째부터는 문서가 열린 채로 남아 있어 빠르다 — 그래서 **열린 문서 검사를 하지 않는다**
    (일러스트레이터는 반대다). 설정은 tools/photoshop/config.json.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('build_thumb', 'dump_episodes', 'dump_layer_fx', 'dump_text_runs')]
    [string]$Script,
    <#  기본 30분. 180MB 템플릿을 여는 데만 1~2분이고 build_thumb 은 안 하나에 1~2분이다.
        짧은 dump 잡에는 손으로 짧게 준다 (-TimeoutSec 300). #>
    [int]$TimeoutSec = 1800,
    [switch]$NoJev                  # 모달 문구 분류에서 표만 본다
)

$ErrorActionPreference = 'Stop'
$com = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) '_com\run.ps1'
& $com -App photoshop -Job $Script -TimeoutSec $TimeoutSec -NoJev:$NoJev
exit $LASTEXITCODE
