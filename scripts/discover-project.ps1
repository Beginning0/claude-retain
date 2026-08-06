# discover-project.ps1 — Descubrir estructura del proyecto y generar graph inicial

param(
    [string]$ProjectRoot = (Get-Location).Path,
    [switch]$Rebuild
)

$PluginDir = ""
if ($env:CLAUDE_PLUGIN_ROOT) {
    $PluginDir = $env:CLAUDE_PLUGIN_ROOT
} else {
    $knownPaths = @(
        "$HOME\.claude\plugins\claude-retain",
        (Get-Location).Path
    )
    foreach ($dir in $knownPaths) {
        if (Test-Path "$dir\claude_retain\project_graph.py") {
            $PluginDir = $dir
            break
        }
    }
}

if (-not $PluginDir) {
    Write-Host "[claude-retain] ERROR: No se encontró el plugin claude-retain" -ForegroundColor Red
    exit 1
}

Write-Host "[claude-retain] Discover - analizando proyecto: $ProjectRoot"

# Ejecutar Python para hacer el scan
$pythonCode = @"
import sys, os, hashlib, re
from pathlib import Path

project_root = r"$ProjectRoot"
ignore_dirs = {
    "node_modules", ".git", "__pycache__", ".tox", ".mypy_cache",
    ".pytest_cache", ".venv", "venv", "env", ".env",
    "dist", "build", "target", "out", "bin", "obj",
    ".next", ".nuxt", ".cache", ".idea", ".vscode",
}
ignore_exts = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico",
    ".mp4", ".avi", ".mov", ".wmv", ".flv",
    ".mp3", ".wav", ".ogg", ".flac",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
}

files = []
for root, dirs, fnames in os.walk(project_root):
    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
    for fname in fnames:
        ext = Path(fname).suffix.lower()
        if ext in ignore_exts:
            continue
        if fname.startswith(".") and ext not in {".py", ".js", ".ts", ".json", ".yml", ".yaml", ".toml", ".md"}:
            continue
        abs_path = os.path.join(root, fname)
        rel_path = os.path.relpath(abs_path, project_root)
        files.append((abs_path, rel_path))

# Detectar imports
results = []
for abs_path, rel_path in files:
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(10000)
        classes = len(re.findall(r"\bclass\s+\w+", content[:4000]))
        functions = len(re.findall(r"\bdef\s+\w+", content[:4000]))
        async_funcs = len(re.findall(r"\basync\s+def\s+\w+", content[:4000]))
        imports = re.findall(r"\bfrom\s+(\w+[\.\w]*)\s+import\b", content) + \
                  re.findall(r"\bimport\s+(\w+)", content)
        results.append({
            "path": rel_path,
            "classes": classes,
            "functions": functions,
            "async_functions": async_funcs,
            "imports": list(set(imports)),
        })
    except Exception:
        continue

print(f"FOUND_FILES:{len(files)}")
for r in results:
    print(f"FILE:{r['path']}|{r['classes']}-{r['functions']}-{r['async_functions']}|{'|'.join(r['imports'])}")
"@

$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$result = & $pythonExe -c $pythonCode 2>&1

$foundFiles = 0
foreach ($line in $result) {
    if ($line -match "^FOUND_FILES:(\d+)$") {
        $foundFiles = [int]$matches[1]
    } elseif ($line -match "^FILE:(.+?)\|(\d+)-(\d+)-(\d+)\|(.+)$") {
        $path = $matches[1]
        $classes = $matches[2]
        $functions = $matches[3]
        $async = $matches[4]
        $imports = $matches[5]
        if ($imports) {
            Write-Host "  [import] $path -> $($imports.Replace('|', ', '))" -ForegroundColor Yellow
        } elseif ($classes -gt 0 -or $functions -gt 0) {
            Write-Host "  [code] $path — $($classes) clase(s), $($functions) función(es)" -ForegroundColor Cyan
        }
    }
}

Write-Host "[claude-retain] Discover — encontrado: $foundFiles archivos"

# Construir graph con Python
if ($Rebuild -or (Test-Path "$env:USERPROFILE\.claude-retain\project_graph.db") -eq $false) {
    Write-Host "[claude-retain] Construyendo graph del proyecto..." -ForegroundColor Cyan

    $graphCode = @"
import sys, os
sys.path.insert(0, r"$PluginDir")
from claude_retain.project_graph import ProjectGraphManager

pm = ProjectGraphManager(r"$ProjectRoot")
result = pm.build_graph()
print(f"BUILT: nodes={result['nodes_created']}, edges={result['edges_created']}")
"@

    $graphResult = & $pythonExe -c $graphCode 2>&1
    foreach ($line in $graphResult) {
        if ($line -match "^BUILT:") {
            Write-Host "[claude-retain] Graph construido: $line" -ForegroundColor Green
        }
    }
}


