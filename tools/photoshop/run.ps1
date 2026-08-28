<#
    포토샵을 COM 으로 띄워 같은 폴더의 .jsx 를 실행한다.

        .\tools\photoshop\run.ps1 build_thumb
        .\tools\photoshop\run.ps1 dump_episodes
        .\tools\photoshop\run.ps1 dump_layer_fx
        .\tools\photoshop\run.ps1 dump_text_runs

    포토샵이 안 떠 있으면 알아서 뜬다. 템플릿이 180MB 라 첫 실행은 1~2분 걸린다.
    두 번째부터는 문서가 열린 채로 남아 있어 빠르다.

    설정은 tools/photoshop/config.json 에서 읽는다.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('build_thumb', 'dump_episodes', 'dump_layer_fx', 'dump_text_runs')]
    [string]$Script
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$jsx  = Join-Path $here "$Script.jsx"
if (-not (Test-Path $jsx)) { throw "스크립트가 없습니다: $jsx" }

$cfgPath = Join-Path $here 'config.json'
if (-not (Test-Path $cfgPath)) { throw "config.json 이 없습니다: $cfgPath" }
$cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not (Test-Path $cfg.template)) {
    throw "템플릿을 찾을 수 없습니다: $($cfg.template)`n   config.json 의 template 경로를 확인하세요. 원본 .psd 는 저장소에 없습니다(180MB)."
}

Write-Host "  포토샵 연결 중..."
$ps = New-Object -ComObject Photoshop.Application
Write-Host "  Photoshop $($ps.Version)"
$ps.DisplayDialogs = 3      # psDisplayNoDialogs

Write-Host "  실행: $Script.jsx"
$result = $ps.DoJavaScriptFile($jsx)
Write-Host "  결과: $result"

# jsx 가 남긴 로그를 그대로 보여 준다
foreach ($name in 'build_log.txt', 'layer_fx.txt', 'ref_tree.txt', 'text_runs.txt') {
    $log = Join-Path $cfg.outDir $name
    if ((Test-Path $log) -and ((Get-Item $log).LastWriteTime -gt (Get-Date).AddMinutes(-5))) {
        Write-Host ""
        Write-Host "  ---- $name ----"
        Get-Content $log -Encoding UTF8 | ForEach-Object { "    $_" }
    }
}
