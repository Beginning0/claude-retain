---
name: read-first-graph
description: Antes de leer archivos con Read, consulta el graph del proyecto para ver si ya hay info guardada. Si no, lee y genera el graph automáticamente.
allowed-tools: [Bash]
---

## Regla de oro: NO leas archivos sin consultar el graph primero

Antes de ejecutar `Read()` para cualquier archivo, **siempre** sigue este flujo:

### Paso 1 — Consulta el graph del proyecto

```bash
# Query semántico: ¿qué sabe el graph sobre este archivo/tarea?
./bin/claude-retain-project-graph.ps1 query_semantic "bot.js"   # PowerShell (Windows)
./bin/claude-retain-project-graph query_semantic "bot.js"        # Bash (Linux/Mac)

# Query estructural: imports, dependencias, relaciones
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash

# Overview rápido del proyecto
./bin/claude-retain-project-graph.ps1 overview   # PowerShell
./bin/claude-retain-project-graph overview        # Bash
```

### Paso 2 — Decide según el resultado

| Resultado del graph | Acción |
|---|---|
| El archivo ya está indexado con info relevante | Usa esa info, NO leas el archivo completo. Lee solo lo que cambió si es necesario. |
| El archivo no está en el graph | Léelo Y genera el graph automáticamente (ver Paso 3) |
| No hay graph construido aún | Ejecuta `build-graph` para construirlo, luego lee el archivo y actualiza el graph |

### Paso 3 — Construir/actualizar graph con `build-graph`

**Para preparar el proyecto antes de trabajar (auto-mode):**
```bash
# Reconstruye TODO el graph sin pedir confirmación
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell
./bin/claude-retain-build-graph --auto         # Bash

# Para archivos específicos (también auto)
./bin/claude-retain-build-graph.ps1 bot.js utils.js  # PowerShell
./bin/claude-retain-build-graph bot.js utils.js       # Bash
```

**Ejemplo de interacción:**
```bash
# Construir graph completo (sin confirmación)
./bin/claude-retain-build-graph.ps1 --auto
[claude-retain] OK — nodes=42, edges=87

# Actualizar solo archivos que cambiaron
./bin/claude-retain-build-graph.ps1 bot.js config.js
[claude-retain] Graph actualizado para 2 archivo(s):
  ✓ bot.js — 3 aristas
  ✓ config.js — 2 aristas
```

**Para actualizar solo archivos que cambiaron:**
```bash
# Después de modificar bot.js y config.js
./bin/claude-retain-build-graph.ps1 bot.js config.js  # PowerShell
./bin/claude-retain-build-graph bot.js config.js       # Bash
```

### Cuándo aplicar

- **Cada vez que vayas a leer un archivo** por primera vez en una sesión
- **Cuando el agente esté leyendo archivos uno por uno** — siempre pregunta primero al graph
- **Cuando necesites comparar cambios** — si ya hay info del archivo, consulta vs lo que leíste antes
- **Antes de empezar una tarea grande** — construye el graph completo para tener contexto

### Patrón de verificación

Después de leer un archivo, verifica: "¿Ya tengo info de esto en el graph?"
Si la respuesta es sí → no necesitas releer. Si no → genera el graph.

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

