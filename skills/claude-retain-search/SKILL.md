---
name: claude-retain-search
description: Cuando el usuario quiere buscar, encontrar o recuperar recuerdos de la memoria persistente.
allowed-tools: [Bash]
---

Busca en la memoria persistente del agente usando búsqueda híbrida (BM25 + embeddings).

Para buscar, ejecuta el comando:

```bash
# Desde la carpeta del plugin — siempre funciona:
./bin/claude-retain-search.ps1 <tu consulta>   # PowerShell (Windows)
./bin/claude-retain-search <tu consulta>       # Bash (Linux/Mac)
```

El resultado mostrará los recuerdos más relevantes encontrados en las 4 capas de memoria.

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

