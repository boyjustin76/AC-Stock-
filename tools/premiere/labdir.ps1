<#  프리미어 실험실 폴더를 찾아준다 (tools/ae/labdir.ps1 과 같은 규칙).
    쓰는 법:  . "$PSScriptRoot\labdir.ps1"  ;  $lab = Get-PproLabDir
#>
function Get-PproLabDir {
    $here   = $PSScriptRoot
    $names  = @('06_실험실\pprolab', 'pprolab')
    $legacy = 'C:\pprolab'

    if ($env:PPROLAB_DIR -and (Test-Path $env:PPROLAB_DIR)) { return (Resolve-Path $env:PPROLAB_DIR).Path }

    $cfgPath = Join-Path $here 'config.json'
    if (Test-Path $cfgPath) {
        try {
            $v = (Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json).labDir
            if ($v) {
                if (-not [System.IO.Path]::IsPathRooted($v)) { $v = Join-Path $here $v }
                if (Test-Path $v) { return (Resolve-Path $v).Path }
            }
        } catch { }
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

    $d = $here
    for ($i = 0; $i -lt 4; $i++) { $nd = Split-Path $d -Parent; if (-not $nd -or $nd -eq $d) { break }; $d = $nd }
    return (Join-Path $d $names[0])
}
