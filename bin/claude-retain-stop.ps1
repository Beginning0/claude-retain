# Hook Stop — Limpieza al terminar una respuesta (limpiar entradas expiradas del cache)

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

$cachePath = "$HOME\.claude-retain\llm_cache.db"

# Limpiar entradas expiradas del cache al final de cada respuesta
if (Test-Path $cachePath) {
    python3 -c @"
import sqlite3, time
db_path = r'$cachePath'
conn = sqlite3.connect(db_path)
now_str = time.strftime('%Y-%m-%d %H:%M:%S')
deleted = conn.execute('DELETE FROM llm_cache WHERE fecha_guardado < ?', (now_str,)).rowcount
total = conn.execute('SELECT COUNT(*) FROM llm_cache').fetchone()[0]
conn.commit()
if deleted > 0:
    print(f'[claude-retain] LLM Cache - {deleted} entradas expiradas eliminadas, {total} restantes')
conn.close()
"@ 2>$null
}


