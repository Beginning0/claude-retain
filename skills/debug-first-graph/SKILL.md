---
name: debug-first-graph
description: Cuando el agente necesita debuggear un error en el proyecto — siempre consulta el graph ANTES de leer archivos, usa sub-agentes para paralelizar investigación, y consulta memoria antes de repetir lecturas.
allowed-tools: [Bash]
---

## Regla de oro para debugging: NO leas archivos sin consultar el graph primero

Cuando un error aparece (ej: `signalSide is not defined`), **siempre** sigue este flujo:

### Paso 1 — Construir/verificar el graph del proyecto

```bash
# Si no existe o está vacío — construirlo
./bin/claude-retain-build-graph.ps1    # PowerShell
./bin/claude-retain-build-graph         # Bash

# Verificar qué sabe el graph sobre el archivo
./bin/claude-retain-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-graph query_structural "bot.js"        # Bash
```

### Paso 2 — Buscar el error en memoria antes de leer

```bash
# Buscar si ya se reportó este error antes
!claude-retain search "signalSide is not defined"
# o
./bin/claude-retain-search.ps1 "signalSide is not defined"   # PowerShell
./bin/claude-retain-search "signalSide is not defined"        # Bash
```

### Paso 3 — Usar sub-agentes para investigación paralela

**NO leas archivos uno por uno.** Para tareas de debugging, spawn sub-agentes que investiguen en paralelo:

```javascript
// Patrón: investigación paralela del error
const DIMENSIONS = [
    { key: "scope", prompt: "Buscar todas las referencias a signalSide en el proyecto" },
    { key: "flow", prompt: "Trazar el flujo de ejecución que lleva al error en analyzeStrategyLoop" },
    { key: "cache", prompt: "Verificar si macdCrossCache podría estar causando el problema" },
];

const results = await parallel([
    agent(DIMENSIONS[0].prompt, { schema: FINDINGS_SCHEMA }),
    agent(DIMENSIONS[1].prompt, { schema: FINDINGS_SCHEMA }),
    agent(DIMENSIONS[2].prompt, { schema: FINDINGS_SCHEMA }),
]);
```

### Paso 4 — Consultar el graph para entender dependencias

```bash
# ¿Qué archivos importan bot.js?
./bin/claude-retain-graph.ps1 query_structural "bot.js" | imported_by

# ¿Qué funciones se definen en bot.js?
./bin/claude-retain-graph.ps1 query_structural "bot.js" | defines
```

### Paso 5 — Solo si necesitas más detalle, leer archivos específicos

Después de los pasos 1-4, solo lee **los archivos que el graph identificó como relevantes**, no todos.

## Anti-patrones a evitar

| Anti-patrón | Patrón correcto |
|---|---|
| Leer archivo línea por línea | Consultar graph → leer solo lo relevante |
| Investigar secuencialmente (10 reads) | Sub-agentes en paralelo (3 agentes) |
| No consultar memoria antes de leer | Verificar si ya hay info del error |
| No construir graph primero | Construir graph → usarlo como mapa |

## Flujo completo de debugging

```
ERROR: signalSide is not defined
  ↓
1. build-graph → ¿qué archivos hay?
2. search "signalSide" → ¿ya se reportó este error?
3. query_structural "bot.js" → ¿qué funciones/imports tiene?
4. parallel agents:
   - Buscar todas las referencias a signalSide
   - Trazar flujo de ejecución
   - Verificar variables cache
5. Leer solo archivos relevantes (no todos)
6. Fix + test
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

## Sub-agentes para debugging

Cuando el error es complejo, usar Workflow tool con sub-agentes:

```javascript
// Debugging: investigación paralela del error
const DIMENSIONS = [
    { key: "scope", prompt: "Buscar todas las referencias a signalSide en TODO el proyecto" },
    { key: "flow", prompt: "Trazar el flujo de ejecución de analyzeStrategyLoop hasta el error" },
    { key: "cache", prompt: "Verificar si macdCrossCache o marketCache causan el problema" },
];

const results = await parallel([
    agent(DIMENSIONS[0].prompt, { label: "scope:sigSide", schema: FINDINGS_SCHEMA }),
    agent(DIMENSIONS[1].prompt, { label: "flow:analyzeLoop", schema: FINDINGS_SCHEMA }),
    agent(DIMENSIONS[2].prompt, { label: "cache:macdCross", schema: FINDINGS_SCHEMA }),
]);

// Verificación adversarial del resultado
const confirmed = (await parallel(results.flat().map(f => () =>
    agent(`Verificar: ${f.description} — ¿es real o falso positivo?`,
          { schema: VERDICT }))).filter(Boolean).filter(v => v.isReal));
```

