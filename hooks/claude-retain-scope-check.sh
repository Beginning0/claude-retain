#!/bin/bash
# Hook PreToolUse — Ejecuta scope-checker ANTES de escribir en archivos JS/TS
# Lee el contexto del tool call de stdin (JSON)

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

# Fallback: python3 -> python
PYTHON=$(command -v python3 || command -v python)

# Leer stdin JSON
INPUT_TEXT=$(cat)
[ -z "$INPUT_TEXT" ] && exit 0

TOOL_NAME=$(echo "$INPUT_TEXT" | $PYTHON -c "import sys, json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
# Solo para Write/Edit
if [ "$TOOL_NAME" != "Write" ] && [ "$TOOL_NAME" != "Edit" ]; then
    exit 0
fi

# Obtener la ruta del archivo
FILE_PATH=$(echo "$INPUT_TEXT" | $PYTHON -c "import sys, json; d=json.load(sys.stdin); print(d.get('input',{}).get('file_path',''))" 2>/dev/null)
[ -z "$FILE_PATH" ] && exit 0

# Solo archivos JS/TS
EXTENSION=$(echo "$FILE_PATH" | grep -oiE '\.(js|ts|mjs|cjs)$' | head -1 | tr '[:upper:]' '[:lower:]')
if [ -z "$EXTENSION" ]; then
    exit 0
fi

# Verificar si el archivo existe antes de escanear
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Ejecutar scope-checker
SKILL_DIR="$PLUGIN_DIR/skills/scope-checker"
PY_SCRIPT="$SKILL_DIR/scope-checker.py"

if [ -f "$PY_SCRIPT" ]; then
    OUTPUT=$($PYTHON "$PY_SCRIPT" "$FILE_PATH" --json 2>/dev/null)
    if [ $? -ne 0 ] && [ -n "$OUTPUT" ]; then
        # scope-checker encontró problemas (exit code 1)
        ISSUES=$(echo "$OUTPUT" | $PYTHON -c "import sys, json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null)
        if [ -n "$ISSUES" ] && [ "$ISSUES" -gt 0 ]; then
            echo "[claude-retain] scope-checker: Se encontraron $ISSUES problema(s) de scope de variables en $FILE_PATH antes de escribir." >&2
            # Mostrar detalles resumidos
            echo "$OUTPUT" | $PYTHON -c "
import sys, json
data = json.load(sys.stdin)
for issue in data:
    sev = issue['severity']
    var = issue['variable']
    line = issue['assign_line']
    detail = issue['detail']
    print(f'  [{sev}] {var} (linea {line}): {detail}', file=sys.stderr)
" 2>/dev/null
            echo "[claude-retain] scope-checker: RECOMENDADO — verificar scope de variables antes de escribir." >&2
        fi
    elif [ -z "$OUTPUT" ]; then
        # No hubo output — probablemente no hay errores (o el script no se ejecutó)
        :
    fi
fi


