#!/bin/bash
# Hook: después de guardar — ejecutar consolidación de memoria

PYTHON=$(command -v python3 || command -v python)
$PYTHON -c "
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.consolidate import run_consolidation

try:
    result = run_consolidation()
    if result:
        print('[claude-retain] Consolidation: daily summaries merged into weekly')
    else:
        print('[claude-retain] Consolidation: skipped (no summaries to merge)')
except Exception as e:
    print('[claude-retain] Consolidation failed: ' + str(e))
" 2>/dev/null || true
