---
name: loop-orchestration
description: Cuando necesitas iterar sobre una tarea — debugging, refactor, o cualquier cosa que requiera prueba y error. Activa el modo LOOP para iterar hasta completar.
allowed-tools: [Bash]
---

## Modo LOOP

Crea el estado de LOOP para iterar sobre la tarea. Cada iteración evalúa qué funcionó, decide qué intentar, y registra en claude-retain.

### Iniciar LOOP

```bash
# Iniciar LOOP con evaluación automática en claude-retain
cat > .claude/loop-task.local.md <<EOF
---
active: true
iteration: 1
max_iterations: 20
completion_promise: "TASK COMPLETE"
mode: loop
strategy: auto-discover
tools_available: []
evaluations: []
started_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
---

[TAREA ACTUAL]
EOF
```

### Flujo de cada iteración

1. **EVALUAR** — ¿Qué funcionó y qué no en la iteración anterior?
2. **DECIDIR** — ¿Qué estrategia intentar ahora? (basado en claude-retain)
3. **ACTUAR** — Ejecutar el plan
4. **REGISTRAR** — Guardar resultados en claude-retain

### Evaluar iteración actual

```bash
# Registrar evaluación de la iteración actual en claude-retain
cat > ~/.claude-retain/evaluations/loop-$(date +%Y%m%d-%H%M%S).md <<EOF
---
task: [nombre de la tarea]
iteration: [número]
mode: loop
strategy_used: [qué estrategia intentaste]
result: [success | partial | failure]
confidence: [0.0 - 1.0]
notes: [qué funcionó, qué no, qué intentar después]
tools_used: [Bash, Write, Edit, etc.]
---
EOF
```

### Decidir estrategia para la siguiente iteración

Revisa claude-retain para ver qué estrategias funcionaron en tareas similares:

```bash
# Buscar patrones exitosos en claude-retain
grep -r "result: success" ~/.claude-retain/evaluations/ | grep "[task_name]"
```

### Terminar LOOP

Cuando la tarea está completa, actualiza el estado:

```bash
# Marcar LOOP como completado
sed -i 's/active: true/active: false/' .claude/loop-task.local.md
```

### Estrategias comunes para LOOP

| Tarea | Estrategia recomendada |
|-------|----------------------|
| Debugging | Cambiar enfoque (log → code review → reproduce) |
| Refactoring | Pequeños cambios incrementales con test en cada paso |
| Feature nueva | Prototipar primero, luego refactorizar |
| Migration | Cambiar un módulo a la vez, verificar en cada paso |

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

