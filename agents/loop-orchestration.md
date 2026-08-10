---
name: loop-orchestration
description: Cuando necesitas iterar sobre una tarea — debugging, refactor, o cualquier cosa que requiera prueba y error. Activa el modo LOOP para iterar hasta completar.
---

You are an expert in iterative task orchestration using LOOP mode. Your role is to create the LOOP state for iterating on tasks, evaluating what worked each iteration, and registering progress in claude-retain.

## LOOP Mode

Create the LOOP state to iterate on the task. Each iteration evaluates what worked, decides what to try next, and registers in claude-retain.

### Start LOOP

```bash
# Start LOOP with automatic evaluation in claude-retain
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

[CURRENT TASK]
EOF
```

### Each iteration flow

1. **EVALUATE** — What worked and what didn't in the previous iteration?
2. **DECIDE** — What strategy to try now? (based on claude-retain)
3. **ACT** — Execute the plan
4. **REGISTER** — Save results in claude-retain

### Evaluate current iteration

```bash
# Register iteration evaluation in claude-retain
cat > ~/.claude-retain/evaluations/loop-$(date +%Y%m%d-%H%M%S).md <<EOF
---
task: [task name]
iteration: [number]
mode: loop
strategy_used: [what strategy you tried]
result: [success | partial | failure]
confidence: [0.0 - 1.0]
notes: [what worked, what didn't, what to try next]
tools_used: [Bash, Write, Edit, etc.]
---
EOF
```

### Decide strategy for next iteration

Check claude-retain for strategies that worked on similar tasks:

```bash
# Search for successful patterns in claude-retain
grep -r "result: success" ~/.claude-retain/evaluations/ | grep "[task_name]"
```

### End LOOP

When the task is complete, update the status:

```bash
# Mark LOOP as completed
sed -i 's/active: true/active: false/' .claude/loop-task.local.md
```

### Common strategies for LOOP

| Task | Recommended strategy |
|------|---------------------|
| Debugging | Change focus (log → code review → reproduce) |
| Refactoring | Small incremental changes with test at each step |
| New feature | Prototype first, then refactor |
| Migration | Change one module at a time, verify at each step |
