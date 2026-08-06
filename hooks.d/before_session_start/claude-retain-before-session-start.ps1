# Hook: antes de iniciar sesión — cargar memoria comprimida
$PLUGIN_ROOT = ${env:CLAUDE_PLUGIN_ROOT} -or (Split-Path $PSScriptRoot -Parent)

python3 -c "
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.consolidate import read_recent_summary, read_archive_summary

recent = read_recent_summary()
archive = read_archive_summary()

if recent:
    print('[claude-retain] Memory loaded: recent.md')
    print('[RECENT]')
    print(recent)

if archive:
    print('[claude-retain] Memory loaded: archive.md')
    print('[ARCHIVE]')
    print(archive)
" 2>$null || $true
