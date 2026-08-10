# Hook: después de guardar — ejecutar consolidación de memoria
$PLUGIN_ROOT = ${env:CLAUDE_PLUGIN_ROOT} -or (Split-Path $PSScriptRoot -Parent)

$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$pythonCode = @"
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
    print(f'[claude-retain] Consolidation failed: {e}')
"@

& $pythonExe -c $pythonCode 2>$null || $true
