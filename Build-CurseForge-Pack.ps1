# Creates a personal-use CurseForge import ZIP on Windows by downloading the
# original files from their official Modrinth CDNs. No mod JARs are hosted here.
param(
    [string]$OutputPath = "$HOME\Downloads\Galax71_ExtremeFPS_26.2_CurseForge.zip"
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$lockPath = Join-Path $base 'resolved-mods.json'
$manifestPath = Join-Path $base 'manifest.json'
if (!(Test-Path $lockPath) -or !(Test-Path $manifestPath)) {
    throw 'Extract the complete CurseForge_Personal_Installer_26.2.zip first, then run this script.'
}
$mods = @(foreach ($item in (Get-Content $lockPath -Raw | ConvertFrom-Json)) { $item })
$workspace = Join-Path $env:TEMP ('Galax71-ExtremeFPS-' + [guid]::NewGuid().ToString('N'))
$modsDir = Join-Path $workspace 'overrides\mods'
New-Item -ItemType Directory -Force $modsDir | Out-Null
try {
    Copy-Item $manifestPath (Join-Path $workspace 'manifest.json')
    $i = 0
    foreach ($mod in $mods) {
        $i++
        $name = [string]$mod.filename
        if ($name -notmatch '^[^/\\]+\.jar$') { throw "Unsafe filename: $name" }
        $url = [string]$mod.url
        if (-not $url.StartsWith('https://cdn.modrinth.com/')) {
            throw "Unexpected mod download host: $url"
        }
        $dest = Join-Path $modsDir $name
        Write-Host "[$i/$($mods.Count)] Downloading $($mod.name) $($mod.version)"
        Invoke-WebRequest -Uri $url -OutFile $dest -MaximumRedirection 4
        $actual = (Get-FileHash -Path $dest -Algorithm SHA512).Hash.ToLowerInvariant()
        $expected = ([string]$mod.sha512).ToLowerInvariant()
        if ($actual -ne $expected) { throw "SHA512 checksum mismatch: $name" }
    }
    $readme = @'
Galax71 Extreme FPS 26.2 Fabric - personal-use CurseForge import.
All JARs were downloaded from original Modrinth CDN URLs and SHA-512 checked.
For performance use Sodium, Lithium, and other bundled compatible mods.
No shaders. Start with 8-12GB RAM; compare with 20GB allocation.
Vulkan support depends on current Sodium/game compatibility and mod conflicts.
This personal-use export is not intended for redistribution or CurseForge publication.
'@
    Set-Content -Path (Join-Path $workspace 'README.txt') -Value $readme -Encoding UTF8
    $outFolder = Split-Path -Parent $OutputPath
    if (!(Test-Path $outFolder)) { New-Item -ItemType Directory -Force $outFolder | Out-Null }
    if (Test-Path $OutputPath) { Remove-Item $OutputPath -Force }
    Compress-Archive -Path (Join-Path $workspace '*') -DestinationPath $OutputPath -CompressionLevel Optimal
    Write-Host "SUCCESS: $OutputPath" -ForegroundColor Green
    Write-Host "Mod count: $($mods.Count). Import the generated ZIP into CurseForge."
    explorer.exe /select,"$OutputPath"
} finally {
    if (Test-Path $workspace) { Remove-Item $workspace -Recurse -Force }
}
