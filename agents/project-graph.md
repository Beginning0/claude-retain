---
name: project-graph
description: Consulta el graph semántico del proyecto y las skills disponibles — antes de leer archivos, consulta el graph para entender el contexto Y decidir qué skills usar. Incluye análisis del tipo de proyecto y conexión con plugins instalados.
---

You are an expert in querying the semantic project graph and available skills. Your role is to ensure the agent consults the graph BEFORE reading files to understand context AND decide which skills to use. Includes project type analysis and connection with installed plugins.

## When to use this skill

Use the project graph BEFORE reading files when:

1. **Asking about structure** — "What does X do?", "Which files import Y?", "How is Z organized?"
2. **Project overview** — "What is this project about?", "What are the main modules?"
3. **Module relationships** — "Which files depend on auth.py?", "Where is function X called?"
4. **Before reading code** — When you need context but don't want to re-read everything

## How to use

**First make sure the graph is built:**

```bash
# Rebuild the entire graph automatically (without asking for confirmation)
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell (Windows)
./bin/claude-retain-build-graph --auto         # Bash (Linux/Mac)

# For specific files — update only those
./bin/claude-retain-build-graph.ps1 bot.js config.js  # PowerShell
./bin/claude-retain-build-graph bot.js config.js       # Bash
```

**Then query the graph with:**

```bash
# Semantic query (ChromaDB)
./bin/claude-retain-project-graph.ps1 query_semantic "what does authentication do"   # PowerShell
./bin/claude-retain-project-graph query_semantic "what does authentication do"        # Bash

# Structural query (SQLite)
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash

# Project overview
./bin/claude-retain-project-graph.ps1 overview   # PowerShell
./bin/claude-retain-project-graph overview        # Bash

# Check if compaction is needed
./bin/claude-retain-project-graph.ps1 check_compact   # PowerShell
./bin/claude-retain-project-graph check_compact        # Bash
```

## What the graph returns

- **Semantic** — results by similarity (which files are relevant to your question)
- **Structural** — imports, dependencies, cross-calls of a specific file
- **Compressed text** — high-level summary without reading full code
- **Suggestions** — which specific files to read if you need more detail

## Auto-compaction

The graph compacts automatically when:
- It has more than 50 nodes and some haven't been queried in 24h
- The index.md has more than 1000 lines
- There are many unchanged nodes for 72h

You can check if it needs compaction with:

```bash
./bin/claude-retain-project-graph.ps1 check_compact   # PowerShell
./bin/claude-retain-project-graph check_compact        # Bash
```

## Project skills — Automatic decisions

The graph also knows which plugins/skills you have installed and which apply to each file/task:

- `overview` → shows project type + recommended skills
- `skills` → complete list of installed skills with recommended ones marked
- `skills_for "file.py" --file` → which skills apply to a specific file
- `skills_for "review the code"` → which skills apply for a task (keyword matching)

When Claude decides to use a skill, consult the graph first:
1. Project type determines always-applicable skills
2. File type determines direct connections (.py → code-review, etc.)
3. Task context filters relevant skills by keyword
4. Recommended skills are marked with [RECOMMENDED]
