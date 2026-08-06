# Wrapper para el servidor MCP del cache LLM (PowerShell)
# Se asegura de que PYTHONPATH incluya el directorio del plugin

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
    Write-Error "[claude-retain] ERROR: No se encontro el directorio del plugin."
    exit 1
}

$env:claude-retain_CACHE_PATH = "$HOME\.claude-retain\llm_cache.db"
$env:PYTHONPATH = "${pluginDir};${env:PYTHONPATH}"
& python3 -m claude_retain.mcp_server


