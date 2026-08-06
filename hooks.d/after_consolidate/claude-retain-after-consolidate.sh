#!/bin/bash
# Hook: después de consolidar — actualizar grafo de conocimiento

python3 -c "
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.consolidate import read_daily_summaries
from claude_retain.project_graph import ProjectGraphManager

summaries = read_daily_summaries()
if not summaries:
    sys.exit(0)

try:
    pm = ProjectGraphManager()
    for summary in summaries[-5:]:
        pm.add_knowledge_entry(summary.date, summary.summary)
    print('[claude-retain] Graph updated with ' + str(len(summaries)) + ' new entries')
except Exception as e:
    print('[claude-retain] Graph update failed: ' + str(e))
" 2>/dev/null || true
