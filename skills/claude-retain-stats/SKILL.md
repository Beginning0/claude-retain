---
name: claude-retain-stats
description: Cuando el usuario pide ver estadísticas de memoria, cache LLM, uso de tokens o datos del sistema de memoria persistente.
allowed-tools: [Bash]
---

Muestra las estadísticas de la memoria persistente del agente (4 capas L0-L3) y del cache LLM.

Para ver las estadísticas, ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-stats.ps1    # PowerShell (Windows)
./bin/claude-retain-stats         # Bash (Linux/Mac)
```

Si no está disponible, muestra un mensaje indicando que el plugin no está instalado correctamente o que claude-retain no está instalado.

**También incluye:**
- Estado del graph del proyecto (nodos/aristas si existe)
- Cantidad de archivos indexados en el graph semántico

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

