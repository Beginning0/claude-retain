# Hook: antes de iniciar sesión — cargar memoria comprimida
$PLUGIN_ROOT = ${env:CLAUDE_PLUGIN_ROOT} -or (Split-Path $PSScriptRoot -Parent)

$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$pythonCode = @"
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
"@

& $pythonExe -c $pythonCode 2>$null || $true
