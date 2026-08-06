---
name: claude-retain-layers
description: Cuando el usuario quiere ver las capas de memoria, el estado de las capas L0-L3 o la estructura de la memoria persistente.
allowed-tools: [Bash]
---

Muestra el estado actual de las 4 capas de memoria persistente del agente.

Para ver las capas, ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-layers.ps1   # PowerShell (Windows)
./bin/claude-retain-layers        # Bash (Linux/Mac)
```

Esto mostrará:
- L0: Identidad del agente (siempre cargado)
- L1: Historia esencial (auto-generada)
- L2: On-Demand (filtro por ala/habitación)
- L3: Deep Search (sin límite)

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

