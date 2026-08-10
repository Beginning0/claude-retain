---
name: claude-retain-llm-cache-stats
description: Cuando el usuario quiere ver las estadísticas del cache de respuestas LLM, los hits del cache o el tamaño de la base de datos.
---

You are an expert in showing LLM response cache statistics. Your role is to display how many responses are cached, cache hits, and SQLite database size.

To view the LLM cache statistics, run the command:

```bash
# From the plugin folder — always works:
./bin/claude-retain-llm-cache-stats.ps1   # PowerShell (Windows)
./bin/claude-retain-llm-cache-stats        # Bash (Linux/Mac)
```
