---
name: claude-retain-eval
description: Evaluar el resultado de una tarea completada y guardar el patrón en claude-retain para futuras referencias. Se activa al terminar una tarea compleja o cuando se quiere registrar qué funcionó.
---

You are an expert in evaluating Claude Code task completion and saving patterns for future reference. Your role is to record what worked and what didn't after complex tasks so Claude can learn from them later.

## Task Evaluation

When completing a task, record what worked and what didn't so Claude can learn from it in the future.

### Evaluate completed task

```bash
# Evaluate the most recent task in claude-retain
cat > ~/.claude-retain/evaluations/task-$(date +%Y%m%d-%H%M%S).md <<EOF
---
task: [task name]
mode_used: loop | graph | none
graph_type: [debugging | refactoring | feature | migration | code_review]
tools_used: [Bash, Write, Edit, Read, etc.]
result: success | partial | failure
confidence: [0.0 - 1.0]
iterations: [number of iterations if LOOP]
phases: [number of phases if GRAPH]
lessons_learned: [what you learned from this task]
what_worked: [what strategies worked]
what_failed: [what didn't work]
better_approach: [how you'd do it better next time]
---
EOF
```

### Search for past patterns

To decide which mode to use, search claude-retain for what worked before:

```bash
# Search for successful patterns for a similar task type
grep -r "result: success" ~/.claude-retain/evaluations/ | grep "[task_type]"
```

### Recommendation pattern

claude-retain stores in its layers:
- **L0**: Which mode (LOOP/GRAPH) worked best for each task type
- **L1**: What strategies gave good results
- **L2**: Evaluations per iteration/phase — what worked and what didn't
- **L3**: Tool knowledge graph — which tool was used for what
