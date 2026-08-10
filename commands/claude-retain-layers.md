---
name: claude-retain-layers
description: Mostrar estado de las capas de memoria L0-L3
---

Muestra el estado actual de las 4 capas de memoria persistente del agente.

Ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-layers.ps1   # PowerShell (Windows)
./bin/claude-retain-layers        # Bash (Linux/Mac)
```

Esto mostrará:
- L0: Identidad del agente (siempre cargado)
- L1: Historia esencial (auto-generada)
- L2: On-Demand (filtro por ala/habitación)
- L3: Deep Search (sin límite)
