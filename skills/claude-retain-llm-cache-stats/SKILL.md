---
name: claude-retain-llm-cache-stats
description: Cuando el usuario quiere ver las estadísticas del cache de respuestas LLM, los hits del cache o el tamaño de la base de datos.
allowed-tools: [Bash]
---

Muestra las estadísticas del cache de respuestas LLM — cuántas respuestas están cacheadas, hits, tamaño de la base de datos SQLite.

Para ver las estadísticas del cache LLM, ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-llm-cache-stats.ps1   # PowerShell (Windows)
./bin/claude-retain-llm-cache-stats        # Bash (Linux/Mac)
```

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

