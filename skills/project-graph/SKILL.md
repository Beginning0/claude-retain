---
name: project-graph
description: Consulta el graph semántico del proyecto y las skills disponibles — antes de leer archivos, consulta el graph para entender el contexto Y decidir qué skills usar. Incluye análisis del tipo de proyecto y conexión con plugins instalados.
allowed-tools: [Bash]
---

## Cuándo usar este skill

Usa el graph del proyecto ANTES de leer archivos cuando:

1. **Preguntas sobre la estructura** — "¿Qué hace X?", "¿Qué archivos importan Y?", "¿Cómo está organizado Z?"
2. **Overview del proyecto** — "¿De qué va este proyecto?", "¿Cuáles son los módulos principales?"
3. **Relaciones entre módulos** — "¿Qué archivos dependen de auth.py?", "¿Dónde se llama a la función X?"
4. **Antes de leer código** — Cuando necesitas contexto pero no quieres releer todo

## Cómo usar

**Primero asegúrate de que el graph esté construido:**

```bash
# Sin argumentos — muestra archivos y pide confirmación (interactivo)
./bin/claude-retain-build-graph.ps1    # PowerShell (Windows)
./bin/claude-retain-build-graph         # Bash (Linux/Mac)

# Con archivos específicos — actualiza solo esos
./bin/claude-retain-build-graph.ps1 bot.js config.js  # PowerShell
./bin/claude-retain-build-graph bot.js config.js       # Bash
```

**Luego consulta el graph con:**

```bash
# Query semántico (ChromaDB)
./bin/claude-retain-graph.ps1 query_semantic "qué hace la autenticación"   # PowerShell
./bin/claude-retain-graph query_semantic "qué hace la autenticación"        # Bash

# Query estructural (SQLite)
./bin/claude-retain-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-graph query_structural "bot.js"        # Bash

# Overview del proyecto
./bin/claude-retain-graph.ps1 overview   # PowerShell
./bin/claude-retain-graph overview        # Bash

# Verificar si necesita compactación
./bin/claude-retain-graph.ps1 check_compact   # PowerShell
./bin/claude-retain-graph check_compact        # Bash
```

## Qué devuelve el graph

- **Semántico** — resultados por similitud (qué archivos son relevantes para tu pregunta)
- **Estructural** — imports, dependencias, llamadas cruzadas de un archivo específico
- **Texto comprimido** — resumen de alto nivel sin leer código completo
- **Sugerencias** — qué archivos específicos leer si necesita más detalle

## Auto-compact

El graph se compacta automáticamente cuando:
- Tiene más de 50 nodos y algunos no se consultaron en 24h
- El index.md tiene más de 1000 líneas
- Hay muchos nodos sin cambios en 72h

Puedes verificar si necesita compactar con:

```bash
./bin/claude-retain-graph.ps1 check_compact   # PowerShell
./bin/claude-retain-graph check_compact        # Bash
```

## Flujo recomendado

1. Pregunta al graph → obtén contexto de alto nivel
2. Si el graph sugiere archivos → léelos solo si es necesario
3. Después de modificar archivos → el graph se actualiza automáticamente (si graph_update está habilitado)
4. De vez en cuando → verifica y compacta si es necesario

## Skills del proyecto — Decisiones automáticas

El graph también sabe qué plugins/skills tienes instalados y cuáles aplican para cada archivo/tarea:

- `overview` → muestra tipo de proyecto + skills recomendadas
- `skills` → lista completa de skills instaladas con las recomendadas marcadas
- `skills_for "archivo.py" --file` → qué skills aplican a un archivo específico
- `skills_for "revisar el código"` → qué skills aplican para una tarea (keyword matching)

Cuando Claude decide usar una skill, consulta primero el graph:
1. El tipo de proyecto determina las skills siempre-aplicables
2. El tipo de archivo determina conexiones directas (.py → code-review, etc.)
3. El contexto de la tarea filtra las skills relevantes por keyword
4. Las skills recomendadas se marcan con [RECOMENDADO]

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

