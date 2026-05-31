$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$www = (Join-Path $PSScriptRoot "..\custom_components\foxess_plant\www" | Resolve-Path).Path
$canvasW = 1024
$canvasH = 1017
$bgThemes = @("day_light", "day_dark", "night_light", "night_dark")

function Get-OverlayTheme([string]$bgTheme) {
    if ($bgTheme.StartsWith("day_")) { return "day_light" }
    return "night_dark"
}

function Key-EdgeBlack([System.Drawing.Bitmap]$bmp) {
    $w = $bmp.Width; $h = $bmp.Height
    $seen = New-Object 'bool[]' ($w * $h)
    $q = [System.Collections.Generic.Queue[int]]::new()
    function IsBlack([int]$x,[int]$y) {
        $c = $bmp.GetPixel($x,$y)
        return ($c.A -gt 200 -and $c.R -eq 0 -and $c.G -eq 0 -and $c.B -eq 0)
    }
    function Push([int]$x,[int]$y) {
        $i = $y * $w + $x
        if (-not $seen[$i] -and (IsBlack $x $y)) { $seen[$i] = $true; $q.Enqueue($i) }
    }
    for ($x=0; $x -lt $w; $x++) { Push $x 0; Push $x ($h-1) }
    for ($y=0; $y -lt $h; $y++) { Push 0 $y; Push ($w-1) $y }
    $clear = [System.Drawing.Color]::FromArgb(0,0,0,0)
    while ($q.Count -gt 0) {
        $i = $q.Dequeue(); $x = $i % $w; $y = [int][Math]::Floor($i / $w)
        $bmp.SetPixel($x,$y,$clear)
        if ($x -gt 0) { Push ($x-1) $y }
        if ($x -lt $w-1) { Push ($x+1) $y }
        if ($y -gt 0) { Push $x ($y-1) }
        if ($y -lt $h-1) { Push $x ($y+1) }
    }
}

function Load-HomeLayer([string]$theme) {
    $path = Join-Path $www "flow_home_$theme.png"
    $src = [System.Drawing.Bitmap]::FromFile($path)
    $bmp = New-Object System.Drawing.Bitmap $canvasW, $canvasH, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($src, 0, 0, $canvasW, $canvasH)
    $g.Dispose(); $src.Dispose()
    Key-EdgeBlack $bmp
    return $bmp
}

$homeLayers = @{}
foreach ($t in @("day_light", "night_dark")) {
    $homeLayers[$t] = Load-HomeLayer $t
    $out = Join-Path $www "flow_home_$t.png"
    $homeLayers[$t].Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Host "keyed flow_home_$t.png"
}

foreach ($theme in $bgThemes) {
    $srcPath = Join-Path $www "flow_home_bg_$theme.png"
    $outPath = Join-Path $www "flow_home_bg_scene_$theme.png"
    $overlay = Get-OverlayTheme $theme

    $src = [System.Drawing.Image]::FromFile($srcPath)
    try {
        $scale = [Math]::Max($canvasW / $src.Width, $canvasH / $src.Height)
        $nw = [int][Math]::Round($src.Width * $scale)
        $nh = [int][Math]::Round($src.Height * $scale)
        $x = [int][Math]::Floor(($canvasW - $nw) / 2)

        $canvas = New-Object System.Drawing.Bitmap $canvasW, $canvasH, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $g = [System.Drawing.Graphics]::FromImage($canvas)
            try {
                $g.Clear([System.Drawing.Color]::Black)
                $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
                $g.DrawImage($src, $x, 0, $nw, $nh)
                $g.DrawImage($homeLayers[$overlay], 0, 0, $canvasW, $canvasH)
            } finally { $g.Dispose() }
            $canvas.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
            Write-Host "wrote flow_home_bg_scene_$theme.png"
        } finally { $canvas.Dispose() }
    } finally { $src.Dispose() }
}

foreach ($bmp in $homeLayers.Values) { $bmp.Dispose() }
