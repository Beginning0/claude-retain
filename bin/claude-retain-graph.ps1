# Wrapper PowerShell para mostrar grafo de conocimiento temporal

$pluginDir = ""
if ($env:CLAUDE_PLUGIN_ROOT) {
    $pluginDir = $env:CLAUDE_PLUGIN_ROOT
}
else {
    $knownPaths = @(
        "$HOME\.claude\plugins\claude-retain",
        (Get-Location).Path
    )
    foreach ($dir in $knownPaths) {
        if (Test-Path "$dir\claude_retain\cli.py") {
            $pluginDir = $dir
            break
        }
    }
}

if (-not $pluginDir) {
    Write-Host "[claude-retain] ERROR: No se encontró el directorio del plugin" -ForegroundColor Red
    exit 1
}

$PYTHONPATH = "$pluginDir;$env:PYTHONPATH"
$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$args = if ($args.Count -gt 0) { $args } else { @() }
# Usar CLAUDE_PLUGIN_PATH para evitar expansión de variables de PowerShell
$env:CLAUDE_PLUGIN_PATH = $pluginDir
& $pythonExe "-c" "from claude_retain.cli import main; main()" graph @args
