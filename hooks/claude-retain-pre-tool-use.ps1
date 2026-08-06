# Hook PreToolUse — Consulta el graph del proyecto ANTES de leer archivos
# Lee el contexto del tool call de stdin (JSON)
# Si el archivo ya tiene info en el graph, emite un hint para que el agente use esa info

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

# Leer stdin JSON
$inputText = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($inputText)) { exit 0 }

$toolInput = $inputText | ConvertFrom-Json
$toolName = if ($toolInput.tool_name) { $toolInput.tool_name } else { "" }

# Solo para la herramienta Read
if ($toolName -ne "Read") { exit 0 }

$filePath = ""
if ($toolInput.input -and $toolInput.input.file_path) {
    $filePath = $toolInput.input.file_path
}

if ([string]::IsNullOrWhiteSpace($filePath)) { exit 0 }

# Verificar si el archivo ya está en el graph del proyecto
$graphDir = "$HOME\.claude-retain\project_graph"
$graphDb = "$graphDir\project_graph.db"

if (-not (Test-Path $graphDb)) {
    Write-Host "[claude-retain] PreRead — graph no construido, sugiriendo consulta primero" -ForegroundColor Yellow
    exit 0
}

# Consultar si el archivo existe en el graph
$pythonCode = @"
import sys, os, sqlite3

graph_db = r"$graphDb"
file_path = r"$filePath"

if not os.path.exists(graph_db):
    print("NO_GRAPH")
    sys.exit(0)

conn = sqlite3.connect(graph_db)
try:
    # Buscar el archivo en los nodos
    cursor = conn.execute("""
        SELECT n.path, n.node_type, n.summary, ns.query_count, ns.last_query
        FROM nodes n
        LEFT JOIN node_stats ns ON n.node_id = ns.node_id
        WHERE n.path = ?
    """, (file_path,))
    row = cursor.fetchone()

    if row:
        path, node_type, summary, query_count, last_query = row
        if query_count and query_count > 0:
            print(f"HINT: Archivo indexado — {query_count} consultas previas")
            print(f"HINT_TYPE: indexed")
            if summary:
                print(f"HINT_SUMMARY: {summary}")
            if last_query:
                print(f"HINT_LAST_QUERY: {last_query}")
        else:
            print(f"HINT: Archivo en graph pero sin consultas previas")
            print(f"HINT_TYPE: unqueried")
            if summary:
                print(f"HINT_SUMMARY: {summary}")
    else:
        print("HINT: Archivo NO está indexado — consulta el graph antes de leer")
        print("HINT_TYPE: not_indexed")

except Exception as e:
    print(f"ERROR: {e}")
finally:
    conn.close()
"@

$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$result = & $pythonExe -c $pythonCode 2>&1
foreach ($line in $result) {
    if ($line -match "^HINT:") {
        Write-Host "[claude-retain] PreRead: $($line.Substring(6))" -ForegroundColor DarkYellow
    } elseif ($line -match "^HINT_TYPE:") {
        # Tipo de hint — silencioso, solo para referencia interna
    } elseif ($line -match "^HINT_SUMMARY:") {
        Write-Host "[claude-retain] PreRead: $($line.Substring(14))" -ForegroundColor DarkYellow
    } elseif ($line -match "^HINT_LAST_QUERY:") {
        Write-Host "[claude-retain] PreRead: Última consulta: $($line.Substring(17))" -ForegroundColor DarkYellow
    } elseif ($line -match "^NO_GRAPH:") {
        exit 0
    } elseif ($line -match "^ERROR:") {
        Write-Host "[claude-retain] PreRead error: $($line.Substring(7))" -ForegroundColor DarkRed
    }
}


