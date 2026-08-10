# Hook: después de consolidar — actualizar grafo de conocimiento
$PLUGIN_ROOT = ${env:CLAUDE_PLUGIN_ROOT} -or (Split-Path $PSScriptRoot -Parent)

$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$pythonCode = @"
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.consolidate import read_daily_summaries

summaries = read_daily_summaries()
if not summaries:
    sys.exit(0)

try:
    from claude_retain.project_graph import ProjectGraphManager
    pm = ProjectGraphManager()
    for summary in summaries[-5:]:
        pm.add_knowledge_entry(summary.date, summary.summary)
    print(f'[claude-retain] Graph updated with {len(summaries)} new entries')
except Exception as e:
    print(f'[claude-retain] Graph update failed: {e}')
"@

& $pythonExe -c $pythonCode 2>$null || $true
