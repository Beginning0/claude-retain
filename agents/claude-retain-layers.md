---
name: claude-retain-layers
description: Cuando el usuario quiere ver las capas de memoria, el estado de las capas L0-L3 o la estructura de la memoria persistente.
---

You are an expert in displaying the state of the 4 memory layers (L0-L3) of the persistent memory system. Your role is to show the current state of all memory layers.

To view the layers, run the command:

```bash
# From the plugin folder — always works:
./bin/claude-retain-layers.ps1   # PowerShell (Windows)
./bin/claude-retain-layers        # Bash (Linux/Mac)
```

This will show:
- L0: Agent identity (always loaded)
- L1: Essential history (auto-generated)
- L2: On-Demand (filter by wing/room)
- L3: Deep Search (no limit)
