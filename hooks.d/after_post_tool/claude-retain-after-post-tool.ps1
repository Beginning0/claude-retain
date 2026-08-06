# Hook: después de una herramienta — auto-save si se cruzó el umbral
$PLUGIN_ROOT = ${env:CLAUDE_PLUGIN_ROOT} -or (Split-Path $PSScriptRoot -Parent)

$TOOL_NAME = $args[0] -or "unknown"

python3 -c "
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.extract import extract_last_exchange

exchange = extract_last_exchange()
if not exchange:
    sys.exit(0)

tools_count = len(exchange.tools_used)
if tools_count >= 3:
    from pipeline.compress import compress_session
    result = compress_session([exchange])
    if result and result.success:
        print(f'[claude-retain] Auto-save: {result.tokens_before} -> {result.tokens_after} tokens')
    else:
        print('[claude-retain] Auto-save: skipped (no compression needed)')
" 2>$null || $true
