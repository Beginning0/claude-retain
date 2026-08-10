---
name: claude-retain-llm-cache-clear
description: Limpiar entradas del cache de respuestas LLM
---

Limpia las entradas expiradas del cache de respuestas LLM.

Ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-llm-cache-clear.ps1   # PowerShell (Windows)
./bin/claude-retain-llm-cache-clear        # Bash (Linux/Mac)
```

Esto elimina todas las respuestas cacheadas que han excedido su TTL (por defecto 24 horas).
