---
name: claude-retain-stats
description: Mostrar estadísticas de memoria persistente (4 capas L0-L3) y cache LLM
---

Muestra las estadísticas de la memoria persistente del agente (4 capas L0-L3) y del cache LLM.

Ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-stats.ps1    # PowerShell (Windows)
./bin/claude-retain-stats         # Bash (Linux/Mac)
```

Si no está disponible, muestra un mensaje indicando que el plugin no está instalado correctamente o que claude-retain no está instalado.

**También incluye:**
- Estado del graph del proyecto (nodos/aristas si existe)
- Cantidad de archivos indexados en el graph semántico
