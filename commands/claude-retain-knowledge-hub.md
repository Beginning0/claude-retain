---
name: claude-retain-knowledge-hub
description: Hub de conocimiento — cuánto sabe el graph sobre cada archivo y gaps de información
---

Muestra un resumen de todo lo que el graph del proyecto conoce, organizado por archivos. Útil para ver rápidamente qué información está disponible sin leer cada archivo.

Ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-knowledge-hub.ps1    # PowerShell (Windows)
./bin/claude-retain-knowledge-hub         # Bash (Linux/Mac)
```

Muestra para cada archivo: imports, definiciones, relaciones, y si hay gaps de información.
