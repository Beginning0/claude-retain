#!/bin/bash
# Hook PreToolUse — Consulta el graph del proyecto ANTES de leer archivos
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
[ "$TOOL_NAME" != "Read" ] && exit 0

FILE_PATH=$(echo "$INPUT_TEXT" | $PYTHON -c "import sys, json; d=json.load(sys.stdin); print(d.get('input',{}).get('file_path',''))" 2>/dev/null)
[ -z "$FILE_PATH" ] && exit 0

GRAPH_DIR="$HOME/.claude-retain/project_graph"
GRAPH_DB="$GRAPH_DIR/project_graph.db"

if [ ! -f "$GRAPH_DB" ]; then
    echo "[claude-retain] PreRead — graph no construido, sugiriendo consulta primero" >&2
    exit 0
fi

# Consultar si el archivo existe en el graph
$PYTHON -c "
import sys, os, sqlite3

graph_db = r'$GRAPH_DB'
file_path = r'$FILE_PATH'

if not os.path.exists(graph_db):
    print('NO_GRAPH')
    sys.exit(0)

conn = sqlite3.connect(graph_db)
try:
    cursor = conn.execute('''
        SELECT n.path, n.node_type, n.summary, ns.query_count, ns.last_query
        FROM nodes n
        LEFT JOIN node_stats ns ON n.node_id = ns.node_id
        WHERE n.path = ?
    ''', (file_path,))
    row = cursor.fetchone()

    if row:
        path, node_type, summary, query_count, last_query = row
        if query_count and query_count > 0:
            print(f'HINT: Archivo indexado — {query_count} consultas previas')
            print(f'HINT_TYPE: indexed')
            if summary:
                print(f'HINT_SUMMARY: {summary}')
            if last_query:
                print(f'HINT_LAST_QUERY: {last_query}')
        else:
            print('HINT: Archivo en graph pero sin consultas previas')
            print('HINT_TYPE: unqueried')
            if summary:
                print(f'HINT_SUMMARY: {summary}')
    else:
        print('HINT: Archivo NO está indexado — consulta el graph antes de leer')
        print('HINT_TYPE: not_indexed')

except Exception as e:
    print(f'ERROR: {e}')
finally:
    conn.close()
" 2>/dev/null | while IFS= read -r line; do
    case "$line" in
        HINT:*) echo "[claude-retain] PreRead: ${line#HINT: }" >&2 ;;
        HINT_SUMMARY:*) echo "[claude-retain] PreRead: ${line#HINT_SUMMARY: }" >&2 ;;
        HINT_LAST_QUERY:*) echo "[claude-retain] PreRead: Última consulta: ${line#HINT_LAST_QUERY: }" >&2 ;;
        NO_GRAPH|HINT_TYPE:*|ERROR:*) ;;
    esac
done


