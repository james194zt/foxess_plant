$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$www = (Join-Path $PSScriptRoot "..\custom_components\foxess_plant\www" | Resolve-Path).Path
$canvasW = 1024
$canvasH = 1017
$homeThemes = @("day_light", "day_dark", "night_light", "night_dark")
$overlayThemes = @("day_light", "night_dark")
$matteLum = 28

$boxes = @{
    pv  = @{ left = 0.388; top = 0.342; width = 0.448; height = 0.242 }
    aio = @{ left = 0.312; top = 0.622; width = 0.136; height = 0.222 }
}

function Invoke-DecodeWebp {
    $need = $false
    foreach ($theme in $overlayThemes) {
        if (-not (Test-Path (Join-Path $www "flow_pv_${theme}_sprite.png"))) { $need = $true }
    }
    if (-not $need) { return }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    wsl bash -c "sed -i 's/\r$//' /mnt/c/Users/James/Documents/repo/foxess_plant/tools/decode_flow_webp.sh 2>/dev/null; bash /mnt/c/Users/James/Documents/repo/foxess_plant/tools/decode_flow_webp.sh" 2>&1 | Out-Host
    $ErrorActionPreference = $prevEap
}

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

function Bake-OverlayScene([string]$layer, [string]$theme) {
    $box = $boxes[$layer]
    $left = [int][Math]::Floor($box.left * $canvasW)
    $top = [int][Math]::Floor($box.top * $canvasH)
    $bw = [int][Math]::Round($box.width * $canvasW)
    $bh = [int][Math]::Round($box.height * $canvasH)
    $spriteName = if ($layer -eq "pv") { "flow_pv" } else { "flow_aio_812" }
    $spritePath = Join-Path $www "${spriteName}_${theme}_sprite.png"
    if (-not (Test-Path $spritePath)) { throw "Missing $spritePath (run decode_flow_webp.sh)" }
    $outPath = Join-Path $www "flow_${layer}_scene_$theme.png"

    $src = [System.Drawing.Bitmap]::FromFile($spritePath)
    $fitted = New-Object System.Drawing.Bitmap $bw, $bh, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $gs = [System.Drawing.Graphics]::FromImage($fitted)
    $gs.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $gs.DrawImage($src, 0, 0, $bw, $bh)
    $gs.Dispose()
    $src.Dispose()
    Remove-BlackMatte $fitted

    $canvas = New-Object System.Drawing.Bitmap $canvasW, $canvasH, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $gc = [System.Drawing.Graphics]::FromImage($canvas)
    $gc.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $gc.DrawImage($fitted, $left, $top, $bw, $bh)
    $gc.Dispose()
    $fitted.Dispose()
    $tmp = "$outPath.tmp"
    $canvas.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png)
    $canvas.Dispose()
    if (Test-Path $outPath) { Remove-Item -Force $outPath }
    Move-Item -Force $tmp $outPath
    Write-Host "wrote flow_${layer}_scene_$theme.png"
}

Invoke-DecodeWebp

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
    Bake-OverlayScene "pv" $theme
    Bake-OverlayScene "aio" $theme
}
