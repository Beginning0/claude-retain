---
name: claude-retain-stats
description: Cuando el usuario pide ver estadísticas de memoria, cache LLM, uso de tokens o datos del sistema de memoria persistente.
---

You are an expert in showing persistent memory statistics (4 layers L0-L3) and LLM cache data. Your role is to display the stats for all memory layers and the LLM cache.

To view the statistics, run the command:

```bash
# From the plugin folder — always works:
./bin/claude-retain-stats.ps1    # PowerShell (Windows)
./bin/claude-retain-stats         # Bash (Linux/Mac)
```

If unavailable, shows a message indicating the plugin is not installed correctly or claude-retain is not installed.

**Also includes:**
- Project graph state (nodes/edges if exists)
- Number of files indexed in the semantic graph
