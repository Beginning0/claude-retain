---
name: claude-retain-delete-checkpoint
description: Eliminar un checkpoint de memoria
---

Elimina un checkpoint específico de la memoria persistente.

Ejecuta el comando con el ID del checkpoint:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-delete-checkpoint.ps1 <checkpoint_id>    # PowerShell (Windows)
./bin/claude-retain-delete-checkpoint <checkpoint_id>         # Bash (Linux/Mac)
```

Ejemplo: `!claude-retain delete-checkpoint ckpt_1722800000`
