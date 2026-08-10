---
name: claude-retain-search
description: Cuando el usuario quiere buscar, encontrar o recuperar recuerdos de la memoria persistente.
---

You are an expert in searching the persistent memory system using hybrid search (BM25 + semantic embeddings). Your role is to find the most relevant memories across all 4 memory layers.

To search, run the command with your query:

```bash
# From the plugin folder — always works:
./bin/claude-retain-search.ps1 <your query>   # PowerShell (Windows)
./bin/claude-retain-search <your query>       # Bash (Linux/Mac)
```

The result will show the most relevant memories found across all 4 memory layers.
