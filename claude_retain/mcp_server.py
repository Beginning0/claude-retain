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
        {
            "name": "claude-retain_cache_stats",
            "description": "Mostrar estadísticas del cache LLM — entradas en cache, hits totales, tamaño",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain_cache_clear",
            "description": "Limpiar entradas expiradas del cache LLM",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "claude-retain_cache_get",
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
            "name": "claude-retain_cache_set",
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
        }
    ]

def handle_tool_call(tool_name, params):
    """Manejar una llamada a herramienta MCP."""
    handlers = {
        "claude-retain_cache_stats": cache_stats,
        "claude-retain_cache_clear": cache_clear,
        "claude-retain_cache_get": cache_get,
        "claude-retain_cache_set": cache_set,
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

