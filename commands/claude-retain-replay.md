---
name: claude-retain-replay
description: Ver recuerdos de un checkpoint sin restaurar (Time-Travel Debugging)
---

Muestra los recuerdos que existían en un checkpoint específico sin restaurar la memoria a ese estado.

Ejecuta el comando con el ID del checkpoint:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-replay.ps1 <checkpoint_id>    # PowerShell (Windows)
./bin/claude-retain-replay <checkpoint_id>         # Bash (Linux/Mac)
```

Ejemplo: `!claude-retain replay ckpt_1722800000`

Útil para verificar qué información existía en un punto anterior antes de hacer un rewind.
