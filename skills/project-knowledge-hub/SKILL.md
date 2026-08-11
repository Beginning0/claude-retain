---
name: project-knowledge-hub
description: Hub de conocimiento del proyecto — muestra cuánto sabe el graph sobre cada archivo, entidades conocidas y gaps de información.
allowed-tools: [Bash]
---

## Hub de Conocimiento del Proyecto

Muestra un resumen de todo lo que el graph del proyecto conoce, organizado por archivos. Útil para ver rápidamente qué información está disponible sin leer cada archivo.

### Comandos principales

**1. Hub completo — overview de todo el conocimiento:**
```bash
# Reconstruye TODO el graph sin pedir confirmación
./bin/claude-retain-build-graph.ps1 --auto    # PowerShell (Windows)
./bin/claude-retain-build-graph --auto         # Bash (Linux/Mac)
```

**2. Query estructural de un archivo específico:**
```bash
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash
# Muestra: imports, definiciones, relaciones de este archivo
```

**3. Query semántico — buscar por concepto:**
```bash
./bin/claude-retain-project-graph.ps1 query_semantic "autenticación"   # PowerShell
./bin/claude-retain-project-graph query_semantic "autenticación"        # Bash
# Devuelve archivos relevantes por similitud semántica
```

**4. Overview del proyecto completo:**
```bash
./bin/claude-retain-project-graph.ps1 overview   # PowerShell
./bin/claude-retain-project-graph overview        # Bash
# Muestra: nodos, aristas, tipo de proyecto, cruxes
```

### Qué muestra el hub

| Información | Comando |
|---|---|
| Archivos indexados y su estado | `build-graph` (sin argumentos) |
| Imports del archivo | `query_structural "archivo"` → imports |
| Definiciones (funciones/clases) | `query_structural "archivo"` → defines |
| Relación de herencia | `query_structural "archivo"` → extends |
| Archivos que importan este | `query_structural "archivo"` → imported_by |
| Resumen semántico del archivo | `query_semantic "archivo"` |
| Cruxes (lógica central) | `overview` → archivos con cruxes |

### Gaps — Qué no sabe el graph

Si un archivo no aparece en los resultados, puede significar:
1. **No está indexado** — ejecuta `build-graph` para indexarlo
2. **Está en el graph pero sin consultas previas** — el agente nunca lo consultó
3. **Fue compactado** — se movió a `~/.claude-retain/project_graph/compacted/`

### Flujo de trabajo

```
1. build-graph → ¿qué archivos hay?
2. query_structural "archivo" → ¿qué sabe el graph de este archivo?
3. query_semantic "concepto" → ¿qué archivos son relevantes para X?
4. overview → ¿cuánto del proyecto está indexado?
```

### Ejemplo de uso

```bash
# ¿Cuánto sabe el graph sobre bot.js?
./bin/claude-retain-project-graph.ps1 query_structural "bot.js"   # PowerShell
./bin/claude-retain-project-graph query_structural "bot.js"        # Bash

# Resultado esperado:
#   Nodo: bot.js (file)
#   Resumen: 0 clases, 15 funciones
#   Importa: utils.js, config.js
#   Definiciones: main, handleRequest, processPayment
#   Herencia: -
#   Queries: 3 consultas previas

# ¿Qué archivos son relevantes para "pagos"?
./bin/claude-retain-project-graph.ps1 query_semantic "pagos"   # PowerShell
./bin/claude-retain-project-graph query_semantic "pagos"        # Bash

# Resultado esperado:
#   [semantic] similitud=0.892 — bot.js
#     Función processPayment...
#   [semantic] similitud=0.756 — payment.js
#     Clase PaymentProcessor...
```

## Estilo de comunicación — Eficiencia

Reglas para output directo y accionable:

1. **Empezar con la acción**, no con contexto — primero el resultado, después la explicación
2. **Numerar pasos** en lugar de listas — cada línea un solo paso
3. **Sin preamble, sin recap, sin closers** — no "vamos a", "en resumen", "espero ayude"
4. **Listas máx 5 items** — si necesitas más, dividir
5. **Estimaciones concretas en minutos** — no "un momento", usar "2 min", "30 seg"
6. **Reportar errores de hecho** — no disculpas, solo qué falló y cómo arreglar
7. **Wins visibles** — cuando un paso se completa, marcarlo claro

