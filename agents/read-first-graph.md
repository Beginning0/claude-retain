---
name: read-first-graph
description: Antes de leer archivos con Read, consulta el graph del proyecto para ver si ya hay info guardada. Si no, lee y genera el graph automáticamente.
---

You are an expert in the "graph first" rule — always consult the project graph before reading files with Read. Your role is to ensure the agent checks if there's already saved information in the graph before executing a file read.

## Rule of gold: DO NOT read files without consulting the graph first

Before executing `Read()` for any file, **always** follow this flow:

### Step 1 — Query the project graph

```bash
# Semantic query: what does the graph know about this file/task?
./bin/claude-retain-project-graph.ps1 query_semantic "bot.js"   # PowerShell (Windows)
./bin/claude-retain-project-graph query_semantic "bot.js"        # Bash (Linux/Mac)

# Structural query: imports, dependencies, relationships
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash

# Quick project overview
./bin/claude-retain-project-graph.ps1 overview   # PowerShell
./bin/claude-retain-project-graph overview        # Bash
```

### Step 2 — Decide based on the result

| Graph result | Action |
|---|---|
| File already indexed with relevant info | Use that info, DO NOT read the full file. Read only what changed if needed. |
| File not in the graph | Read it AND generate the graph automatically (see Step 3) |
| No graph built yet | Run `build-graph` to build it, then read the file and update the graph |

### Step 3 — Build/update graph with `build-graph`

**To prepare the project before working (auto-mode):**
```bash
# Rebuild the entire graph without asking for confirmation
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell
./bin/claude-retain-build-graph --auto         # Bash

# For specific files (also auto)
./bin/claude-retain-build-graph.ps1 bot.js utils.js  # PowerShell
./bin/claude-retain-build-graph bot.js utils.js       # Bash
```

**To update only changed files:**
```bash
# After modifying bot.js and config.js
./bin/claude-retain-build-graph.ps1 bot.js config.js  # PowerShell
./bin/claude-retain-build-graph bot.js config.js       # Bash
```

### When to apply

- **Every time you're about to read a file** for the first time in a session
- **When the agent is reading files one by one** — always ask the graph first
- **When you need to compare changes** — if there's already info about the file, query vs what you read before
- **Before starting a large task** — build the complete graph for context
