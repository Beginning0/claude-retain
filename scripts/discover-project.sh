#!/bin/bash
# discover-project.sh — Descubrir estructura del proyecto y generar graph inicial

PROJECT_ROOT="${1:-$(pwd)}"
REBUILD="${2:-}"

# Buscar el plugin
PLUGIN_DIR=""
if [ -n "$CLAUDE_PLUGIN_ROOT" ]; then
    PLUGIN_DIR="$CLAUDE_PLUGIN_ROOT"
elif [ -d "$PWD/.claude-plugin" ] && [ -f "$PWD/claude_retain/project_graph.py" ]; then
    PLUGIN_DIR="$PWD"
else
    for dir in \
        "$HOME/.claude/plugins/claude-retain" \
        "${CLAUDE_PLUGIN_ROOT:-.}"; do
        if [ -d "$dir" ] && [ -f "$dir/claude_retain/project_graph.py" ]; then
            PLUGIN_DIR="$dir"
            break
        fi
    done
fi

if [ -z "$PLUGIN_DIR" ]; then
    echo "[claude-retain] ERROR: No se encontró el plugin claude-retain" >&2
    exit 1
fi

echo "[claude-retain] Discover - analizando proyecto: $PROJECT_ROOT"

# Fallback: python3 -> python
PYTHON=$(command -v python3 || command -v python)

# Escanear archivos con Python
$PYTHON -c "
import sys, os, re
from pathlib import Path

project_root = '$PROJECT_ROOT'
ignore_dirs = {
    'node_modules', '.git', '__pycache__', '.tox', '.mypy_cache',
    '.pytest_cache', '.venv', 'venv', 'env', '.env',
    'dist', 'build', 'target', 'out', 'bin', 'obj',
    '.next', '.nuxt', '.cache', '.idea', '.vscode',
}
ignore_exts = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico',
    '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.mp3', '.wav', '.ogg', '.flac',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.woff', '.woff2', '.ttf', '.eot',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
}

files = []
for root, dirs, fnames in os.walk(project_root):
    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
    for fname in fnames:
        ext = Path(fname).suffix.lower()
        if ext in ignore_exts:
            continue
        if fname.startswith('.') and ext not in {'.py', '.js', '.ts', '.json', '.yml', '.yaml', '.toml', '.md'}:
            continue
        abs_path = os.path.join(root, fname)
        rel_path = os.path.relpath(abs_path, project_root)
        files.append((abs_path, rel_path))

results = []
for abs_path, rel_path in files:
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(10000)
        classes = len(re.findall(r'\bclass\s+\w+', content[:4000]))
        functions = len(re.findall(r'\bdef\s+\w+', content[:4000]))
        async_funcs = len(re.findall(r'\basync\s+def\s+\w+', content[:4000]))
        imports = re.findall(r'\bfrom\s+(\w+[\.\w]*)\s+import\b', content) + \
                  re.findall(r'\bimport\s+(\w+)', content)
        results.append({
            'path': rel_path,
            'classes': classes,
            'functions': functions,
            'async_functions': async_funcs,
            'imports': list(set(imports)),
        })
    except Exception:
        continue

print(f'FOUND_FILES:{len(files)}')
for r in results:
    print(f\"FILE:{r['path']}|{r['classes']}-{r['functions']}-{r['async_functions']}|{'|'.join(r['imports'])}\")
" 2>/dev/null

FOUND_COUNT=$($PYTHON -c "
import sys, os, re
from pathlib import Path

project_root = '$PROJECT_ROOT'
ignore_dirs = {
    'node_modules', '.git', '__pycache__', '.tox', '.mypy_cache',
    '.pytest_cache', '.venv', 'venv', 'env', '.env',
    'dist', 'build', 'target', 'out', 'bin', 'obj',
    '.next', '.nuxt', '.cache', '.idea', '.vscode',
}
ignore_exts = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico',
    '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.mp3', '.wav', '.ogg', '.flac',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.woff', '.woff2', '.ttf', '.eot',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
}

count = 0
for root, dirs, fnames in os.walk(project_root):
    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
    count += len(fnames)
print(count)
" 2>/dev/null)

echo "[claude-retain] Discover - encontrado: $FOUND_COUNT archivos de código"

# Construir graph si es rebuild o no existe la DB
if [ "$REBUILD" = "--rebuild" ] || [ ! -f "$HOME/.claude-retain/project_graph.db" ]; then
    echo "[claude-retain] Construyendo graph del proyecto..."

    $PYTHON -c "
import sys, os
sys.path.insert(0, '$PLUGIN_DIR')
from claude_retain.project_graph import ProjectGraphManager

pm = ProjectGraphManager('$PROJECT_ROOT')
result = pm.build_graph()
print(f'BUILT: nodes={result[\"nodes_created\"]}, edges={result[\"edges_created\"]}')
" 2>/dev/null
fi


