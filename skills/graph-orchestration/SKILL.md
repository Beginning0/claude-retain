---
name: graph-orchestration
description: Cuando la tarea tiene pasos definidos y caminos de decisión claros — debugging con reproducción, migraciones, deploys, o cualquier flujo con decisiones condicionales.
allowed-tools: [Bash]
---

## Modo GRAPH

Define el grafo de trabajo para la tarea. Los grafos son flujos de decisión predefinidos que Claude puede seguir.

### Grafo: Debugging (reproducir bug)

```
REPRODUCIR BUG
    ↓
¿LO REPRODUCE? — NO → PEDIR INFO → REINTENTAR
    ↓ SI
HALLAR CAUSA
    ↓
INTENTAR FIX
    ↓
TESTS — ¿PASAN? — NO → VOLVER A CORRIGIR → INTENTAR FIX
    ↓ SI
REVISION — ¿APROBADO? — NO → CORREGIR → TESTS
    ↓ SI
TERMINA
```

### Grafo: Refactoring

```
ANALIZAR impacto
    ↓
MODIFICAR módulo A
    ↓
TESTEAR → ¿PASAN? — NO → CORRIGIR → TESTEAR
    ↓ SI
MODIFICAR módulo B
    ↓
TESTEAR → ¿PASAN? — NO → CORRIGIR → TESTEAR
    ↓ SI
... (repetir para cada módulo)
    ↓
DEPLOY
```

### Grafo: Feature nueva

```
PLANEAR (especificar endpoints, modelos, etc.)
    ↓
IMPLEMENTAR backend
    ↓
TESTEAR API → ¿FUNCIONA? — NO → CORREGIR → TESTEAR
    ↓ SI
IMPLEMENTAR frontend
    ↓
TESTEAR UI → ¿FUNCIONA? — NO → CORREGIR → TESTEAR
    ↓ SI
DEPLOY
```

### Grafo: Migración

```
BACKUP
    ↓
ANALIZAR cambios necesarios
    ↓
MIGRAR datos A
    ↓
VERIFICAR integridad → ¿OK? — NO → ROLLBACK
    ↓ SI
MIGRAR datos B
    ↓
VERIFICAR integridad → ¿OK? — NO → ROLLBACK
    ↓ SI
... (repetir)
    ↓
DEPLOY
```

### Grafo: Code Review

```
LEER archivos cambiados
    ↓
REVIEW estructura → ¿OK? — NO → SUGERIR REESTRUCTURA
    ↓ SI
REVIEW lógica → ¿OK? — NO → SUGERIR CAMBIOS
    ↓ SI
REVIEW edge cases → ¿OK? — NO → SUGERIR FIXES
    ↓ SI
APROBAR
```

### Usar grafos con Workflow tool

Para grafos complejos, usa el Workflow tool para crear sub-agentes:

```javascript
// Grafo: Code Review por fases
const results = await pipeline(
    [
        {phase: "estructura", prompt: "Revisar la estructura del código"},
        {phase: "lógica", prompt: "Revisar la lógica de negocio"},
        {phase: "edge cases", prompt: "Revisar casos borde y errores"},
    ],
    review => parallel(review.findings.map(f => () =>
        agent(`Adversarial check: ${f}`, {schema: VERDICT})))
);
```

### Registrar progreso en claude-retain

Al completar un grafo, registra el resultado:

```bash
cat > ~/.claude-retain/evaluations/graph-$(date +%Y%m%d-%H%M%S).md <<EOF
---
task: [nombre de la tarea]
mode: graph
graph_type: [debugging | refactoring | feature | migration | code_review]
phases_completed: [número]
total_phases: [número]
result: [success | partial | failure]
lessons_learned: [qué aprendiste]
---
EOF
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

