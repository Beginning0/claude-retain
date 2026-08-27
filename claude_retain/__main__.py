"""Entry point para python -m claude_retain <subcommand>.

Cuando se ejecuta como módulo, busca el directorio del plugin en las carpetas conocidas
y añade el PYTHONPATH antes de ejecutar el subcomando.
"""

import os
import sys
from pathlib import Path

def find_plugin_dir():
    """Buscar el directorio del plugin en las carpetas conocidas."""
    # Si está instalado via pip, no necesitamos modificar PYTHONPATH
    if "claude_retain" in sys.modules:
        return None

    for dir_path in [
        os.environ.get("CLAUDE_PLUGIN_ROOT", ""),
        os.path.expanduser("~/.claude/plugins/claude-retain"),
        str(Path(__file__).parent.parent),  # directorio del plugin (si estamos en el lugar correcto)
    ]:
        if not dir_path:
            continue
        plugin_dir = Path(dir_path)
        if plugin_dir.is_dir() and (plugin_dir / "claude_retain" / "cli.py").exists():
            return str(plugin_dir)

    # Si no encontramos el directorio, intentar desde sys.argv[0]
    script_dir = Path(__file__).parent.parent
    while script_dir != script_dir.root:
        if (script_dir / "claude_retain" / "cli.py").exists():
            return str(script_dir)
        script_dir = script_dir.parent

    return None

def main():
    plugin_dir = find_plugin_dir()
    if plugin_dir and plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    # Si no hay subcomando, mostrar ayuda del CLI
    if len(sys.argv) < 2:
        from claude_retain.cli import main as cli_main
        cli_main()
        return

    module_name = sys.argv[1]

    # Comandos del CLI (no módulos)
    cli_commands = {
        "stats", "search", "save", "layers", "graph", "llm-cache-stats", "llm-cache-clear",
        "build-graph", "scope-checker", "checkpoints", "rewind", "branch", "replay",
        "delete-checkpoint", "cleanup",
    }

    if module_name in cli_commands:
        from claude_retain.cli import main as cli_main
        # Reemplazar sys.argv para que el CLI reciba sus propios argumentos
        sys.argv = [sys.argv[0]] + sys.argv[1:]
        cli_main()
        return

    # Intentar como módulo (mcp_server, project_graph)
    try:
        module = __import__(f"claude_retain.{module_name}", fromlist=["main"])
    except ModuleNotFoundError as e:
        print(f"ERROR: No se encontró el modulo {module_name}: {e}")
        return

    # Ejecutar main() si el módulo lo tiene
    if hasattr(module, "main"):
        module.main()

if __name__ == "__main__":
    main()

