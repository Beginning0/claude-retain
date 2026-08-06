"""CLI wrapper para el project graph — build, overview, query_semantic, etc."""

import sys
import os
from pathlib import Path

# Agregar directorio del plugin al path
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))

if __name__ == "__main__":
    from claude_retain.project_graph import main
    main()
