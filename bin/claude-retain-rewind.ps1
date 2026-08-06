# Wrapper PowerShell para claude-retain rewind

$ErrorActionPreference = "Stop"

try {
    $claude-retainCmd = Get-Command claude-retain -ErrorAction SilentlyContinue
    if ($claude-retainCmd) {
        & claude-retain rewind @args
        exit $LASTEXITCODE
    }
} catch {}

$PLUGIN_DIR = $null
if ($env:CLAUDE_PLUGIN_ROOT) {
    $PLUGIN_DIR = $env:CLAUDE_PLUGIN_ROOT
} elseif (Test-Path "$PWD\.claude-plugin") {
    $PLUGIN_DIR = $PWD
} else {
    $knownDirs = @(
        "$HOME\.claude\plugins\claude-retain",
        ($env:CLAUDE_PLUGIN_ROOT -split ";" | Where-Object { $_ })[0]
    )
    foreach ($dir in $knownDirs) {
        if ($dir -and (Test-Path (Join-Path $dir "claude_retain\cli.py"))) {
            $PLUGIN_DIR = $dir
            break
        }
    }
}

if (-not $PLUGIN_DIR) {
    Write-Host "[claude-retain] ERROR: No se encontro el directorio del plugin." -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = "$PLUGIN_DIR;$env:PYTHONPATH"
& python -m claude_retain.cli rewind @args
exit $LASTEXITCODE


