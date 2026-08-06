"""MCP Server para el cache LLM de claude-retain.

Exponer herramientas MCP para gestionar el cache LLM:
- claude-retain_cache_stats: Mostrar estadísticas del cache
- claude-retain_cache_clear: Limpiar entradas expiradas
- claude-retain_cache_get: Obtener una respuesta cacheada por clave
- claude-retain_cache_set: Guardar una respuesta en el cache
"""

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

CACHE_PATH = os.environ.get("claude-retain_CACHE_PATH", os.path.expanduser("~/.claude-retain/llm_cache.db"))

def init_db():
    """Inicializar la base de datos si no existe."""
    cache_dir = Path(CACHE_PATH).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not os.path.exists(CACHE_PATH):
        conn = sqlite3.connect(CACHE_PATH)
        conn.execute("""CREATE TABLE IF NOT EXISTS llm_cache (
            cache_key TEXT PRIMARY KEY,
            prompt_hash TEXT NOT NULL,
            context_hash TEXT NOT NULL,
            model TEXT NOT NULL,
            provider TEXT NOT NULL,
            pregunta TEXT,
            respuesta TEXT NOT NULL,
            chars_contexto INTEGER DEFAULT 0,
            fecha_guardado TEXT NOT NULL,
            ttl_seconds INTEGER DEFAULT 86400,
            hits INTEGER DEFAULT 0
        )""")
        conn.commit()
        conn.close()

def cache_stats():
    """Mostrar estadísticas del cache LLM."""
    if not os.path.exists(CACHE_PATH):
        return {
            "content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}],
            "isError": False
        }

    conn = sqlite3.connect(CACHE_PATH)
    total = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
    hits_total = conn.execute("SELECT COALESCE(SUM(hits), 0) FROM llm_cache").fetchone()[0]
    size = Path(CACHE_PATH).stat().st_size
    conn.close()

    return {
        "content": [
            {"type": "text", "text": f"[claude-retain] Estadísticas del cache LLM\n"
             f"Entradas en cache: {total}\n"
             f"Hits totales:      {hits_total}\n"
             f"Tamaño archivo:    {size:,} bytes"}
        ],
        "isError": False
    }

def cache_clear():
    """Limpiar entradas expiradas del cache."""
    if not os.path.exists(CACHE_PATH):
        return {
            "content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}],
            "isError": False
        }

    conn = sqlite3.connect(CACHE_PATH)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    deleted = conn.execute("DELETE FROM llm_cache WHERE fecha_guardado < ?", (now_str,)).rowcount
    remaining = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
    conn.commit()
    conn.close()

    return {
        "content": [
            {"type": "text", "text": f"[claude-retain] Cache limpiado — {deleted} entradas eliminadas, {remaining} restantes"}
        ],
        "isError": False
    }

def cache_get(params):
    """Obtener una respuesta cacheada por clave."""
    cache_key = params.get("cache_key", "")
    if not cache_key:
        return {"content": [{"type": "text", "text": "Error: cache_key es requerido"}], "isError": True}

    if not os.path.exists(CACHE_PATH):
        return {
            "content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}],
            "isError": False
        }

    conn = sqlite3.connect(CACHE_PATH)
    row = conn.execute("SELECT respuesta, hits FROM llm_cache WHERE cache_key = ?", (cache_key,)).fetchone()
    conn.close()

    if not row:
        return {"content": [{"type": "text", "text": "No se encontró la clave en el cache"}], "isError": False}

    return {
        "content": [
            {"type": "text", "text": f"Respuesta cacheada (hits: {row[1]})\n\n{row[0]}"}
        ],
        "isError": False
    }

def cache_set(params):
    """Guardar una respuesta en el cache."""
    cache_key = params.get("cache_key", "")
    prompt_hash = params.get("prompt_hash", "")
    context_hash = params.get("context_hash", "")
    model = params.get("model", "unknown")
    provider = params.get("provider", "unknown")
    pregunta = params.get("pregunta", "")
    respuesta = params.get("respuesta", "")
    ttl = int(params.get("ttl", 86400)) if params.get("ttl") else 86400

    if not cache_key or not respuesta:
        return {"content": [{"type": "text", "text": "Error: cache_key y respuesta son requeridos"}], "isError": True}

    if not os.path.exists(CACHE_PATH):
        return {
            "content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}],
            "isError": False
        }

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(CACHE_PATH)
    conn.execute("""INSERT OR REPLACE INTO llm_cache
        (cache_key, prompt_hash, context_hash, model, provider, pregunta, respuesta, chars_contexto, fecha_guardado, ttl_seconds, hits)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (cache_key, prompt_hash, context_hash, model, provider, pregunta, respuesta, len(respuesta), now_str, ttl))
    conn.commit()
    conn.close()

    return {
        "content": [{"type": "text", "text": f"Respuesta guardada en cache (TTL: {ttl}s)"}],
        "isError": False
    }

def list_tools():
    """Lista de herramientas MCP."""
    return [
        # --- Cache LLM ---
        {
            "name": "claude-retain-cache-stats",
            "description": "Mostrar estadísticas del cache LLM — entradas en cache, hits totales, tamaño",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain-cache-clear",
            "description": "Limpiar entradas expiradas del cache LLM",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain-cache-get",
            "description": "Obtener una respuesta cacheada por clave. Retorna la respuesta cacheada si existe.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cache_key": {
                        "type": "string",
                        "description": "Clave única de la respuesta cacheada (hash sha256 de prompt+contexto)"
                    }
                },
                "required": ["cache_key"]
            }
        },
        {
            "name": "claude-retain-cache-set",
            "description": "Guardar una respuesta en el cache LLM para futuras consultas similares.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cache_key": {"type": "string", "description": "Clave única de la respuesta"},
                    "prompt_hash": {"type": "string", "description": "Hash sha256 del prompt"},
                    "context_hash": {"type": "string", "description": "Hash sha256 del contexto"},
                    "model": {"type": "string", "description": "Modelo usado (ej: claude-sonnet-4-20250514)"},
                    "provider": {"type": "string", "description": "Proveedor (ej: anthropic)"},
                    "pregunta": {"type": "string", "description": "La pregunta original"},
                    "respuesta": {"type": "string", "description": "La respuesta del LLM"},
                    "ttl": {"type": "integer", "description": "TTL en segundos (default: 86400 = 24h)"}
                },
                "required": ["cache_key", "respuesta"]
            }
        },
        # --- Memoria persistente ---
        {
            "name": "claude-retain-stats",
            "description": "Estadísticas de memoria (L0-L3) y cache LLM — muestra tokens por capa, drawers, triples del grafo",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain-search",
            "description": "Buscar recuerdos en la memoria persistente — combina BM25 keyword + embeddings semánticos",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Consulta de búsqueda"},
                    "n_results": {"type": "integer", "description": "Número de resultados (default: 5)"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "claude-retain-layers",
            "description": "Estado de las 4 capas de memoria — L0 identidad, L1 historia esencial, L2 on-demand, L3 deep search",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain-graph",
            "description": "Mostrar grafo de conocimiento — para una entidad específica o todos los triples",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entidad a consultar (default: todos los triples)"}
                },
                "required": []
            }
        },
        # --- Checkpoints ---
        {
            "name": "claude-retain-checkpoints",
            "description": "Listar todos los checkpoints de memoria — IDs, fechas, drawers count",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain-rewind",
            "description": "Restaurar la memoria a un checkpoint anterior — revierte drawers a estado previo",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "checkpoint_id": {"type": "string", "description": "ID del checkpoint a restaurar"}
                },
                "required": ["checkpoint_id"]
            }
        },
        {
            "name": "claude-retain-replay",
            "description": "Ver los recuerdos de un checkpoint sin restaurarlos — muestra drawers del checkpoint",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "checkpoint_id": {"type": "string", "description": "ID del checkpoint a replay"}
                },
                "required": ["checkpoint_id"]
            }
        },
        {
            "name": "claude-retain-delete-checkpoint",
            "description": "Eliminar un checkpoint de la memoria — libera drawers asociados",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "checkpoint_id": {"type": "string", "description": "ID del checkpoint a eliminar"}
                },
                "required": ["checkpoint_id"]
            }
        },
        {
            "name": "claude-retain-branch",
            "description": "Crear bifurcación de memoria desde un checkpoint — crea un nuevo checkpoint derivado",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "from_checkpoint": {"type": "string", "description": "Checkpoint base para la bifurcación"},
                    "label": {"type": "string", "description": "Etiqueta opcional para la bifurcación"}
                },
                "required": ["from_checkpoint"]
            }
        },
        # --- Project Graph ---
        {
            "name": "claude-retain-build-graph",
            "description": "Reconstruir el grafo del proyecto — indexa nodos y aristas de archivos del proyecto",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Archivos a indexar (default: todos)"}
                },
                "required": []
            }
        },
        # --- Session Compression ---
        {
            "name": "claude-retain-compress",
            "description": "Comprimir la sesión actual manualmente — detecta LLM disponible y comprime",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain-consolidate",
            "description": "Consolidar diarios en resúmenes semanales — fusiona today-*.md en recent.md",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain-memory-summary",
            "description": "Mostrar resumen de memoria comprimida — muestra today, recent y archive",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
    ]

def handle_tool_call(tool_name, params):
    """Manejar una llamada a herramienta MCP."""
    # --- Cache LLM ---
    def cache_stats_handler(p):
        if not os.path.exists(CACHE_PATH):
            return {"content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}], "isError": False}
        conn = sqlite3.connect(CACHE_PATH)
        total = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
        hits_total = conn.execute("SELECT COALESCE(SUM(hits), 0) FROM llm_cache").fetchone()[0]
        size = Path(CACHE_PATH).stat().st_size
        conn.close()
        return {"content": [{"type": "text", "text": f"[claude-retain] Estadísticas del cache LLM\nEntradas en cache: {total}\nHits totales: {hits_total}\nTamaño archivo: {size:,} bytes"}], "isError": False}

    def cache_clear_handler(p):
        if not os.path.exists(CACHE_PATH):
            return {"content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}], "isError": False}
        conn = sqlite3.connect(CACHE_PATH)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        deleted = conn.execute("DELETE FROM llm_cache WHERE fecha_guardado < ?", (now_str,)).rowcount
        remaining = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
        conn.commit()
        conn.close()
        return {"content": [{"type": "text", "text": f"[claude-retain] Cache limpiado — {deleted} entradas eliminadas, {remaining} restantes"}], "isError": False}

    def cache_get_handler(p):
        cache_key = p.get("cache_key", "")
        if not cache_key:
            return {"content": [{"type": "text", "text": "Error: cache_key es requerido"}], "isError": True}
        if not os.path.exists(CACHE_PATH):
            return {"content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}], "isError": False}
        conn = sqlite3.connect(CACHE_PATH)
        row = conn.execute("SELECT respuesta, hits FROM llm_cache WHERE cache_key = ?", (cache_key,)).fetchone()
        conn.close()
        if not row:
            return {"content": [{"type": "text", "text": "No se encontró la clave en el cache"}], "isError": False}
        return {"content": [{"type": "text", "text": f"Respuesta cacheada (hits: {row[1]})\n\n{row[0]}"}], "isError": False}

    def cache_set_handler(p):
        cache_key = p.get("cache_key", "")
        respuesta = p.get("respuesta", "")
        if not cache_key or not respuesta:
            return {"content": [{"type": "text", "text": "Error: cache_key y respuesta son requeridos"}], "isError": True}
        if not os.path.exists(CACHE_PATH):
            return {"content": [{"type": "text", "text": "Cache no disponible — no se encontró la base de datos"}], "isError": False}
        conn = sqlite3.connect(CACHE_PATH)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        ttl = int(p.get("ttl", 86400)) if p.get("ttl") else 86400
        conn.execute("""INSERT OR REPLACE INTO llm_cache
            (cache_key, prompt_hash, context_hash, model, provider, pregunta, respuesta, chars_contexto, fecha_guardado, ttl_seconds, hits)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (cache_key, p.get("prompt_hash",""), p.get("context_hash",""), p.get("model","unknown"), p.get("provider","unknown"), p.get("pregunta",""), respuesta, len(respuesta), now_str, ttl))
        conn.commit()
        conn.close()
        return {"content": [{"type": "text", "text": f"Respuesta guardada en cache (TTL: {ttl}s)"}], "isError": False}

    # --- Memoria persistente ---
    def stats_handler(p):
        from claude_retain.memory import MemoryManager
        mm = MemoryManager()
        if not mm.initialize():
            return {"content": [{"type": "text", "text": "claude-retain no disponible"}], "isError": False}
        s = mm.stats()
        from llm_cache import llm_cache
        cache = llm_cache()
        lines = [f"[claude-retain] Estadísticas de memoria\n"]
        lines.append(f"L0 — Identidad: {s.get('identity_tokens', 0)} tokens")
        lines.append(f"L1 — Historia esencial: {s.get('essential_story_tokens', 0)} tokens")
        lines.append(f"L2 — On-Demand: {s.get('total_drawers', 0)} drawers")
        lines.append(f"L3 — Deep Search: disponible")
        lines.append(f"Grafo de conocimiento: {s.get('knowledge_graph_triples', 0)} triples")
        if cache:
            cs = cache.stats()
            mem = cs.get("memory", {})
            pers = cs.get("persistent", {})
            lines.append(f"\nLLM Cache:")
            lines.append(f"  En memoria: {mem.get('total_entries', 0)} / {mem.get('max_size', 500)}")
            lines.append(f"  Persistente: {pers.get('total_entries', 0)} entradas, {pers.get('total_hits', 0)} hits")
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    def search_handler(p):
        from claude_retain.memory import MemoryManager
        mm = MemoryManager()
        if not mm.initialize():
            return {"content": [{"type": "text", "text": "claude-retain no disponible"}], "isError": False}
        query = p.get("query", "")
        if not query:
            return {"content": [{"type": "text", "text": "Error: query es requerido"}], "isError": True}
        n_results = p.get("n_results", 5)
        results = mm.search_memories(query)
        if not results:
            return {"content": [{"type": "text", "text": "No se encontraron resultados"}], "isError": False}
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"\n{i}. Sim: {r.get('similarity', 0):.3f} | Wing: {r.get('wing', '?')} | Room: {r.get('room', '?')}")
            text = r.get("text", "")
            if len(text) > 200:
                text = text[:200] + "..."
            lines.append(f"   {text}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    def layers_handler(p):
        from claude_retain.memory import MemoryManager
        mm = MemoryManager()
        if not mm.initialize():
            return {"content": [{"type": "text", "text": "claude-retain no disponible"}], "isError": False}
        identity = mm.get_identity()
        lines = [f"\nL0 — Identidad: {'[OK]' if identity else '[NO CONFIG]'} ({len(identity)//4} tokens)"]
        try:
            story = mm.get_essential_story()
            lines.append(f"L1 — Historia esencial: {'[OK]' if story else '[NO]'} ({len(story)//4} tokens)")
        except Exception:
            lines.append("L1 — Historia esencial: [ERROR]")
        try:
            from claude_retain.palace import get_collection
            col = get_collection(palace_path=mm.palace_path, create=False)
            count = col.count() if col else 0
            lines.append(f"L2 — On-Demand: [OK] ({count} drawers)")
        except Exception:
            lines.append("L2 — On-Demand: [ERROR]")
        lines.append("L3 — Deep Search: [OK]")
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    def graph_handler(p):
        from claude_retain.memory import MemoryManager
        mm = MemoryManager()
        if not mm.initialize():
            return {"content": [{"type": "text", "text": "claude-retain no disponible"}], "isError": False}
        entity = p.get("entity")
        if entity:
            triples = mm.get_knowledge_about(entity)
            if not triples:
                return {"content": [{"type": "text", "text": f"No hay conocimiento sobre '{entity}'"}], "isError": False}
            lines = [f"{t['subject']} --{t['predicate']}--> {t['object']}" for t in triples]
        else:
            all_triples = mm.kg.query_entity("ALL") if mm.kg else []
            entities = set()
            for t in (all_triples or []):
                entities.add(t.get("subject", ""))
            lines = [f"Grafo de conocimiento ({len(all_triples) if all_triples else 0} triples):\n"]
            for e in sorted(entities):
                if e and e != "ALL":
                    count = sum(1 for t in (all_triples or []) if t.get("subject") == e)
                    lines.append(f"  • {e} ({count} triples)")
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    # --- Checkpoints ---
    def checkpoints_handler(p):
        from claude_retain.checkpoints import CheckpointManager
        ckpt_mgr = CheckpointManager()
        checkpoints = ckpt_mgr.list_checkpoints()
        if not checkpoints:
            return {"content": [{"type": "text", "text": "No hay checkpoints"}], "isError": False}
        lines = [f"\nCheckpoints ({len(checkpoints)} total):\n"]
        for ckpt in checkpoints:
            label = f" — {ckpt['label']}" if ckpt.get('label') else ""
            is_branch = " [BRANCH]" if ckpt.get('is_branch') else ""
            time_str = ""
            try:
                import datetime
                time_str = datetime.datetime.fromtimestamp(ckpt['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            lines.append(f"  {ckpt['checkpoint_id']}{label}{is_branch} — {time_str} ({ckpt.get('drawers_count', '?')} drawers)")
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    def rewind_handler(p):
        from claude_retain.checkpoints import CheckpointManager
        checkpoint_id = p.get("checkpoint_id")
        if not checkpoint_id:
            return {"content": [{"type": "text", "text": "Error: checkpoint_id es requerido"}], "isError": True}
        ckpt_mgr = CheckpointManager()
        result = ckpt_mgr.rewind(checkpoint_id)
        if result:
            return {"content": [{"type": "text", "text": f"[Checkpoint] Memoria restaurada a {checkpoint_id}"}], "isError": False}
        else:
            return {"content": [{"type": "text", "text": f"[Checkpoint] ERROR: no se pudo restaurar a {checkpoint_id}"}], "isError": True}

    def replay_handler(p):
        from claude_retain.checkpoints import CheckpointManager
        checkpoint_id = p.get("checkpoint_id")
        if not checkpoint_id:
            return {"content": [{"type": "text", "text": "Error: checkpoint_id es requerido"}], "isError": True}
        ckpt_mgr = CheckpointManager()
        result = ckpt_mgr.replay(checkpoint_id)
        if "error" in result:
            return {"content": [{"type": "text", "text": f"[Checkpoint] ERROR: {result['error']}"}], "isError": True}
        lines = [f"\nReplay de {checkpoint_id}:\n"]
        lines.append(f"  Checkpoint: {result['checkpoint_id']}")
        try:
            import datetime
            time_str = datetime.datetime.fromtimestamp(result['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"  Fecha: {time_str}")
        except Exception:
            pass
        lines.append(f"  Label: {result.get('label', 'N/A')}")
        lines.append(f"  Drawers: {result['drawers_count']}")
        if result.get('is_branch'):
            lines.append(f"  Base: {result.get('base_checkpoint')}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    def delete_checkpoint_handler(p):
        from claude_retain.checkpoints import CheckpointManager
        checkpoint_id = p.get("checkpoint_id")
        if not checkpoint_id:
            return {"content": [{"type": "text", "text": "Error: checkpoint_id es requerido"}], "isError": True}
        ckpt_mgr = CheckpointManager()
        result = ckpt_mgr.delete_checkpoint(checkpoint_id)
        if result:
            return {"content": [{"type": "text", "text": f"[Checkpoint] Eliminado: {checkpoint_id}"}], "isError": False}
        else:
            return {"content": [{"type": "text", "text": f"[Checkpoint] ERROR: no se pudo eliminar {checkpoint_id}"}], "isError": True}

    def branch_handler(p):
        from claude_retain.checkpoints import CheckpointManager
        checkpoint_id = p.get("from_checkpoint")
        if not checkpoint_id:
            return {"content": [{"type": "text", "text": "Error: from_checkpoint es requerido"}], "isError": True}
        ckpt_mgr = CheckpointManager()
        result = ckpt_mgr.branch(checkpoint_id, p.get("label"))
        if result:
            return {"content": [{"type": "text", "text": f"[Checkpoint] Bifurcación creada: {result}"}], "isError": False}
        else:
            return {"content": [{"type": "text", "text": f"[Checkpoint] ERROR: no se pudo crear bifurcación desde {checkpoint_id}"}], "isError": True}

    # --- Project Graph ---
    def build_graph_handler(p):
        from claude_retain.project_graph import ProjectGraphManager
        import os as _os
        project_root = _os.getcwd()
        pm = ProjectGraphManager(project_root)
        files = p.get("files")
        if files:
            result = pm.incremental_update(files, project_root)
            lines = [f"[claude-retain] Graph actualizado para {len(files)} archivo(s):"]
            for f in files:
                lines.append(f"  ✓ {f} — {result['edges_updated']} aristas")
        else:
            result = pm.build_graph(project_root)
            lines = [f"[claude-retain] Graph reconstruido"]
            lines.append(f"  Nodes creadas: {result['nodes_created']}")
            lines.append(f"  Edges creadas: {result['edges_created']}")
        pm.close()
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    # --- Session Compression ---
    def compress_handler(p):
        import sys, os as _os
        plugin_root = _os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        if plugin_root:
            sys.path.insert(0, plugin_root)
        from pipeline.extract import extract_last_exchange
        from pipeline.compress import compress_session
        exchange = extract_last_exchange()
        if not exchange:
            return {"content": [{"type": "text", "text": "[claude-retain] No hay intercambios de sesión para comprimir"}], "isError": False}
        result = compress_session([exchange])
        if not result or not result.success:
            return {"content": [{"type": "text", "text": "[claude-retain] Compresión no necesaria — la sesión ya es corta"}], "isError": False}
        lines = [f"[claude-retain] Compresión completada"]
        lines.append(f"  Tokens originales: {result.tokens_before}")
        lines.append(f"  Tokens comprimidos: {result.tokens_after}")
        saved = result.tokens_before - result.tokens_after
        pct = round(saved / result.tokens_before * 100) if result.tokens_before else 0
        lines.append(f"  Ahorro: {pct}% ({saved} tokens)")
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    def consolidate_handler(p):
        import sys, os as _os
        plugin_root = _os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        if plugin_root:
            sys.path.insert(0, plugin_root)
        from pipeline.consolidate import run_consolidation
        success = run_consolidation()
        if not success:
            return {"content": [{"type": "text", "text": "[claude-retain] No hay diarios para consolidar"}], "isError": False}
        return {"content": [{"type": "text", "text": "[claude-retain] Consolidación completada — diarios fusionados en semanales"}], "isError": False}

    def memory_summary_handler(p):
        from pipeline.types import DailySummary, WeeklySummary
        try:
            from pathlib import Path as _Path
            import datetime as _dt
            today_file = _Path.home() / ".claude-retain" / "memory_hub" / "today.md"
            recent_file = _Path.home() / ".claude-retain" / "memory_hub" / "recent.md"
            archive_dir = _Path.home() / ".claude-retain" / "memory_hub" / "archive"
            lines = [f"[claude-retain] Resumen de memoria"]
            if today_file.exists():
                mtime = _dt.datetime.fromtimestamp(today_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                size = today_file.stat().st_size
                lines.append(f"  Today: {today_file.name} ({size:,} bytes, {mtime})")
            else:
                lines.append(f"  Today: no disponible")
            if recent_file.exists():
                mtime = _dt.datetime.fromtimestamp(recent_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                size = recent_file.stat().st_size
                lines.append(f"  Recent: {recent_file.name} ({size:,} bytes, {mtime})")
            else:
                lines.append(f"  Recent: no disponible")
            if archive_dir.exists():
                archives = sorted([f for f in archive_dir.iterdir() if f.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:5]
                lines.append(f"  Archive: {len(list(archive_dir.iterdir()))} archivos (mostrando últimos 5)")
                for af in archives:
                    mtime = _dt.datetime.fromtimestamp(af.stat().st_mtime).strftime("%Y-%m-%d")
                    lines.append(f"    - {af.name} ({mtime})")
            else:
                lines.append(f"  Archive: no disponible")
        except Exception as e:
            lines = [f"[claude-retain] Error al leer resumen: {e}"]
        return {"content": [{"type": "text", "text": "\n".join(lines)}], "isError": False}

    handlers = {
        # --- Cache LLM ---
        "claude-retain-cache-stats": cache_stats_handler,
        "claude-retain-cache-clear": cache_clear_handler,
        "claude-retain-cache-get": cache_get_handler,
        "claude-retain-cache-set": cache_set_handler,
        # --- Memoria ---
        "claude-retain-stats": stats_handler,
        "claude-retain-search": search_handler,
        "claude-retain-layers": layers_handler,
        "claude-retain-graph": graph_handler,
        # --- Checkpoints ---
        "claude-retain-checkpoints": checkpoints_handler,
        "claude-retain-rewind": rewind_handler,
        "claude-retain-replay": replay_handler,
        "claude-retain-delete-checkpoint": delete_checkpoint_handler,
        "claude-retain-branch": branch_handler,
        # --- Project Graph ---
        "claude-retain-build-graph": build_graph_handler,
        # --- Session Compression ---
        "claude-retain-compress": compress_handler,
        "claude-retain-consolidate": consolidate_handler,
        "claude-retain-memory-summary": memory_summary_handler,
    }

    handler = handlers.get(tool_name)
    if not handler:
        return {
            "jsonrpc": "2.0",
            "id": params.get("id"),
            "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
        }

    try:
        result = handler(params)
        return {
            "jsonrpc": "2.0",
            "id": params.get("id"),
            "result": {"content": result["content"]}
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": params.get("id"),
            "error": {"code": -32603, "message": str(e)}
        }

def main():
    """Servidor MCP — lee JSON-RPC de stdin, escribe en stdout."""
    import signal

    def sigterm_handler(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    init_db()

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        try:
            request = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "claude-retain-cache", "version": "0.1.0"},
                    "capabilities": {"tools": {"listChanged": True}}
                }
            }
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": list_tools()}
            }
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_params = params.get("arguments", {})
            response = handle_tool_call(tool_name, {"id": request_id, **tool_params})
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()

