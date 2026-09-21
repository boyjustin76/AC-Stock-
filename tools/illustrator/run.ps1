<#
    일러스트레이터 잡을 공용 실행기로 넘긴다 (next_step 46 · 2단계).

        .\tools\illustrator\run.ps1 dump_ai
        .\tools\illustrator\run.ps1 build_live
        .\tools\illustrator\run.ps1 build_live -Force            # 남의 문서가 열려 있어도
        .\tools\illustrator\run.ps1 dump_ai -TimeoutSec 300      # 짧은 잡은 짧게 걸어 둔다

    부르는 법은 그대로다. 안에서 하는 일이 늘었다 — 시간 제한, 판정 줄로 성공 정하기,
    실패하면 **모달을 죽이기 전에 찍고 문구를 분류**해서 <결과폴더>/<잡>_fail.txt 에 남긴다.
    내용은 tools/_com/run.ps1 하나에 모여 있다(앱 넷이 같은 것을 쓴다).

    경로는 박지 않는다 (labdir.ps1). jsx 에는 _paths.json 으로 넘긴다 — 공용 실행기의 Prep-Illustrator.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Script,
    [switch]$Force,                 # 남의 문서가 열려 있어도 진행
    <#  기본 30분. build_live 는 24.7MB 원본을 열고 아트보드 열 장을 짓는 잡이라 **10분 안팎**이고
        (매뉴얼 log/LIVE-SCREEN-MANUAL.md), export_obs 는 8000x4500 이라 더 걸린다.
        600 으로 뒀더니 정상 빌드가 제한에 걸렸다(2026-09-21 실측) — 짧은 잡에는 손으로 짧게 준다. #>
    [int]$TimeoutSec = 1800,
    [switch]$NoJev                  # 모달 문구 분류에서 표만 본다
)

$ErrorActionPreference = 'Stop'
$com = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) '_com\run.ps1'
& $com -App illustrator -Job $Script -TimeoutSec $TimeoutSec -SkipDocGuard:$Force -NoJev:$NoJev
exit $LASTEXITCODE
