---
name: agent-orchestration
description: Cuando la tarea es compleja, requiere múltiples pasos, investigación, debugging, refactor extenso, o trabajar en un proyecto grande. Detecta automáticamente si necesita LOOP (iterativo) o GRAPH (estructurado).
allowed-tools: [Bash]
---

## Regla de oro para tareas complejas: NUNCA leas archivos sin consultar el graph primero

Antes de iniciar cualquier tarea compleja, **siempre** verifica si el graph del proyecto está construido y consulta el graph para obtener contexto.

### Antes de cualquier lectura:

```bash
# Verificar si hay graph
./bin/claude-retain-project-graph.ps1 overview   # PowerShell
./bin/claude-retain-project-graph overview        # Bash

# Si no existe, construirlo automáticamente
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell
./bin/claude-retain-build-graph --auto         # Bash

# Consultar el graph para contexto
./bin/claude-retain-project-graph.ps1 query_structural "archivo.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "archivo.js"        # Bash
```

## Orquestación de Agentes

Cuando la tarea lo requiera, usa el Workflow tool para crear sub-agentes que trabajen en paralelo y te entreguen resultados estructurados.

### Decidir entre LOOP y GRAPH

**Usa LOOP cuando:**
- Debugging que requiere múltiples intentos
- Refactoring extenso
- Features que necesitan prueba y error
- Tareas donde no sabes el camino óptimo de antemano
- Necesitas iterar sobre un diseño o implementación

**Usa GRAPH cuando:**
- Reproducción de bugs con pasos definidos
- Migraciones con fases claras
- Deploys con checklist
- Tareas donde conoces los caminos posibles de antemano
- Necesitas decisiones condicionales (¿pasan tests? → sí/no)

### Auto-discovery híbrido de herramientas

Antes de decidir el modo, descubre qué herramientas están disponibles:

```bash
# Ejecutar descubrimiento y construir graph automáticamente
./bin/claude-retain-build-graph.ps1 --auto  # PowerShell
./bin/claude-retain-build-graph --auto       # Bash
```

Registra en claude-retain lo encontrado para futuras referencias:
- Skills instaladas → patrón de qué skills activas
- MCP servers → herramientas disponibles como API
- Hooks → automatizaciones activas

### Creación de sub-agentes con Workflow tool

**Para tareas independientes (paralelo):**
```javascript
// Múltiples agentes investigando diferentes partes del error
const results = await parallel([
    agent("Buscar referencias a signalSide en TODO el proyecto", {schema: FINDINGS_SCHEMA}),
    agent("Trazar flujo de ejecución de analyzeStrategyLoop", {schema: FINDINGS_SCHEMA}),
    agent("Verificar si macdCrossCache causa el problema", {schema: FINDINGS_SCHEMA}),
]);
```

**Para tareas en pipeline (secuencial por ítem):**
```javascript
// Transformar datos paso a paso
const results = await pipeline(items, stage1, stage2, stage3);
```

**Para descubrimiento de bugs/issues:**
```javascript
// Loop-until-dry: encontrar todos los bugs
const bugs = [];
while (budget.total && budget.remaining() > 50_000) {
    const result = await agent("Encontrar bugs en este código", {schema: BUGS_SCHEMA});
    bugs.push(...result.bugs);
}
```

### Patrón de verificación adversarial

Para confirmar hallazgos, spawn múltiples agentes que intenten refutar:
```javascript
const votes = await parallel(Array.from({length: 3}, () => () =>
    agent("Intenta refutar: esta es la causa del bug", {schema: VERDICT})));
const confirmed = votes.filter(Boolean).filter(v => !v.refuted).length >= 2;
```

### Anti-patrón: NO repetir lecturas

Si ya leíste información y el graph la indexó, **NO vuelvas a leer**. El hook PostRead genera automáticamente el graph después de cada lectura. Para obtener info del archivo usa el graph:

```bash
# En vez de volver a leer bot.js:
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash
# → Devuelve imports, definiciones, relaciones SIN leer el archivo
```

### Memorizar patrones exitosos en claude-retain

Al completar una tarea, guarda el patrón para futuras referencias:
- Qué modo (LOOP/GRAPH) funcionó mejor
- Qué herramientas se usaron
- Qué estrategias dieron buen resultado
- Cuántas iteraciones fueron necesarias
- Qué archivos se leyeron (para no repetir)

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

### Ejemplo: output correcto vs incorrecto

❌ Mal: "Voy a buscar las referencias a signalSide en todo el proyecto para ver dónde está causando el error. Primero voy a construir el graph del proyecto..."
✅ Bien: `./bin/claude-retain-project-graph.ps1 query_structural "signalSide" → 3 archivos, 5 referencias`

❌ Mal: "En resumen, encontramos que hay 2 archivos con problemas y vamos a arreglarlos"
✅ Bien: `Fix: 1. signalSide en bot.js (línea 42)  2. obCrossWallContra en analyzer.js (línea 87)`

