---
name: project-knowledge-hub
description: Hub de conocimiento del proyecto — muestra cuánto sabe el graph sobre cada archivo, entidades conocidas y gaps de información.
---

You are an expert in showing the project knowledge hub — how much the project graph knows about each file, known entities, and information gaps. Your role is to display a summary of everything the project graph knows, organized by files.

## Project Knowledge Hub

Shows a summary of everything the project graph knows, organized by files. Useful for quickly seeing what information is available without reading each file.

### Main commands

**1. Complete hub — overview of all knowledge:**
```bash
# Rebuild the entire graph without asking for confirmation
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell (Windows)
./bin/claude-retain-build-graph --auto         # Bash (Linux/Mac)
```

**2. Structural query of a specific file:**
```bash
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash
# Shows: imports, definitions, relationships of this file
```

**3. Semantic query — search by concept:**
```bash
./bin/claude-retain-project-graph.ps1 query_semantic "authentication"   # PowerShell
./bin/claude-retain-project-graph query_semantic "authentication"        # Bash
# Returns relevant files by semantic similarity
```

**4. Project overview:**
```bash
./bin/claude-retain-project-graph.ps1 overview   # PowerShell
./bin/claude-retain-project-graph overview        # Bash
# Shows: nodes, edges, project type, cruxes
```

### What the hub shows

| Information | Command |
|---|---|
| Indexed files and their status | `build-graph` (no arguments) |
| File imports | `query_structural "file"` → imports |
| Definitions (functions/classes) | `query_structural "file"` → defines |
| Inheritance relationship | `query_structural "file"` → extends |
| Files that import this | `query_structural "file"` → imported_by |
| Semantic summary of file | `query_semantic "file"` |
| Cruxes (core logic) | `overview` → cruxes files |

### Gaps — What the graph doesn't know

If a file doesn't appear in the results, it could mean:
1. **Not indexed** — run `build-graph` to index it
2. **In the graph but no prior queries** — the agent never queried it
3. **Compacted** — moved to `~/.claude-retain/project_graph/compacted/`
