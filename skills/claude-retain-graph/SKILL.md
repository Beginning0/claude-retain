---
name: claude-retain-graph
description: Cuando el usuario quiere ver el grafo de conocimiento, las entidades y relaciones del sistema de memoria.
allowed-tools: [Bash]
---

Muestra el grafo de conocimiento temporal del agente, con entidades y relaciones.

Para ver el grafo, ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-graph.ps1 [entidad]   # PowerShell (Windows)
./bin/claude-retain-graph [entidad]        # Bash (Linux/Mac)

# Sin entidad — muestra todas las entidades:
./bin/claude-retain-graph.ps1   # PowerShell
./bin/claude-retain-graph        # Bash
```

Si se proporciona una entidad, muestra solo el conocimiento sobre esa entidad específica. Si no, lista todas las entidades disponibles en el grafo de conocimiento temporal.

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

