<#  썸네일 작업실 폴더를 찾아준다 (_labdir.jsx 의 PowerShell 판).
    쓰는 법:  . "$PSScriptRoot\labdir.ps1"  ;  $lab = Get-CmgWorkDir $cfg.labDir
    찾는 순서: CMGWORK_DIR 환경변수 → config.json 의 labDir → 위로 올라가며
               '06_실험실\cmgwork' → 'cmgwork' → 옛 자리 C:\cmgwork
    tools/ae/labdir.ps1 과 같은 규칙이다.
#>
function Get-CmgWorkDir {
    param([string]$CfgLabDir)

    $here   = $PSScriptRoot
    $names  = @('06_실험실\cmgwork', 'cmgwork')
    $legacy = 'C:\cmgwork'

    if ($env:CMGWORK_DIR -and (Test-Path $env:CMGWORK_DIR)) { return (Resolve-Path $env:CMGWORK_DIR).Path }

    if ($CfgLabDir) {
        $v = $CfgLabDir
        if (-not [System.IO.Path]::IsPathRooted($v)) { $v = Join-Path $here $v }
        if (Test-Path $v) { return (Resolve-Path $v).Path }
    }

    $d = $here
    for ($i = 0; $i -lt 8; $i++) {
        foreach ($n in $names) {
            $c = Join-Path $d $n
            if (Test-Path $c) { return (Resolve-Path $c).Path }
        }
        $nd = Split-Path $d -Parent
        if (-not $nd -or $nd -eq $d) { break }
        $d = $nd
    }

    if (Test-Path $legacy) { return $legacy }

    # 아직 없으면 만들 자리를 돌려준다 (통합 폴더 안)
    $d = $here
    for ($i = 0; $i -lt 4; $i++) {
        $nd = Split-Path $d -Parent
        if (-not $nd -or $nd -eq $d) { break }
        $d = $nd
    }
    return (Join-Path $d $names[0])
}

<#  config 의 상대경로를 작업실 기준 절대경로로 푼다. 절대경로면 그대로 둔다. #>
function Resolve-UnderLab {
    param([string]$Value, [string]$Lab)
    if (-not $Value) { return $Value }
    if ([System.IO.Path]::IsPathRooted($Value)) { return $Value }
    if ($Value -eq '.') { return $Lab }
    return (Join-Path $Lab $Value)
}
