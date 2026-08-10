---
name: claude-retain-search
description: Buscar recuerdos en la memoria persistente usando búsqueda híbrida (BM25 + embeddings)
---

Busca en la memoria persistente del agente usando búsqueda híbrida (BM25 + embeddings).

Ejecuta el comando con tu consulta:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-search.ps1 <tu consulta>   # PowerShell (Windows)
./bin/claude-retain-search <tu consulta>       # Bash (Linux/Mac)
```

El resultado mostrará los recuerdos más relevantes encontrados en las 4 capas de memoria.
