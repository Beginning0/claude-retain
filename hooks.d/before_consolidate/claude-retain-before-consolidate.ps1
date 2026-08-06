# Hook: antes de consolidar — verificar si hay resúmenes diarios para consolidar
$PLUGIN_ROOT = ${env:CLAUDE_PLUGIN_ROOT} -or (Split-Path $PSScriptRoot -Parent)

python3 -c "
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.consolidate import read_daily_summaries
from pipeline.spawn_guard import acquire_lock

if not acquire_lock():
    sys.exit(0)

summaries = read_daily_summaries()
if not summaries:
    print('[claude-retain] Consolidation: no daily summaries to consolidate')
    sys.exit(0)

print(f'[claude-retain] Consolidation: {len(summaries)} daily summaries found, consolidating...')
" 2>$null || $true
