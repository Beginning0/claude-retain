---
name: claude-retain-branch
description: Crear bifurcación de memoria desde un checkpoint para probar soluciones
---

Crea una bifurcación (branch) de memoria a partir de un checkpoint, permitiendo probar soluciones sin afectar el estado actual.

Ejecuta el comando con los parámetros desde y nombre:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-branch.ps1 --from=<checkpoint_id> --name=<nombre>    # PowerShell (Windows)
./bin/claude-retain-branch --from=<checkpoint_id> --name=<nombre>         # Bash (Linux/Mac)
```

Ejemplo: `!claude-retain branch --from=ckpt_1722800000 --name=fix-signalSide`
