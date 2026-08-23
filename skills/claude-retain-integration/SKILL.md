---
name: claude-retain-integration
description: How to use claude-retain persistent memory from Codex or any other CLI agent — search past context at session start, save decisions/learnings at milestones, checkpoints for risky work. Use when starting work in a known project, resuming a previous conversation, or finishing an important task on this machine.
---

# claude-retain-integration (memoria persistente para cualquier agente)

claude-retain guarda memoria entre sesiones en `~/.claude-retain/` (Windows: `C:\Users\<usuario>\.claude-retain`). Funciona desde cualquier agente vía CLI Python — no requiere MCP ni hooks de Claude Code.

## Ubicación del clon

- El clon puede estar en CUALQUIER ruta. Si no existe:
  `git clone https://github.com/Beginning0/claude-retain <ruta-a-tu-clon>`
  y copia esta skill en la carpeta de skills del agente.
- Trabaja SIEMPRE desde esa carpeta: entra a ella (`cd <ruta-a-tu-clon>`) antes de correr los comandos.

## REGLA DE USO AUTOMÁTICO (no opcional)

1. **Inicio de sesión / resume en un proyecto conocido** → ejecutar SIEMPRE antes de trabajar:
   `python -m claude_retain search "<nombre-del-proyecto>"`
   Si hay resultados relevantes, mencionarlos brevemente ("Recuerdo que la última vez...") y no volver a preguntar al usuario lo que ya está guardado.
2. **Al terminar una tarea importante o tomar una decisión relevante** → guardar memoria (comando `save_memory` abajo). wing = proyecto, room = tema.
3. **Trabajo riesgoso** (refactor grande, migración, borrados) → crear checkpoint antes; `rewind` SOLO con confirmación explícita del usuario.
4. **No abusar**: 1 búsqueda al inicio + 1 guardado por hito. Cada llamada cuesta ~2-10 s (carga de embeddings). En sesiones triviales (preguntas simples, sin proyecto) no usar.

## Comandos (ejecutar desde la carpeta del clon — funciona en PowerShell y Bash)

```powershell
# Ve a la carpeta del clon una sola vez (PowerShell o Bash):
cd <ruta-a-tu-clon>

# Estado general (capas L0-L3, grafo, cache)
python -m claude_retain stats

# Buscar en memoria (BM25 + embeddings). Siempre antes de preguntar por contexto pasado.
python -m claude_retain search "<consulta>"

# Guardar una memoria. wing = proyecto, room = tema.
python -c "import sys; sys.path.insert(0,'.'); from claude_retain.memory import MemoryManager; mm=MemoryManager(); ok=mm.initialize(); print('init:',ok); r=mm.save_memory(content='<resumen de la decision/aprendizaje>', wing='<proyecto>', room='<tema>'); print('save:',r)"

# Capas / grafo / checkpoints
python -m claude_retain layers
python -m claude_retain graph [entidad]
python -m claude_retain checkpoints
python -m claude_retain replay <checkpoint_id>    # ver sin restaurar
python -m claude_retain rewind <checkpoint_id>   # RESTAURAR (pedir confirmacion al usuario)
```

Si el agente corre en sandbox que no permite escribir en `~/.claude-retain`, pedir permiso de escalado para esos comandos.

## Convenciones de memoria

- `wing` = proyecto o dominio (`codex`, `bot_asimetrico`, `llama_app`)
- `room` = tema dentro del wing (`integracion`, `debug`, `decisiones`)
- Contenido: 1-3 frases concretas (qué se decidió, por qué, estado). No volcar conversaciones.

## Notas conocidas

- Windows: la consola usa cp1252 y los drawers contienen BOM/unicode → `cli.py` fuerza UTF-8 (`reconfigure`) para que `search` no crashee con `UnicodeEncodeError`. Si aparece ese error, el clon está desactualizado.
- Los resultados de búsqueda muestran `Sim:` (similitud); 0.000 = match solo BM25 o drawer sin embedding.
- El LLM cache (`llm-cache-stats`) es para Claude Code; desde otros agentes no se usa.

