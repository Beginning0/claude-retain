# Hook PostToolUse — Construye/actualiza el graph del proyecto después de leer archivos
# También detecta archivos grandes y genera resumen automático

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

# Verificar si el archivo está dentro del proyecto actual
$currentProject = (Get-Location).Path
$pythonCode = @"
import os, sys

project_root = r"$currentProject"
file_path = r"$filePath"

# Verificar si el archivo está dentro del proyecto
rel = os.path.relpath(file_path, project_root)
if rel.startswith('..'):
    print("NOT_IN_PROJECT")
    sys.exit(0)

print("IN_PROJECT")
"@

$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$projectResult = & $pythonExe -c $pythonCode 2>$null
$inProject = False
foreach ($line in $projectResult) {
    if ($line -eq "IN_PROJECT") { $inProject = True }
}

if (-not $inProject) { exit 0 }

# Verificar si el archivo es grande (>100KB)
$largeFile = $false
$largeWarning = ""
try {
    $fileSize = (Get-Item $filePath).Length
    if ($fileSize -gt 102400) {  # >100KB
        $largeFile = $true
        $sizeKB = [math]::Round($fileSize / 1024, 1)
        $largeWarning = "ARCHIVO_GRANDE: $filePath ($sizeKB KB)"
    }
} catch {
    # Ignorar error al obtener tamaño
}

# Construir/actualizar el graph para este archivo
$graphDB = "$HOME\.claude-retain\project_graph.db"
$graphDir = "$HOME\.claude-retain\project_graph"

if (Test-Path $graphDB) {
    # Actualizar incrementalmente solo este archivo
    $pythonCode2 = @"
import sys, os
sys.path.insert(0, r"$PluginDir")
from claude_retain.project_graph import ProjectGraphManager

project_root = r"$currentProject"
file_path = r"$filePath"
rel_path = os.path.relpath(file_path, project_root)

pm = ProjectGraphManager(project_root)
result = pm.incremental_update([rel_path])
print(f"GRAPH_UPDATE: edges={result['edges_updated']}, nodes={result['nodes_created']}")
pm.close()
"@

    $graphResult = & $pythonExe -c $pythonCode2 2>$null
    foreach ($line in $graphResult) {
        if ($line -match "^GRAPH_UPDATE:") {
            Write-Host "[claude-retain] PostRead: Graph actualizado — $line" -ForegroundColor DarkGreen
        } elseif ($line -match "^GRAPH_ERROR:") {
            Write-Host "[claude-retain] PostRead error: $line" -ForegroundColor DarkRed
        }
    }
} else {
    # Construir graph completo del proyecto
    Write-Host "[claude-retain] PostRead — graph no encontrado, construyendo..." -ForegroundColor Yellow

    $buildCode = @"
import sys, os
sys.path.insert(0, r"$PluginDir")
from claude_retain.project_graph import ProjectGraphManager

project_root = r"$currentProject"
pm = ProjectGraphManager(project_root)
result = pm.build_graph()
print(f"BUILT: nodes={result['nodes_created']}, edges={result['edges_created']}")
"@

    $buildResult = & $pythonExe -c $buildCode 2>$null
    foreach ($line in $buildResult) {
        if ($line -match "^BUILT:") {
            Write-Host "[claude-retain] PostRead: Graph construido — $line" -ForegroundColor DarkGreen
        }
    }
}

# Mostrar advertencia de archivo grande si aplica
if ($largeFile) {
    Write-Host "[claude-retain] $largeWarning" -ForegroundColor Yellow
    Write-Host "[claude-retain]    Para consultar sin leerlo completo: ./bin/claude-retain-graph.ps1 query_structural $(Split-Path $filePath -Leaf)" -ForegroundColor Gray
}


