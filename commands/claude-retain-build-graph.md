---
name: claude-retain-build-graph
description: Construir/actualizar el graph del proyecto — sin argumentos muestra archivos y pide confirmación
---

Construye o actualiza el graph de conocimiento del proyecto — nodos (archivos, funciones, clases) y aristas (importaciones, dependencias).

Ejecuta el comando:

```bash
# Sin argumentos — muestra archivos disponibles y pide confirmación:
./bin/claude-retain-build-graph.ps1    # PowerShell (Windows)
./bin/claude-retain-build-graph         # Bash (Linux/Mac)

# Con archivos específicos — actualiza solo esos:
./bin/claude-retain-build-graph.ps1 bot.js utils.js    # PowerShell (Windows)
./bin/claude-retain-build-graph bot.js utils.js         # Bash (Linux/Mac)

# Auto-mode — reconstruye TODO sin pedir confirmación:
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell (Windows)
./bin/claude-retain-build-graph --auto         # Bash (Linux/Mac)
```

El graph permite consultas semánticas (ChromaDB) y estructurales (SQLite).
