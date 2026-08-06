# Claude Retain — Memoria persistente y cache LLM para Claude Code

Plugin que agrega **memoria persistente**, **compresión de sesiones** y **cache de respuestas** a Claude Code, haciéndolo más autónomo sin depender de que el usuario recuerde o proporcione información manualmente.

## ¿Qué hace?

1. **Compresión automática de sesiones** — Convierte sesiones largas en resúmenes diarios/semanales. Si una sesión tiene 500 interacciones, Claude Code solo carga el resumen (~60% menos tokens)
2. **Memoria persistente (4 capas)** — Claude Code recuerda conversaciones pasadas sin que tengas que copiarlas de nuevo
3. **Cache LLM** — Si preguntas lo mismo dos veces, responde desde cache sin gastar tokens extra
4. **Auto-permission** — Operaciones seguras sin confirmación; operaciones peligrosas con backup automático

## Arquitectura de memoria

```
┌─────────────────────────────────────────────┐
│  L0 — Identity (~100 tokens)               │ ← Siempre cargado
│  (quién es el agente)                       │
├─────────────────────────────────────────────┤
│  L1 — Essential Story (~800 tokens)        │ ← Auto-generado desde la historia
│  (historia esencial del proyecto)            │
├─────────────────────────────────────────────┤
│  L2 — On-Demand (filtrado por wing/room)   │ ← Carga selectiva según contexto
│  (memoria específica por proyecto)           │
├─────────────────────────────────────────────┤
│  L3 — Deep Search (sin límite)             │ ← Búsqueda híbrida BM25 + embeddings
│  (búsqueda profunda sobre toda la memoria)   │
└─────────────────────────────────────────────┘
```

## Compresión de sesiones

El pipeline de compresión convierte sesiones largas en resúmenes comprimidos. Detecta automáticamente qué LLM está disponible y lo usa:

**Prioridad de LLM:**
1. **Haiku** vía CLI de Claude (si existe + OAuth) → compresión óptima, ~$0.004 por sesión
2. **LLM local** vía CLI de Claude Code (si no hay Haiku) → funciona siempre
3. **llama.cpp** directo (último fallback)

**Flujo:**

```
Sesión cruda (500+ interacciones)
  │
  ├─ PostToolUse (Write/Edit) → Auto-save si ≥3 herramientas
  │
  ├─ Stop → Comprimir sesión con LLM disponible
  │         ↓
  │     today-YYYY-MM-DD.md (~60% menos tokens)
  │
  └─ Consolidación semanal → recent.md + archive.md
```

**Beneficios:**
- ~60% menos tokens en memoria de inicio (vs sin compresión)
- Funciona con cualquier configuración — no importa qué LLM tengas
- Si tienes Claude CLI + OAuth → usas Haiku automáticamente
- Si solo tienes un modelo local → funciona igual sin problemas

**Estructura de archivos:**
```
~/.claude-retain/memory/
├── today-2026-08-05.md      ← Resumen diario comprimido
├── recent.md                ← Resumen semanal consolidado
├── archive/                 ← Resúmenes rotados (>7 días)
│   ├── archive-2026-08-01.md
│   └── archive-2026-08-02.md
└── core-memories.md         ← Memorias definitorias de identidad
```

**Comparación Haiku vs Local:**

| | Haiku (CLI Claude) | Modelo local |
|---|---|---|
| Calidad compresión | Mejor (~65%) | Variable (~50-60%) |
| Costo por sesión | ~$0.004 | $0 |
| Requiere | OAuth + CLI Claude | Nada extra |
| Velocidad | ~10s | 30-120s (según modelo) |

## Instalación

### Opción A: Desde marketplace de GitHub (recomendado)

1. Agrega el marketplace al `.claude/settings.json` de Claude Code:

```json
"extraKnownMarketplaces": {
  "claude-retain": {
    "source": {
      "source": "github",
      "repo": "Beginning0/claude-marketplace"
    }
  }
}
```

2. Reinicia Claude Code y ejecuta:

```bash
/plugin marketplace add Beginning0/claude-marketplace
/plugin install claude-retain@claude-retain
```

3. Instala las dependencias de Python desde el directorio clonado:

```powershell
cd $env:USERPROFILE\.claude\plugins\cache\claude-retain\claude-retain\0.1.1
pip install -e .
```

### Opción B: Desde marketplace local (directorio)

1. Agrega al `.claude/settings.json` de Claude Code:

```json
"extraKnownMarketplaces": {
  "claude-retain-local": {
    "source": {
      "source": "directory",
      "path": "C:\\ruta\\a\\tu\\clon\\claude-retain"
    }
  }
}
```

2. Habilita el plugin:

```json
"enabledPlugins": {
  "claude-retain@claude-retain-local": true
}
```

3. Instala las dependencias de Python:

```powershell
cd C:\ruta\a\tu\clon\G--Agentes-Plugin-agente
pip install -e .
```

### Opción C: Instalación manual

1. Clona el repositorio:

```powershell
git clone https://github.com/Beginning0/claude-retain.git
```

2. Agrega al `.claude/settings.json` de Claude Code (el path debe apuntar a donde clonaste):

```json
"extraKnownMarketplaces": {
  "claude-retain-local": {
    "source": {
      "source": "directory",
      "path": "C:\\ruta\\a\\tu\\clon\\claude-retain"
    }
  }
},
"enabledPlugins": {
  "claude-retain@claude-retain-local": true
}
```

3. Instala las dependencias de Python:

```powershell
cd C:\ruta\a\tu\clon\G--Agentes-Plugin-agente
pip install -e .
```

### Dependencias

El plugin requiere las siguientes dependencias de Python:

| Dependencia | Descripción | Notas |
|-------------|-------------|-------|
| `chromadb` | Base de datos vectorial para embeddings | Instalable vía pip |
| `sentence-transformers` | Modelo de embeddings (all-MiniLM-L6-v2) | Instalable vía pip |
| `llama-cpp-python` | Inferencia local con llama.cpp | Requiere compilación C/C++ — [instrucciones](https://github.com/abetlen/llama-cpp-python#installation) |
| `mempalace` | Memoria persistente en memoria RAM | Instalable vía pip |

**Nota:** `llama-cpp-python` es la dependencia más problemática. Si no la necesitás para compresión de sesiones, podes instalar sin ella:

```powershell
pip install chromadb sentence-transformers mempalace
```

Y usar solo el cache LLM y memoria persistente sin compresión con llama.cpp.

## Uso

### Comandos en terminal

```
!claude-retain stats            — Estadísticas de memoria y cache
!claude-retain search <query>   — Buscar en memoria persistente
!claude-retain layers           — Estado de las 4 capas (L0-L3)
!claude-retain graph [entity]   — Grafo de conocimiento
!claude-retain llm-cache stats  — Estadísticas del cache LLM
!claude-retain llm-cache clear  — Limpiar cache LLM
!claude-retain help             — Ayuda
```

### Comandos de compresión

```
!claude-retain compress           — Comprimir sesión actual manualmente
!claude-retain consolidate        — Consolidar diarios en semanales manualmente
!claude-retain memory-summary     — Mostrar resumen de memoria comprimida
```

## Configuración

El archivo `settings.json` controla todos los aspectos del plugin:

- **claude-retain**: habilitar/desabilitar, rutas de la base de datos, tokens máximos L1
- **llm_cache**: habilitar/desabilitar, tamaño máximo en memoria, TTL por defecto
- **auto_permission**: habilitar/desabilitar, categorías permitidas, backup automático
- **session_compression**: habilitar/desabilitar, umbral de herramientas para auto-save, modelo a usar

### Variables de entorno para compresión

```bash
# Qué LLM usar: auto (detecta), haiku, local
CLAUDE_REMEMBER_USE_HAIKU=auto

# Modelo a usar si no hay Haiku disponible
CLAUDE_REMEMBER_MODEL=/ruta/al/modelo.gguf

# Máximo de tokens de salida para compresión (default: 2048)
CLAUDE_REMEMBER_MAX_TOKENS=2048

# Timeout en segundos para llamadas al LLM (default: 60)
CLAUDE_REMEMBER_TIMEOUT=60

# Ruta a llama.cpp CLI (si no está en PATH)
LLAMA_CPP_BIN=/ruta/a/llama-cli
```

## Cómo funciona el cache LLM

1. Antes de cada llamada al LLM, se calcula un hash de `(prompt + contexto)`
2. Si hay match en el cache → respuesta instantánea sin llamar al LLM
3. Si no hay match → llamar al LLM y guardar la respuesta en cache

**Beneficio:** Las respuestas a preguntas similares no cuestan tokens extra.

## Cómo funciona el auto-permission

- **Lectura**: Siempre permitida (no requiere confirmación)
- **Escritura segura**: Siempre permitida (crear archivos nuevos, editar existentes)
- **Operaciones peligrosas**: Permitidas con backup automático — se copia el archivo antes de modificarlo
- **Operaciones destructivas**: Requieren confirmación explícita del usuario

## Datos persistentes

El plugin almacena datos en:

- `~/.claude-retain/palace/` — Base de datos de memoria (ChromaDB + FTS5)
- `~/.claude-retain/knowledge_graph.sqlite3` — Grafo de conocimiento temporal
- `~/.claude-retain/llm_cache.db` — Cache persistente de respuestas LLM (SQLite)
- `~/.claude-retain/backups/` — Backups automáticos de archivos modificados
- `~/.claude-retain/auto_permission.json` — Configuración de permisos
- `~/.claude-retain/memory/` — Resúmenes de sesiones (today-*.md, recent.md, archive/)
- `~/.claude-retain/consolidation.lock` — Lock para evitar consolidación concurrente

## Notas técnicas

- La memoria de inicio (L0 + L1) cuesta ~900 tokens por sesión (vs ~5000+ sin plugin)
- El cache LLM reduce llamadas redundantes a ~0 tokens cuando hay hit
- Los backups automáticos se eliminan después de 7 días (configurable)

### Hooks granulares (hooks.d/)

El plugin usa hooks.d/ para eventos específicos:

| Hook | Cuándo | Qué hace |
|------|--------|----------|
| `before_session_start` | Antes de iniciar sesión | Carga memoria comprimida (recent.md, archive.md) |
| `after_post_tool` | Después de Write/Edit | Auto-save si ≥3 herramientas usadas |
| `before_save` | Antes de guardar sesión | Comprime sesión (detecta Haiku o local) |
| `after_save` | Después de guardar | Consolidar diarios en semanales |
| `before_consolidate` | Antes de consolidar | Verifica resúmenes diarios |
| `after_consolidate` | Después de consolidar | Actualiza grafo de conocimiento |

### Arquitectura de la compresión

- **extract.py** → Lee el historial JSONL de Claude Code, filtra system reminders, agrupa en pares humano/agente
- **compress.py** → Detecta automáticamente Haiku/LLM local y comprime con el mejor disponible (cero pérdida de información)
- **consolidate.py** → Fusiona diarios en semanales/mensuales, rota archivos antiguos a archive/
- **spawn_guard** → Previene consolidación concurrente (mismo archivo lock)
- **slug** → Genera nombres basados en contenido (SHA-256 hash), no timestamps aleatorios

