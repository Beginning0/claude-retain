---
name: claude-retain-debug-first-graph
description: Debug — consultar graph ANTES de leer archivos, usar sub-agentes en paralelo
---

Modo de debugging que consulta el graph del proyecto ANTES de leer archivos, y usa sub-agentes para investigación paralela.

Ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-debug-first-graph.ps1    # PowerShell (Windows)
./bin/claude-retain-debug-first-graph         # Bash (Linux/Mac)
```

Flujo:
1. Construir/verificar graph del proyecto
2. Buscar el error en memoria antes de leer
3. Usar sub-agentes para investigación paralela
4. Consultar graph para entender dependencias
5. Solo después, leer archivos específicos relevantes
