# Wrapper PowerShell para consultar el graph semántico del proyecto

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
        if (Test-Path "$dir\claude_retain\project_graph.py") {
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

# Pasar el resto de los argumentos al CLI del project graph
$args = if ($args.Count -gt 0) { $args } else { @() }
$env:CLAUDE_PLUGIN_PATH = $pluginDir
& $pythonExe "bin\claude-retain-project-graph.py" @args
