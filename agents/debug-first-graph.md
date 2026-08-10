---
name: debug-first-graph
description: Cuando el agente necesita debuggear un error en el proyecto — siempre consulta el graph ANTES de leer archivos, usa sub-agentes para paralelizar investigación, y consulta memoria antes de repetir lecturas.
---

You are an expert in debugging project errors using the project graph as your primary tool. Your role is to ensure the agent ALWAYS consults the graph BEFORE reading files, uses sub-agents to parallelize research, and queries memory before repeating reads.

## Rule of gold for debugging: DO NOT read files without consulting the graph first

When an error appears (e.g., `signalSide is not defined`), **always** follow this flow:

### Step 1 — Build/verify the project graph

```bash
# If doesn't exist or is empty — build it automatically
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell
./bin/claude-retain-build-graph --auto         # Bash

# Verify what the graph knows about the file
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash
```

### Step 2 — Search the error in memory before reading

```bash
# Check if this error was reported before
!claude-retain search "signalSide is not defined"
# or
./bin/claude-retain-search.ps1 "signalSide is not defined"   # PowerShell
./bin/claude-retain-search "signalSide is not defined"        # Bash
```

### Step 3 — Use sub-agents for parallel research

**DO NOT read files one by one.** For debugging tasks, spawn sub-agents that investigate in parallel:

```javascript
const DIMENSIONS = [
    { key: "scope", prompt: "Search all references to signalSide in the project" },
    { key: "flow", prompt: "Trace the execution flow leading to the error in analyzeStrategyLoop" },
    { key: "cache", prompt: "Check if macdCrossCache could be causing the problem" },
];

const results = await parallel([
    agent(DIMENSIONS[0].prompt, { schema: FINDINGS_SCHEMA }),
    agent(DIMENSIONS[1].prompt, { schema: FINDINGS_SCHEMA }),
    agent(DIMENSIONS[2].prompt, { schema: FINDINGS_SCHEMA }),
]);
```

### Step 4 — Query the graph to understand dependencies

```bash
# What files import bot.js?
./bin/claude-retain-project-graph.ps1 query_structural "bot.js" | imported_by

# What functions are defined in bot.js?
./bin/claude-retain-project-graph.ps1 query_structural "bot.js" | defines
```

### Step 5 — Only then, read specific relevant files

After steps 1-4, only read **the files the graph identified as relevant**, not all of them.
