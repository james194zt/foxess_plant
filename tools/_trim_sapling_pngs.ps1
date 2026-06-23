#!/usr/bin/env pwsh
# Trim transparent margins from sapling PNGs so soil bases align when scaled.
Add-Type -AssemblyName System.Drawing

$threshold = 10
$pad = 8
$files = @(
    "$PSScriptRoot/../custom_components/foxess_plant/www/octopus_greener_sapling.png",
    "$PSScriptRoot/../custom_components/foxess_plant/www/octopus_greener_sapling_green.png"
)

foreach ($path in $files) {
    $path = (Resolve-Path $path).Path
    $bmp = [System.Drawing.Bitmap]::FromFile($path)
    $minX = $bmp.Width; $minY = $bmp.Height; $maxX = 0; $maxY = 0
    for ($y = 0; $y -lt $bmp.Height; $y++) {
        for ($x = 0; $x -lt $bmp.Width; $x++) {
            if ($bmp.GetPixel($x, $y).A -gt $threshold) {
                if ($x -lt $minX) { $minX = $x }
                if ($y -lt $minY) { $minY = $y }
                if ($x -gt $maxX) { $maxX = $x }
                if ($y -gt $maxY) { $maxY = $y }
            }
        }
    }
    $cropX = [Math]::Max(0, $minX - $pad)
    $cropY = [Math]::Max(0, $minY - $pad)
    $cropW = [Math]::Min($bmp.Width - $cropX, ($maxX - $minX + 1) + ($pad * 2))
    $cropH = [Math]::Min($bmp.Height - $cropY, ($maxY - $minY + 1) + ($pad * 2))
    $rect = New-Object System.Drawing.Rectangle $cropX, $cropY, $cropW, $cropH
    $cropped = $bmp.Clone($rect, $bmp.PixelFormat)
    $bmp.Dispose()
    $cropped.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $cropped.Dispose()
    Write-Output "Trimmed $(Split-Path $path -Leaf) -> ${cropW}x${cropH}"
}
