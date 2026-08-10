---
name: claude-retain-rewind
description: Restaurar memoria a un checkpoint anterior
---

Restaura la memoria persistente al estado de un checkpoint específico.

Ejecuta el comando con el ID del checkpoint:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-rewind.ps1 <checkpoint_id>    # PowerShell (Windows)
./bin/claude-retain-rewind <checkpoint_id>         # Bash (Linux/Mac)
```

Ejemplo: `!claude-retain rewind ckpt_1722800000`

Esto restaurará la memoria al estado exacto de ese checkpoint.
