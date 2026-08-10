---
name: claude-retain-llm-cache-clear
description: Cuando el usuario quiere limpiar, borrar o eliminar entradas del cache de respuestas LLM.
---

You are an expert in clearing the LLM response cache. Your role is to remove expired entries from the LLM response cache.

To clear the cache, run the command:

```bash
# From the plugin folder — always works:
./bin/claude-retain-llm-cache-clear.ps1   # PowerShell (Windows)
./bin/claude-retain-llm-cache-clear        # Bash (Linux/Mac)
```

This removes all cached responses that have exceeded their TTL (default 24 hours).
