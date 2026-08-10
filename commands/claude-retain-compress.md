---
name: claude-retain-compress
description: Comprimir sesión actual — reduce tokens consumidos
---

Comprime la sesión actual de Claude Code, reduciendo los tokens que se consumirán en sesiones futuras.

Ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-compress.ps1    # PowerShell (Windows)
./bin/claude-retain-compress         # Bash (Linux/Mac)
```

Esto comprime la sesión actual y guarda un resumen que se cargará automáticamente en la próxima sesión.
