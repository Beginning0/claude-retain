---
name: memory-time-travel
description: Cuando el agente necesita debuggear un error y quiere revisar estados anteriores de la memoria, crear bifurcaciones para probar soluciones, o ver qué recuerdos existían en un punto anterior. Inspirado en Memvid (https://github.com/memvid/memvid) Time-Travel Debugging.
allowed-tools: [Bash]
---

## Time-Travel Debugging — Rewind, Replay y Branch

Cuando aparece un error (ej: `signalSide is not defined`), el agente puede revisar estados anteriores de la memoria para encontrar cuándo se corrompió o cuándo se perdió información.

### Comandos disponibles

| Comando | Descripción |
|---------|------------|
| `!claude-retain checkpoints` | Listar todos los checkpoints |
| `!claude-retain rewind <id>` | Restaurar memoria a un checkpoint anterior |
| `!claude-retain branch --from=<id> --name=<nombre>` | Crear bifurcación para probar soluciones |
| `!claude-retain replay <id>` | Ver recuerdos de un checkpoint sin restaurar |
| `!claude-retain delete-checkpoint <id>` | Eliminar un checkpoint |

### Flujo de Time-Travel Debugging

```
ERROR detectado (ej: signalSide is not defined)
  ↓
1. !claude-retain checkpoints → ¿qué checkpoints hay?
2. !claude-retain replay <id> → ¿qué recuerdos existían en ese punto?
3. Si es útil, !claude-retain rewind <id> → restaurar a ese estado
4. Si quieres probar una solución sin perder el actual:
   !claude-retain branch --from=<id> --name=fix-signalSide
5. Hacer cambios en la bifurcación y probar
6. Si funciona, !claude-retain rewind <branch_id> → restaurar la solución
```

### Ejemplo de debugging con Time-Travel

```bash
# 1. Ver checkpoints disponibles
!claude-retain checkpoints

# Resultado:
# Checkpoints (5 total):
#   ckpt_1722800000 — 2026-08-05 14:30:00 (42 drawers)
#   ckpt_1722799000 — 2026-08-05 14:20:00 (38 drawers)
#   ckpt_1722798000 — 2026-08-05 14:10:00 (35 drawers)

# 2. Ver qué recuerdos existían en el checkpoint de antes del error
!claude-retain replay ckpt_1722798000

# Resultado:
# Replay de ckpt_1722798000:
#   Checkpoint: ckpt_1722798000
#   Fecha: 2026-08-05 14:10:00
#   Label: after-save-141000
#   Drawers: 35

# 3. Si ese checkpoint tiene la info que necesitas, restaura a él
!claude-retain rewind ckpt_1722798000

# Resultado:
# [Checkpoint] Rewind exitoso — ckpt_1722798000
# [Checkpoint] Memoria restaurada a ckpt_1722798000

# 4. O crea una bifurcación para probar la solución sin perder el estado actual
!claude-retain branch --from=ckpt_1722798000 --name=fix-signalSide

# Resultado:
# [Checkpoint] Bifurcación creada: branch_fix_signalSide_...

# 5. Después de probar la solución en la bifurcación:
!claude-retain rewind branch_fix_signalSide_*
```

### Anti-patrones a evitar

| Anti-patrón | Patrón correcto |
|---|---|
| No revisar checkpoints antes de hacer cambios | Ver checkpoints → replay → decidir si rewind es útil |
| Hacer rewind sin verificar primero | Usar replay para ver el estado del checkpoint |
| No crear bifurcación para probar soluciones | Usar branch para mantener el estado actual intacto |

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

### Ejemplo: output correcto vs incorrecto

❌ Mal: "Voy a revisar los checkpoints para ver cuál tiene la información que necesitamos. Primero voy a listar los checkpoints disponibles..."
✅ Bien: `!claude-retain checkpoints → 5 checkpoints, el más reciente tiene 42 drawers`

❌ Mal: "En resumen, vimos que hay un checkpoint útil y vamos a restaurarlo"
✅ Bien: `Rewind: ckpt_1722798000 (35 drawers) — memoria restaurada`

