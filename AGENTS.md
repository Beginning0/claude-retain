# AGENTS.md — instrucciones para agentes de código

Este repo es **claude-retain**: plugin de memoria persistente (4 capas L0-L3, BM25 + embeddings, grafo de conocimiento, checkpoints con time-travel) para agentes de código.

## Usar la propia memoria del plugin (obligatorio al trabajar en este proyecto)

Antes de empezar a trabajar en cualquier proyecto de esta máquina, el agente DEBE consultar la memoria persistente y guardar lo importante al terminar:

- Instrucciones completas: `skills/claude-retain-integration/SKILL.md` (lee este archivo si tu agente soporta skills).
- Clon local: `H:\Nueva carpeta\claude-retain` (esta carpeta). Datos en `~/.claude-retain/`.

```powershell
# 1) Al iniciar/resumir sesión en un proyecto conocido:
Set-Location "H:\Nueva carpeta\claude-retain"; python -m claude_retain search "<proyecto>"

# 2) Al terminar una tarea importante (wing=proyecto, room=tema):
python -c "import sys; sys.path.insert(0,'.'); from claude_retain.memory import MemoryManager; mm=MemoryManager(); ok=mm.initialize(); print('init:',ok); r=mm.save_memory(content='<decision/aprendizaje>', wing='<proyecto>', room='<tema>'); print('save:',r)"
```

Regla: 1 búsqueda al inicio + 1 guardado por hito. No abusar (~2-10 s por llamada).

## Desarrollo del plugin (reglas para este repo)

- Python 3.9+, sin dependencias externas obligatorias en el core (`claude_retain/`). El CLI es `python -m claude_retain <comando>`.
- **Windows**: la consola usa cp1252; los drawers pueden contener BOM/unicode. Mantener el fix de UTF-8 en `claude_retain/cli.py` (`sys.stdout.reconfigure(encoding='utf-8', errors='replace')`) — sin él, `search` crashea con `UnicodeEncodeError`.
- Prueba rápida tras cambios:
  ```powershell
  Set-Location "H:\Nueva carpeta\claude-retain"
  python -m claude_retain stats
  python -m claude_retain search "proyecto"
  ```
- Los skills de Claude Code viven en `skills/<nombre>/SKILL.md` y los comandos en `commands/*.md`; al añadir uno nuevo, registrar el path en `.claude-plugin/plugin.json`.

