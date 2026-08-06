# Hook PostToolUse — Crea backup automático de archivos modificados
# Lee el contexto del tool call de stdin (JSON)

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

# Config del plugin
$CONFIG_FILE = "$HOME\.claude-retain\auto_permission.json"
if (-not (Test-Path $CONFIG_FILE)) { exit 0 }

# Leer stdin JSON
$inputText = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($inputText)) { exit 0 }

$toolInput = $inputText | ConvertFrom-Json
$toolName = if ($toolInput.tool_name) { $toolInput.tool_name } else { "" }
$filePath = ""
if ($toolInput.input -and $toolInput.input.file_path) {
    $filePath = $toolInput.input.file_path
}

# Solo hacer backup para herramientas Write/Edit (no Bash)
if ([string]::IsNullOrWhiteSpace($filePath) -or $toolName -eq "Bash") { exit 0 }

# Verificar si auto-backup está habilitado
$autoBackup = $false
try {
    $config = Get-Content $CONFIG_FILE -Raw | ConvertFrom-Json
    $autoBackup = $config.categories.dangerous.auto_backup -eq $true
} catch {
    $autoBackup = $false
}

if (-not $autoBackup) { exit 0 }

# Crear backup del archivo original
$backupDir = "$HOME\.claude-retain\backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$fileDir = [System.IO.Path]::GetDirectoryName($filePath)
$fileName = [System.IO.Path]::GetFileName($filePath)
$backupFile = "$backupDir\$((($fileDir -replace '\\', '_') -replace '/', '_')}_${fileName}_${timestamp}"

if (Test-Path $filePath) {
    Copy-Item $filePath $backupFile -ErrorAction SilentlyContinue
    Write-Host "[claude-retain] Backup creado: $backupFile"
}

# ──────── Generar diff y actualizar graph del proyecto ────────

$graphUpdate = $false
try {
    $config = Get-Content $CONFIG_FILE -Raw | ConvertFrom-Json
    $graphUpdate = $config.categories.dangerous.graph_update -eq $true
} catch {
    $graphUpdate = $false
}

if ($graphUpdate -and -not [string]::IsNullOrWhiteSpace($filePath)) {
    $pythonCode = @"
import sys, os, json, hashlib
sys.path.insert(0, r"$PluginDir")
from claude_retain.project_graph import ProjectGraphManager

project_root = r"$((Get-Location).Path)"
file_path = r"$filePath"

if not os.path.exists(file_path):
    print("NO_FILE")
    sys.exit(0)

rel_path = os.path.relpath(file_path, project_root)

# Leer el archivo modificado
with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    new_content = f.read()

# Buscar backup del archivo original para generar diff
backup_dir = r"$HOME\.claude-retain\backups"
diff_lines = []
if os.path.exists(backup_dir):
    import glob, time
    # Buscar el backup más reciente de este archivo
    pattern = os.path.join(backup_dir, f"*_{os.path.basename(file_path)}_*")
    backups = glob.glob(pattern)
    if backups:
        latest_backup = max(backups, key=os.path.getmtime)
        with open(latest_backup, 'r', encoding='utf-8', errors='ignore') as f:
            old_content = f.read()

        # Generar diff simple (línea por línea)
        import difflib
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        differ = difflib.unified_diff(old_lines, new_lines, n=3)
        diff_text = ''.join(differ)
        if diff_text:
            # Guardar diff
            diff_file = os.path.join(backup_dir, f"diff_{os.path.basename(file_path)}_{int(time.time())}.patch")
            with open(diff_file, 'w', encoding='utf-8') as f:
                f.write(diff_text)
            diff_lines = [l for l in diff_text.splitlines() if l.startswith(('-', '+')) and not l.startswith('---') and not l.startswith('+++')]

# Calcular hash del nuevo contenido
new_hash = hashlib.sha256(new_content.encode()).hexdigest()[:12]

# Actualizar graph del proyecto
try:
    pm = ProjectGraphManager(project_root)
    result = pm.incremental_update([rel_path])
    # Registrar cambio en node_stats
    conn = pm.ensure_conn()
    import time
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("""INSERT OR REPLACE INTO node_stats
        (node_id, query_count, last_query, change_count)
        VALUES (?, 0, ?, 1)""", (rel_path, now))
    conn.commit()
    pm.close()

    print(f"GRAPH_UPDATE: edges={result['edges_updated']}")
    print(f"DIFF: {len(diff_lines)} líneas cambiadas")
    if diff_lines[:5]:
        print(f"DIFF_EXAMPLE: {';'.join(diff_lines[:5])}")
    print(f"NEW_HASH: {new_hash}")
except Exception as e:
    print(f"GRAPH_ERROR: {e}")
"@

    $pythonExe = "python3"
    if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
        $pythonExe = "python"
    }

    $graphResult = & $pythonExe -c $pythonCode 2>&1
    foreach ($line in $graphResult) {
        if ($line -match "^GRAPH_UPDATE:") {
            Write-Host "[claude-retain] Graph actualizado: $line" -ForegroundColor DarkGreen
        } elseif ($line -match "^DIFF_EXAMPLE:") {
            Write-Host "[claude-retain] Diff: $($line.Substring(12))" -ForegroundColor Yellow
        } elseif ($line -match "^NEW_HASH:") {
            Write-Host "[claude-retain] Hash nuevo: $($line.Substring(9))" -ForegroundColor Gray
        } elseif ($line -match "^GRAPH_ERROR:") {
            Write-Host "[claude-retain] Error graph: $line" -ForegroundColor DarkRed
        }
    }
}


