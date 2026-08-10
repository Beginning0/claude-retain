---
name: agent-orchestration
description: Cuando la tarea es compleja, requiere múltiples pasos, investigación, debugging, refactor extenso, o trabajar en un proyecto grande. Detecta automáticamente si necesita LOOP (iterativo) o GRAPH (estructurado).
---

You are an expert in orchestrating complex tasks for Claude Code. Your role is to detect when a task requires multi-step orchestration and choose the right approach: LOOP (iterative) or GRAPH (structured).

## Rule of gold for complex tasks: NEVER read files without consulting the graph first

Before starting any complex task, **always** check if the project graph is built and query it for context.

### Before any reading:

```bash
# Check if graph exists
./bin/claude-retain-project-graph.ps1 overview   # PowerShell
./bin/claude-retain-project-graph overview        # Bash

# If not, build it automatically
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell
./bin/claude-retain-build-graph --auto         # Bash

# Query the graph for context
./bin/claude-retain-project-graph.ps1 query_structural "archivo.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "archivo.js"        # Bash
```

## Agent Orchestration

When the task requires it, use the Workflow tool to create sub-agents that work in parallel and deliver structured results.

### Decide between LOOP and GRAPH

**Use LOOP when:**
- Debugging requiring multiple attempts
- Extensive refactoring
- Features needing trial and error
- Tasks where you don't know the optimal path upfront
- Needing to iterate on a design or implementation

**Use GRAPH when:**
- Bug reproduction with defined steps
- Migrations with clear phases
- Deploys with checklists
- Tasks where you know possible paths upfront
- Need conditional decisions (pass tests? → yes/no)

### Auto-discovery of available tools

Before deciding the mode, discover what tools are available:

```bash
# Execute discovery and build graph automatically
./bin/claude-retain-build-graph.ps1 --auto  # PowerShell
./bin/claude-retain-build-graph --auto       # Bash
```

### Creating sub-agents with Workflow tool

**For independent tasks (parallel):**
```javascript
const results = await parallel([
    agent("Search for signalSide references in the entire project", {schema: FINDINGS_SCHEMA}),
    agent("Trace execution flow of analyzeStrategyLoop", {schema: FINDINGS_SCHEMA}),
    agent("Check if macdCrossCache causes the problem", {schema: FINDINGS_SCHEMA}),
]);
```

**For pipeline tasks (sequential per item):**
```javascript
const results = await pipeline(items, stage1, stage2, stage3);
```

### Adversarial verification pattern

To confirm findings, spawn multiple agents that attempt to refute:
```javascript
const votes = await parallel(Array.from({length: 3}, () => () =>
    agent("Try to refute: this is the cause of the bug", {schema: VERDICT})));
const confirmed = votes.filter(Boolean).filter(v => !v.refuted).length >= 2;
```

### Anti-pattern: DO NOT repeat reads

If you already read information and the graph indexed it, **DO NOT read again**. The PostRead hook generates the graph automatically after each read.
