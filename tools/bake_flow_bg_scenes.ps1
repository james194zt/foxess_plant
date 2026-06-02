$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$www = Join-Path $PSScriptRoot "..\custom_components\foxess_plant\www" | Resolve-Path
$canvasW = 1024
$canvasH = 1017
$themes = @("day_light", "day_dark", "night_light", "night_dark")

foreach ($theme in $themes) {
    $srcPath = Join-Path $www "flow_home_bg_$theme.png"
    $outPath = Join-Path $www "flow_home_bg_scene_$theme.png"

    $src = [System.Drawing.Image]::FromFile($srcPath)
    try {
        $scale = [Math]::Max($canvasW / $src.Width, $canvasH / $src.Height)
        $nw = [int][Math]::Round($src.Width * $scale)
        $nh = [int][Math]::Round($src.Height * $scale)
        $x = [int][Math]::Floor(($canvasW - $nw) / 2)

        $canvas = New-Object System.Drawing.Bitmap $canvasW, $canvasH
        try {
            $g = [System.Drawing.Graphics]::FromImage($canvas)
            try {
                $g.Clear([System.Drawing.Color]::Black)
                $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
                $g.DrawImage($src, $x, 0, $nw, $nh)
            } finally {
                $g.Dispose()
            }
            $canvas.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
            Write-Host "wrote $outPath"
        } finally {
            $canvas.Dispose()
        }
    } finally {
        $src.Dispose()
    }
}
