#!/usr/bin/env bash
# Wrapper bash para consultar el graph semántico del proyecto

pluginDir=""
if [ -n "$CLAUDE_PLUGIN_ROOT" ]; then
    pluginDir="$CLAUDE_PLUGIN_ROOT"
else
    for dir in "$HOME/.claude/plugins/claude-retain" "$(pwd)"; do
        if [ -f "$dir/claude_retain/project_graph.py" ]; then
            pluginDir="$dir"
            break
        fi
    done
fi

if [ -z "$pluginDir" ]; then
    echo "[claude-retain] ERROR: No se encontró el directorio del plugin" >&2
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)
PYTHONPATH="$pluginDir:$PYTHONPATH" exec "$PYTHON" "bin/claude-retain-project-graph.py" "$@"
