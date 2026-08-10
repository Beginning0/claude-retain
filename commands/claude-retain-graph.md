---
name: claude-retain-graph
description: Mostrar grafo de conocimiento — entidades y relaciones del sistema de memoria
---

Muestra el grafo de conocimiento temporal del agente, con entidades y relaciones.

Ejecuta el comando (opcionalmente con una entidad):

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-graph.ps1 [entidad]   # PowerShell (Windows)
./bin/claude-retain-graph [entidad]        # Bash (Linux/Mac)
```

Sin entidad muestra todas las entidades. Con una entidad específica, muestra solo el conocimiento sobre esa entidad.
