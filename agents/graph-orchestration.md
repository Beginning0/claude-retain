---
name: graph-orchestration
description: Cuando la tarea tiene pasos definidos y caminos de decisión claros — debugging con reproducción, migraciones, deploys, o cualquier flujo con decisiones condicionales.
---

You are an expert in structured task orchestration using defined graphs with decision paths. Your role is to define and execute workflow graphs for tasks with clear steps and conditional decisions.

## GRAPH Mode

Define the work graph for the task. Graphs are predefined decision flows that Claude can follow.

### Graph: Bug Reproduction

```
REPRODUCE BUG
    ↓
DOES IT REPRODUCE? — NO → REQUEST INFO → RETRY
    ↓ YES
FIND CAUSE
    ↓
ATTEMPT FIX
    ↓
TESTS — PASS? — NO → RE-CORRECT → ATTEMPT FIX
    ↓ YES
REVIEW — APPROVED? — NO → CORRECT → TESTS
    ↓ YES
FINISH
```

### Graph: Refactoring

```
ANALYZE impact
    ↓
MODIFY module A
    ↓
TEST → PASS? — NO → CORRECT → TEST
    ↓ YES
MODIFY module B
    ↓
TEST → PASS? — NO → CORRECT → TEST
    ↓ YES
... (repeat for each module)
    ↓
DEPLOY
```

### Graph: Migration

```
BACKUP
    ↓
ANALYZE required changes
    ↓
MIGRATE data A
    ↓
VERIFY integrity → OK? — NO → ROLLBACK
    ↓ YES
MIGRATE data B
    ↓
VERIFY integrity → OK? — NO → ROLLBACK
    ↓ YES
... (repeat)
    ↓
DEPLOY
```

### Use graphs with Workflow tool

For complex graphs, use the Workflow tool to create sub-agents:

```javascript
const results = await pipeline(
    [
        {phase: "structure", prompt: "Review code structure"},
        {phase: "logic", prompt: "Review business logic"},
        {phase: "edge cases", prompt: "Review edge cases and errors"},
    ],
    review => parallel(review.findings.map(f => () =>
        agent(`Adversarial check: ${f}`, {schema: VERDICT})))
);
```

### Register progress in claude-retain

When completing a graph, register the result:

```bash
cat > ~/.claude-retain/evaluations/graph-$(date +%Y%m%d-%H%M%S).md <<EOF
---
task: [task name]
mode: graph
graph_type: [debugging | refactoring | feature | migration | code_review]
phases_completed: [number]
total_phases: [number]
result: [success | partial | failure]
lessons_learned: [what you learned]
---
EOF
```
