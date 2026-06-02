$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$www = (Join-Path $PSScriptRoot "..\custom_components\foxess_plant\www" | Resolve-Path).Path
$canvasW = 1024
$canvasH = 1017
$homeThemes = @("day_light", "day_dark", "night_light", "night_dark")
$overlayThemes = @("day_light", "night_dark")
# Only near-black matte pixels; keep dark roof tiles (typically max channel > 32).
$matteLum = 28

$boxes = @{
    aio = @{ left = 0.312; top = 0.622; width = 0.136; height = 0.222 }
}
# Right roof slope quad on 1024x1017 (TL, TR, BL for GDI+ DrawImage).
$pvRoofQuad = @(
    @{ x = 422; y = 410 }
    @{ x = 706; y = 368 }
    @{ x = 438; y = 558 }
)

function Remove-BlackMatte([System.Drawing.Bitmap]$bmp) {
    $rect = New-Object System.Drawing.Rectangle 0, 0, $bmp.Width, $bmp.Height
    $data = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadWrite, $bmp.PixelFormat)
    $bytes = New-Object byte[] ($data.Stride * $data.Height)
    [System.Runtime.InteropServices.Marshal]::Copy($data.Scan0, $bytes, 0, $bytes.Length)
    $w = $bmp.Width
    $h = $bmp.Height
    for ($y = 0; $y -lt $h; $y++) {
        for ($x = 0; $x -lt $w; $x++) {
            $i = $y * $data.Stride + $x * 4
            $b = $bytes[$i]
            $g = $bytes[$i + 1]
            $r = $bytes[$i + 2]
            $a = $bytes[$i + 3]
            if ($a -eq 0) { continue }
            $na = [Math]::Max($r, [Math]::Max($g, $b))
            if ($na -gt $matteLum) { continue }
            if ($na -eq 0) {
                $bytes[$i] = 0
                $bytes[$i + 1] = 0
                $bytes[$i + 2] = 0
                $bytes[$i + 3] = 0
            } else {
                $bytes[$i + 3] = $na
            }
        }
    }
    [System.Runtime.InteropServices.Marshal]::Copy($bytes, 0, $data.Scan0, $bytes.Length)
    $bmp.UnlockBits($data)
}

function Load-HomeLayer([string]$theme) {
    $path = Join-Path $www "flow_home_$theme.png"
    if (-not (Test-Path $path)) { throw "Missing $path" }
    $src = [System.Drawing.Bitmap]::FromFile($path)
    $bmp = New-Object System.Drawing.Bitmap $canvasW, $canvasH, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    if ($src.Width -eq $canvasW -and $src.Height -eq $canvasH) {
        $g.DrawImage($src, 0, 0)
    } else {
        $g.DrawImage($src, 0, 0, $canvasW, $canvasH)
    }
    $g.Dispose()
    $src.Dispose()
    Remove-BlackMatte $bmp
    return $bmp
}

function Get-SpriteCrop([System.Drawing.Bitmap]$bmp) {
    $minX = $bmp.Width; $minY = $bmp.Height; $maxX = 0; $maxY = 0
    for ($y = 0; $y -lt $bmp.Height; $y++) {
        for ($x = 0; $x -lt $bmp.Width; $x++) {
            if ($bmp.GetPixel($x, $y).A -gt 24) {
                if ($x -lt $minX) { $minX = $x }
                if ($y -lt $minY) { $minY = $y }
                if ($x -gt $maxX) { $maxX = $x }
                if ($y -gt $maxY) { $maxY = $y }
            }
        }
    }
    if ($maxX -le $minX) { throw "No opaque pixels in sprite source" }
    $w = $maxX - $minX + 1
    $h = $maxY - $minY + 1
    $crop = New-Object System.Drawing.Bitmap $w, $h, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($crop)
    $g.DrawImage($bmp, (New-Object System.Drawing.Rectangle 0, 0, $w, $h),
        (New-Object System.Drawing.Rectangle $minX, $minY, $w, $h),
        [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()
    return $crop
}

function Draw-SpriteOnRoof([System.Drawing.Graphics]$g, [System.Drawing.Bitmap]$sprite, $quad) {
    $dest = [System.Drawing.Point[]]@(
        [System.Drawing.Point]::new([int]$quad[0].x, [int]$quad[0].y),
        [System.Drawing.Point]::new([int]$quad[1].x, [int]$quad[1].y),
        [System.Drawing.Point]::new([int]$quad[2].x, [int]$quad[2].y)
    )
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.DrawImage($sprite, $dest)
}

function Bake-PvScene([string]$theme) {
    $outPath = Join-Path $www "flow_pv_scene_$theme.png"
    if (-not (Test-Path $outPath)) { throw "Missing $outPath" }
    $legacy = [System.Drawing.Bitmap]::FromFile($outPath)
    $sprite = Get-SpriteCrop $legacy
    $legacy.Dispose()
    Remove-BlackMatte $sprite
    $canvas = New-Object System.Drawing.Bitmap $canvasW, $canvasH, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($canvas)
    Draw-SpriteOnRoof $g $sprite $pvRoofQuad
    $g.Dispose()
    $sprite.Dispose()
    $tmp = "$outPath.tmp"
    $canvas.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png)
    $canvas.Dispose()
    if (Test-Path $outPath) { Remove-Item -Force $outPath }
    Move-Item -Force $tmp $outPath
    Write-Host "wrote flow_pv_scene_$theme.png (roof perspective)"
}

function Bake-AioScene([string]$theme) {
    $box = $boxes.aio
    $left = [int][Math]::Floor($box.left * $canvasW)
    $top = [int][Math]::Floor($box.top * $canvasH)
    $bw = [int][Math]::Round($box.width * $canvasW)
    $bh = [int][Math]::Round($box.height * $canvasH)
    $srcPath = Join-Path $www "flow_aio_812_$theme.png"
    $outPath = Join-Path $www "flow_aio_scene_$theme.png"
    if (-not (Test-Path $outPath)) { throw "Missing $outPath" }
    $scene = [System.Drawing.Bitmap]::FromFile($outPath)
    Remove-BlackMatte $scene
    $tmp = "$outPath.tmp"
    $scene.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png)
    $scene.Dispose()
    if (Test-Path $outPath) { Remove-Item -Force $outPath }
    Move-Item -Force $tmp $outPath
    Write-Host "matte-removed flow_aio_scene_$theme.png"
}

$homeLayers = @{}
foreach ($t in $homeThemes) {
    $homeLayers[$t] = Load-HomeLayer $t
    Write-Host "matte-removed flow_home_$t.png"
}

foreach ($theme in $homeThemes) {
    $srcPath = Join-Path $www "flow_home_bg_$theme.png"
    $outPath = Join-Path $www "flow_home_bg_scene_$theme.png"
    if (-not (Test-Path $srcPath)) { throw "Missing $srcPath" }

    $src = [System.Drawing.Image]::FromFile($srcPath)
    try {
        $scale = [Math]::Max($canvasW / $src.Width, $canvasH / $src.Height)
        $nw = [int][Math]::Round($src.Width * $scale)
        $nh = [int][Math]::Round($src.Height * $scale)
        $x = [int][Math]::Floor(($canvasW - $nw) / 2)
        $y = $canvasH - $nh

        $canvas = New-Object System.Drawing.Bitmap $canvasW, $canvasH, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $g = [System.Drawing.Graphics]::FromImage($canvas)
            try {
                $g.Clear([System.Drawing.Color]::Black)
                $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
                $g.DrawImage($src, $x, $y, $nw, $nh)
                $g.DrawImage($homeLayers[$theme], 0, 0, $canvasW, $canvasH)
            } finally { $g.Dispose() }

            $flat = New-Object System.Drawing.Bitmap $canvasW, $canvasH, ([System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
            $gf = [System.Drawing.Graphics]::FromImage($flat)
            $gf.DrawImage($canvas, 0, 0)
            $gf.Dispose()
            $flat.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
            $flat.Dispose()
            Write-Host "wrote flow_home_bg_scene_$theme.png"
        } finally { $canvas.Dispose() }
    } finally { $src.Dispose() }
}

foreach ($bmp in $homeLayers.Values) { $bmp.Dispose() }

foreach ($theme in $overlayThemes) {
    Bake-PvScene $theme
    Bake-AioScene $theme
}
