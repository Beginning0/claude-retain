#!/bin/bash
# Script de descubrimiento de herramientas disponibles en Claude Code
# Registra: skills instaladas, MCP servers, hooks configurados

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-.}"
SKILLS_DIR="$HOME/.claude/skills"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "=== Descubriendo herramientas disponibles ==="
echo ""

# 1. Skills instaladas como archivos .skill
echo "Skills (.skill files):"
if [ -d "$SKILLS_DIR" ]; then
    skill_files=$(ls "$SKILLS_DIR"/*.skill 2>/dev/null)
    if [ -n "$skill_files" ]; then
        for f in $skill_files; do
            echo "  - $(basename "$f")"
        done
    else
        echo "  (ninguno)"
    fi
else
    echo "  (directorio no encontrado: $SKILLS_DIR)"
fi

# 2. Skills del plugin.json
echo ""
echo "Skills del plugin:"
PLUGIN_JSON="$PLUGIN_ROOT/.claude-plugin/plugin.json"
if [ -f "$PLUGIN_JSON" ]; then
    skills=$(python3 -c "import json; print('\n'.join('  - ' + s for s in json.load(open('$PLUGIN_JSON')).get('skills', [])))" 2>/dev/null)
    if [ -n "$skills" ]; then
        echo "$skills"
    else
        echo "  (ninguno configurado)"
    fi
fi

# 3. MCP Servers
echo ""
echo "MCP Servers:"
if [ -f "$SETTINGS_FILE" ]; then
    mcp_servers=$(python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    config = json.load(f)
servers = config.get('mcpServers', {})
if servers:
    for name, conf in servers.items():
        print(f'  - {name}: {conf.get(\"command\", \"unknown\")}')
else:
    print('  (ninguno configurado)')
" 2>/dev/null)
    if [ -n "$mcp_servers" ]; then
        echo "$mcp_servers"
    fi
fi

# 4. Hooks configurados
echo ""
echo "Hooks configurados:"
if [ -f "$SETTINGS_FILE" ]; then
    hooks=$(python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    config = json.load(f)
hooks = config.get('hooks', {})
if hooks:
    for name, scripts in hooks.items():
        print(f'  {name}:')
        for script in scripts:
            print(f'    - {script}')
else:
    print('  (ninguno configurado)')
" 2>/dev/null)
    if [ -n "$hooks" ]; then
        echo "$hooks"
    fi
fi

# 5. Skills de claude-retain
echo ""
echo "claude-retain Skills:"
claude-retain_skills=$(ls -d "$PLUGIN_ROOT/skills"/ 2>/dev/null)
if [ -n "$claude-retain_skills" ]; then
    for s in $claude-retain_skills; do
        echo "  - $(basename "$s")"
    done
else
    echo "  (ninguno encontrado)"
fi

echo ""
echo "=== Fin del descubrimiento ==="

