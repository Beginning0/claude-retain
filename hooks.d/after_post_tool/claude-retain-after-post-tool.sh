#!/bin/bash
# Hook: después de una herramienta — auto-save si se cruzó el umbral de 3 herramientas

python3 -c "
import sys, os, json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Contador de herramientas en estado persistente
state_file = Path.home() / '.claude-retain' / 'tool_counter.json'
state_file.parent.mkdir(parents=True, exist_ok=True)

# Leer estado actual
if state_file.exists():
    try:
        with open(state_file) as f:
            state = json.load(f)
    except (json.JSONDecodeError, IOError):
        state = {'count': 0, 'session_id': ''}
else:
    state = {'count': 0, 'session_id': ''}

# Obtener ID de sesión actual del hook
session_id = os.environ.get('CLAUDE_SESSION_ID', '')

# Si cambió de sesión, resetear contador
if session_id and session_id != state.get('session_id', ''):
    state = {'count': 0, 'session_id': session_id}

# Incrementar contador
state['count'] += 1

# Guardar estado actualizado
with open(state_file, 'w') as f:
    json.dump(state, f)

# Si alcanzó el umbral de 3 herramientas, disparar auto-save
if state['count'] >= 3 and os.environ.get('CLAUDE_REMEMBER_AUTO_SAVE', 'true').lower() == 'true':
    from pipeline.compress import compress_last_session
    result = compress_last_session()
    if result:
        if result.success:
            print('[claude-retain] Auto-save: ' + str(result.tokens_before) + ' -> ' + str(result.tokens_after) + ' tokens')
        else:
            print('[claude-retain] Auto-save: skipped — ' + (result.reason if result else 'unknown'))
" 2>/dev/null || true
