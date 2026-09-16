<#  라이브화면 작업에 쓰는 두 폴더를 스스로 찾는다.
    tools/photoshop/labdir.ps1 · tools/ae/labdir.ps1 과 같은 규칙이다 — 경로를 박지 않는다.

    쓰는 법:
        . "$PSScriptRoot\labdir.ps1"
        $lab = Get-LiveDir $cfg.labDir          # 참고자료(원본 .ai·프레임 png)가 있는 곳
        $out = Resolve-UnderLab $cfg.outDir $lab

    찾는 순서: LIVEFRAME_DIR 환경변수 → config 값 → 위로 8단계 올라가며 이름 찾기
#>

<#  자기 위치에서 위로 올라가며 이름(여러 개 중 먼저 걸리는 것)을 찾는다.
    이름에 '/' 가 들어가면 그 하위 경로까지 한 번에 본다.  #>
function Find-UpFolder {
    param([string]$Start, [string[]]$Names, [int]$Depth = 8)
    $d = $Start
    for ($i = 0; $i -lt $Depth; $i++) {
        foreach ($n in $Names) {
            $c = Join-Path $d $n
            if (Test-Path $c) { return (Resolve-Path $c).Path }
        }
        $nd = Split-Path $d -Parent
        if (-not $nd -or $nd -eq $d) { break }
        $d = $nd
    }
    return $null
}

function Get-LiveDir {
    param([string]$CfgDir)

    $here  = $PSScriptRoot
    $names = @('Claude\라이브화면 프레임', '라이브화면 프레임')

    if ($env:LIVEFRAME_DIR -and (Test-Path $env:LIVEFRAME_DIR)) { return (Resolve-Path $env:LIVEFRAME_DIR).Path }

    if ($CfgDir) {
        $v = $CfgDir
        if (-not [System.IO.Path]::IsPathRooted($v)) { $v = Join-Path $here $v }
        if (Test-Path $v) { return (Resolve-Path $v).Path }
    }

    $hit = Find-UpFolder -Start $here -Names $names
    if ($hit) { return $hit }
    throw "라이브화면 참고자료 폴더를 못 찾았습니다. LIVEFRAME_DIR 환경변수나 config.json 의 labDir 을 주세요."
}

<#  납품 폴더 — 차트명가NEW 꾸러미 안. 없으면 만든다. #>
function Get-DeliverDir {
    param([string]$CfgDir)

    $here = $PSScriptRoot
    if ($CfgDir -and [System.IO.Path]::IsPathRooted($CfgDir) -and (Test-Path $CfgDir)) { return (Resolve-Path $CfgDir).Path }

    $pack = Find-UpFolder -Start $here -Names @('01_납품_차트명가NEW')
    if (-not $pack) { throw "납품 폴더(01_납품_차트명가NEW)를 못 찾았습니다." }

    $sub = if ($CfgDir) { $CfgDir } else { '라이브화면' }
    $dir = Join-Path $pack $sub
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    return (Resolve-Path $dir).Path
}

<#  값이 상대경로면 기준 폴더 아래로 푼다. 절대경로면 그대로 둔다. #>
function Resolve-UnderLab {
    param([string]$Value, [string]$Lab)
    if (-not $Value) { return $Lab }
    if ([System.IO.Path]::IsPathRooted($Value)) { return $Value }
    if ($Value -eq '.') { return $Lab }
    return (Join-Path $Lab $Value)
}
