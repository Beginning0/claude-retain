# Wrapper PowerShell para claude-retain checkpoints

$ErrorActionPreference = "Stop"

# 1) Si claude-retain CLI existe via pip, delega a el
try {
    $claude-retainCmd = Get-Command claude-retain -ErrorAction SilentlyContinue
    if ($claude-retainCmd) {
        & claude-retain checkpoints @args
        exit $LASTEXITCODE
    }
} catch {}

# 2) Busca directorio del plugin en rutas conocidas
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

# 3) Ejecuta con PYTHONPATH apuntando al plugin
$env:PYTHONPATH = "$PLUGIN_DIR;$env:PYTHONPATH"
& python -m claude_retain.cli checkpoints @args
exit $LASTEXITCODE


