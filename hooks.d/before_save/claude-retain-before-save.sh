#!/bin/bash
# Hook: antes de guardar — comprimir sesión actual

python3 -c "
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.compress import compress_last_session
from pipeline.entry_header import save_entry_header
from pipeline.spawn_guard import acquire_lock

# Verificar lock
if not acquire_lock():
    sys.exit(0)

try:
    result = compress_last_session()
    if result and result.success:
        save_entry_header(result.compressed_text)
        print('[claude-retain] Session compressed: ' + str(result.tokens_before) + ' -> ' + str(result.tokens_after) + ' tokens')
    else:
        print('[claude-retain] Compression: skipped (' + (result.reason if result else 'unknown') + ')')
finally:
    from pipeline.spawn_guard import release_lock
    release_lock()
" 2>/dev/null || true
