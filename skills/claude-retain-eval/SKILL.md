---
name: claude-retain-eval
description: Evaluar el resultado de una tarea completada y guardar el patrón en claude-retain para futuras referencias. Se activa al terminar una tarea compleja o cuando se quiere registrar qué funcionó.
allowed-tools: [Bash]
---

## Evaluación de Tareas

Al completar una tarea, registra qué funcionó y qué no para que Claude pueda aprender de ello en el futuro.

### Evaluar tarea completada

```bash
# Evaluar la tarea más reciente en claude-retain
cat > ~/.claude-retain/evaluations/task-$(date +%Y%m%d-%H%M%S).md <<EOF
---
task: [nombre de la tarea]
mode_used: loop | graph | none
graph_type: [debugging | refactoring | feature | migration | code_review]
tools_used: [Bash, Write, Edit, Read, etc.]
result: success | partial | failure
confidence: [0.0 - 1.0]
iterations: [número de iteraciones si fue LOOP]
phases: [número de fases si fue GRAPH]
lessons_learned: [qué aprendiste de esta tarea]
what_worked: [qué estrategias funcionaron]
what_failed: [qué no funcionó]
better_approach: [cómo lo harías mejor la próxima vez]
---
EOF
```

### Buscar patrones pasados

Para decidir qué modo usar, busca en claude-retain qué funcionó antes:

```bash
# Buscar patrones exitosos para un tipo de tarea similar
grep -r "result: success" ~/.claude-retain/evaluations/ | grep "[tipo de tarea]"
```

### Patrón de recomendación

claude-retain almacena en sus capas:
- **L0**: Qué modo (LOOP/GRAPH) funcionó mejor para cada tipo de tarea
- **L1**: Qué estrategias dieron buen resultado
- **L2**: Evaluaciones por iteración/fase — qué funcionó y qué no
- **L3**: Grafo de conocimiento de herramientas — qué herramienta se usó para qué

### Ejemplo de evaluación completa

```bash
cat > ~/.claude-retain/evaluations/task-20260802-143000.md <<EOF
---
task: Fix memory leak in auth module
mode_used: loop
tools_used: [Bash, Read, Write, Edit]
result: success
confidence: 0.9
iterations: 5
lessons_learned: "El leak estaba en el session cleanup, no en el login como pensé inicialmente"
what_worked: "Revisar los hooks de session lifecycle fue clave"
what_failed: "Intentar fixear el login primero (fase incorrecta del grafo)"
better_approach: "Ir directo a session lifecycle en tareas de memory leak"
---
EOF
```

### Automatizar evaluación con hook

El hook `claude-retain-loop-update` ya registra evaluaciones automáticamente durante LOOP. Para GRAPH, puedes usar un hook similar o evaluar manualmente al final.

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

