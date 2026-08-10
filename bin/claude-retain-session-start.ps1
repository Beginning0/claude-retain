# Hook SessionStart — Inicializa el cache LLM al iniciar sesión

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

if (-not $pluginDir) { exit 0 }

# Fallback: python3 -> python
$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$cachePath = "$HOME\.claude-retain\llm_cache.db"

# Inicializar la base de datos SQLite del cache si no existe
if (-not (Test-Path $cachePath)) {
    $cacheDir = [System.IO.Path]::GetDirectoryName($cachePath)
    if (-not (Test-Path $cacheDir)) {
        New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
    }

    $pythonExe -c @"
import sqlite3, os, time
db_path = r'$cachePath'
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path)
conn.execute('''CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key TEXT PRIMARY KEY,
    prompt_hash TEXT NOT NULL,
    context_hash TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    pregunta TEXT,
    respuesta TEXT NOT NULL,
    chars_contexto INTEGER DEFAULT 0,
    fecha_guardado TEXT NOT NULL,
    ttl_seconds INTEGER DEFAULT 86400,
    hits INTEGER DEFAULT 0
);''')
conn.commit()
conn.close()
"@ 2>$null
}

# Limpiar entradas expiradas del cache
if (Test-Path $cachePath) {
    $pythonExe -c @"
import sqlite3, time
db_path = r'$cachePath'
conn = sqlite3.connect(db_path)
now_str = time.strftime('%Y-%m-%d %H:%M:%S')
conn.execute('DELETE FROM llm_cache WHERE fecha_guardado < ?', (now_str,))
total = conn.execute('SELECT COUNT(*) FROM llm_cache').fetchone()[0]
conn.commit()
print(f'[claude-retain] LLM Cache - {total} entradas en cache')
conn.close()
"@ 2>$null
}

# ──────── Detectar nuevo proyecto y construir graph ────────

$projectGraphPath = "$env:USERPROFILE\.claude-retain\project_graph"
$graphDB = "$HOME\.claude-retain\project_graph.db"

# Verificar si hay un graph DB del proyecto actual
$currentProject = (Get-Location).Path
$pythonCode = @"
import os, hashlib

project_root = r'$currentProject'
# Generar hash del project root para identificar el proyecto
project_hash = hashlib.md5(project_root.encode()).hexdigest()[:8]

# Verificar si ya existe graph DB para este proyecto
db_path = os.path.expanduser(f'~/.claude-retain/project_graph_{project_hash}.db')
print(db_path)
print(os.path.exists(db_path))
"@

$graphResult = & $pythonExe -c $pythonCode 2>$null
$graphDbPath = $graphResult[0]
$graphExists = $false
if ($graphResult.Count -gt 1) {
    $graphExists = $graphResult[1].Trim() -eq "True"
}

if (-not $graphExists) {
    Write-Host "[claude-retain] Graph - nuevo proyecto detectado, construyendo graph..." -ForegroundColor Cyan
    $buildCode = @"
import sys, os
sys.path.insert(0, r'$PluginDir')
from claude_retain.project_graph import ProjectGraphManager

pm = ProjectGraphManager(r'$currentProject')
result = pm.build_graph()
print(f'BUILT: nodes={result["nodes_created"]}, edges={result["edges_created"]}')
"@

    & $pythonExe -c $buildCode 2>$null | ForEach-Object {
        if ($_ -match "^BUILT:") {
            Write-Host "[claude-retain] Graph construido: $_" -ForegroundColor DarkGreen
        }
    }
}


