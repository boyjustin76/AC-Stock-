<#  AE 작업실 폴더를 찾아준다 (labdir.py 의 PowerShell 판).
    쓰는 법:  . "$PSScriptRoot\labdir.ps1"  ;  $lab = Get-LabDir
    찾는 순서: AELAB_DIR 환경변수 → config.json 의 labDir → 위로 올라가며 폴더 이름 찾기. 못 찾으면 멈춘다 (2026-09-17 — 옛 자리 C:\aelab 은 09-16 에 없앴다)
#>
function Get-LabDir {
    $here   = $PSScriptRoot
    $folder = '02_AE작업실_aelab'

    if ($env:AELAB_DIR -and (Test-Path $env:AELAB_DIR)) { return (Resolve-Path $env:AELAB_DIR).Path }

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
        $c = Join-Path $d $folder
        if (Test-Path $c) { return (Resolve-Path $c).Path }
        $nd = Split-Path $d -Parent
        if (-not $nd -or $nd -eq $d) { break }
        $d = $nd
    }

    throw "AE 작업실 폴더 $folder 를 못 찾았다 — 환경변수 AELAB_DIR 을 주거나 config.json 의 labDir 에 적는다 (찾기 시작: $here)"
}
