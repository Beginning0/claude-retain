#!/bin/bash
# Hook PostToolUse — Construye/actualiza el graph del proyecto después de leer archivos

PLUGIN_DIR=""
if [ -n "$CLAUDE_PLUGIN_ROOT" ]; then
    PLUGIN_DIR="$CLAUDE_PLUGIN_ROOT"
else
    for dir in "$HOME/.claude/plugins/claude-retain" "$(pwd)"; do
        if [ -f "$dir/claude_retain/cli.py" ]; then
            PLUGIN_DIR="$dir"
            break
        fi
    done
fi

[ -z "$PLUGIN_DIR" ] && exit 0

INPUT_TEXT=$(cat)
[ -z "$INPUT_TEXT" ] && exit 0

TOOL_NAME=$(echo "$INPUT_TEXT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
[ "$TOOL_NAME" != "Read" ] && exit 0

FILE_PATH=$(echo "$INPUT_TEXT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('input',{}).get('file_path',''))" 2>/dev/null)
[ -z "$FILE_PATH" ] && exit 0

# Verificar si el archivo está dentro del proyecto actual
CURRENT_PROJECT="$(pwd)"
IN_PROJECT=$(python3 -c "
import os, sys
project_root = r'$CURRENT_PROJECT'
file_path = r'$FILE_PATH'
rel = os.path.relpath(file_path, project_root)
if rel.startswith('..'):
    print('NO')
else:
    print('YES')
" 2>/dev/null)

[ "$IN_PROJECT" != "YES" ] && exit 0

GRAPH_DB="$HOME/.claude-retain/project_graph.db"
GRAPH_DIR="$HOME/.claude-retain/project_graph"

if [ -f "$GRAPH_DB" ]; then
    # Actualizar incrementalmente solo este archivo
    python3 -c "
import sys, os
sys.path.insert(0, r'$PLUGIN_DIR')
from claude_retain.project_graph import ProjectGraphManager

project_root = r'$CURRENT_PROJECT'
file_path = r'$FILE_PATH'
rel_path = os.path.relpath(file_path, project_root)

pm = ProjectGraphManager(project_root)
result = pm.incremental_update([rel_path])
print(f'GRAPH_UPDATE: edges={result[\"edges_updated\"]}, nodes={result[\"nodes_created\"]}')
pm.close()
" 2>/dev/null | while IFS= read -r line; do
    case "$line" in
        GRAPH_UPDATE:*) echo "[claude-retain] PostRead: Graph actualizado — $line" >&2 ;;
        GRAPH_ERROR:*) echo "[claude-retain] PostRead error: $line" >&2 ;;
    esac
done
else
    # Construir graph completo del proyecto
    echo "[claude-retain] PostRead — graph no encontrado, construyendo..." >&2

    python3 -c "
import sys, os
sys.path.insert(0, r'$PLUGIN_DIR')
from claude_retain.project_graph import ProjectGraphManager

project_root = r'$CURRENT_PROJECT'
pm = ProjectGraphManager(project_root)
result = pm.build_graph()
print(f'BUILT: nodes={result[\"nodes_created\"]}, edges={result[\"edges_created\"]}')
" 2>/dev/null | while IFS= read -r line; do
    case "$line" in
        BUILT:*) echo "[claude-retain] PostRead: Graph construido — $line" >&2 ;;
    esac
done
fi


