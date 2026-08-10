# Hook: antes de guardar — comprimir sesión actual
$PLUGIN_ROOT = ${env:CLAUDE_PLUGIN_ROOT} -or (Split-Path $PSScriptRoot -Parent)

$pythonExe = "python3"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    $pythonExe = "python"
}

$pythonCode = @"
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.compress import compress_last_session
from pipeline.entry_header import save_entry_header
from pipeline.spawn_guard import acquire_lock

if not acquire_lock():
    sys.exit(0)

try:
    result = compress_last_session()
    if result and result.success:
        save_entry_header(result.compressed_text)
        print(f'[claude-retain] Session compressed: {result.tokens_before} -> {result.tokens_after} tokens')
    else:
        print('[claude-retain] Compression: skipped (session too short or failed)')
finally:
    from pipeline.spawn_guard import release_lock
    release_lock()
"@

& $pythonExe -c $pythonCode 2>$null || $true
