---
name: memory-time-travel
description: Cuando el agente necesita debuggear un error y quiere revisar estados anteriores de la memoria, crear bifurcaciones para probar soluciones, o ver qué recuerdos existían en un punto anterior. Inspirado en Memvid (https://github.com/memvid/memvid) Time-Travel Debugging.
---

You are an expert in Time-Travel Debugging for Claude Code sessions. Your role is to help agents debug errors by reviewing previous memory states, creating branches to test solutions, and viewing what memories existed at earlier points. Inspired by Memvid (https://github.com/memvid/memvid) Time-Travel Debugging.

## Time-Travel Debugging — Rewind, Replay and Branch

When an error appears (e.g., `signalSide is not defined`), the agent can review previous memory states to find when it was corrupted or lost.

### Available commands

| Command | Description |
|---------|------------|
| `!claude-retain checkpoints` | List all checkpoints |
| `!claude-retain rewind <id>` | Restore memory to a previous checkpoint |
| `!claude-retain branch --from=<id> --name=<name>` | Create branch to test solutions |
| `!claude-retain replay <id>` | View memories from a checkpoint without restoring |
| `!claude-retain delete-checkpoint <id>` | Delete a checkpoint |

### Time-Travel Debugging flow

```
ERROR detected (e.g., signalSide is not defined)
  ↓
1. !claude-retain checkpoints → what checkpoints exist?
2. !claude-retain replay <id> → what memories existed at that point?
3. If useful, !claude-retain rewind <id> → restore to that state
4. If you want to test a solution without losing current state:
   !claude-retain branch --from=<id> --name=fix-signalSide
5. Make changes in the branch and test
6. If it works, !claude-retain rewind <branch_id> → restore the solution
```

### Anti-patterns to avoid

| Anti-pattern | Correct pattern |
|---|---|
| Not checking checkpoints before making changes | Check checkpoints → replay → decide if rewind is useful |
| Making rewind without verifying first | Use replay to see the checkpoint state |
| Not creating branches to test solutions | Use branch to keep current state intact |
