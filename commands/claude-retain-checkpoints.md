---
name: claude-retain-checkpoints
description: Listar checkpoints de memoria (Time-Travel Debugging)
---

Lista todos los checkpoints de memoria disponibles — puntos de control donde se guardó la memoria persistente.

Ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-checkpoints.ps1    # PowerShell (Windows)
./bin/claude-retain-checkpoints         # Bash (Linux/Mac)
```

El resultado muestra cada checkpoint con su fecha, label y cantidad de drawers.
