"""
LLM Cache — Cache de respuestas LLM para ahorrar tokens.

Antes de cada llamada al LLM, verificar cache con hash de (prompt + contexto).
Si hay match → devolver respuesta sin llamar al LLM.
Si no hay match → llamar al LLM y guardar respuesta en cache.

Diseño:
- Cache en memoria (dict) para velocidad
- Persistencia opcional a SQLite para cross-session
- TTL configurable por defecto
- Evicción LRU para control de tamaño
"""

import hashlib
import json
import os
import sys
import sqlite3
import time
from pathlib import Path
from typing import Optional

# Fix para codificación en Windows — reemplazar caracteres Unicode al imprimir
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    _orig_write = sys.stdout.write
    def _fix_unicode(s):
        return s.encode("cp1252", errors="ignore").decode("cp1252", errors="ignore")
    sys.stdout.write = lambda s: _orig_write(_fix_unicode(s)) if isinstance(s, str) else _orig_write(s)

# ──────────────────────────────────────────────────────────────────────
# Cache en memoria — siempre activo, sin latencia
# ──────────────────────────────────────────────────────────────────────

class MemoryCache:
    """Cache en memoria con TTL y evicción LRU."""

    def __init__(self, max_size: int = 500, default_ttl: float = 3600.0):
        self.max_size = max_size
        self.default_ttl = default_ttl  # segundos antes de expirar
        self._cache: dict[str, dict] = {}  # key -> {value, expires_at, access_time}

    def get(self, key: str) -> Optional[str]:
        """Obtener valor del cache. Devuelve None si no hay o expiró."""
        entry = self._cache.get(key)
        if not entry:
            return None
        # Verificar TTL
        if time.time() > entry["expires_at"]:
            del self._cache[key]  # Evicción por TTL
            return None
        # Actualizar access_time (LRU)
        entry["access_time"] = time.time()
        return entry["value"]

    def set(self, key: str, value: str, ttl: float = None):
        """Guardar valor en cache."""
        ttl = ttl or self.default_ttl
        # Si el cache está lleno, evictar el menos accesado
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "access_time": time.time(),
        }

    def _evict_lru(self):
        """Evictar el entry menos accesado."""
        if not self._cache:
            return
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k]["access_time"])
        del self._cache[lru_key]

    def clear_expired(self):
        """Limpiar todos los entries expirados."""
        now = time.time()
        expired = [k for k, v in self._cache.items() if now > v["expires_at"]]
        for k in expired:
            del self._cache[k]

    def size(self) -> int:
        return len(self._cache)

    def stats(self) -> dict:
        """Estadísticas del cache."""
        now = time.time()
        total = len(self._cache)
        expired = sum(1 for v in self._cache.values() if now > v["expires_at"])
        return {
            "total_entries": total,
            "expired_entries": expired,
            "max_size": self.max_size,
            "hit_rate": "0.0%",  # Se actualizará cuando se use
        }

# ──────────────────────────────────────────────────────────────────────
# Cache persistente — SQLite para cross-session
# ──────────────────────────────────────────────────────────────────────

class PersistentCache:
    """Cache persistente a SQLite. Se sincroniza con MemoryCache."""

    def __init__(self, db_path: Path = None):
        if db_path is None:
            # Usar ~/.claude-retain/llm_cache.db por defecto
            home = Path.home() / ".claude-retain"
            home.mkdir(parents=True, exist_ok=True)
            self.db_path = home / "llm_cache.db"
        else:
            self.db_path = db_path
        self._conn = None

    def _get_conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=10)
            self._init_db()
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS llm_cache (
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
            );
            CREATE INDEX IF NOT EXISTS idx_llm_cache_prompt_hash ON llm_cache(prompt_hash);
            CREATE INDEX IF NOT EXISTS idx_llm_cache_context_hash ON llm_cache(context_hash);
            CREATE INDEX IF NOT EXISTS idx_llm_cache_model ON llm_cache(model);
        """)
        conn.commit()

    def get(self, cache_key: str) -> Optional[str]:
        """Obtener valor del cache persistente."""
        try:
            conn = self._get_conn()
            cur = conn.execute(
                "SELECT respuesta, ttl_seconds, fecha_guardado FROM llm_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cur.fetchone()
            if not row:
                return None
            respuesta, ttl, fecha_guardada = row
            # Verificar TTL
            fecha_guardada_dt = time.mktime(time.strptime(fecha_guardada, "%Y-%m-%d %H:%M:%S"))
            if time.time() > fecha_guardada_dt + ttl:
                return None  # Expirado
            # Incrementar hits
            conn.execute("UPDATE llm_cache SET hits = hits + 1 WHERE cache_key = ?", (cache_key,))
            conn.commit()
            return respuesta
        except Exception:
            return None

    def set(self, cache_key: str, respuesta: str, ttl: int = 86400):
        """Guardar valor en cache persistente."""
        try:
            conn = self._get_conn()
            fecha = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT OR REPLACE INTO llm_cache
                (cache_key, prompt_hash, context_hash, model, provider, pregunta, respuesta, chars_contexto, fecha_guardado, ttl_seconds, hits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                cache_key, "", "", "unknown", "unknown",
                "", respuesta, 0, fecha, ttl
            ))
            conn.commit()
        except Exception:
            pass

    def set_with_metadata(self, cache_key: str, respuesta: str, prompt_hash: str,
                         context_hash: str, model: str, provider: str,
                         pregunta: str, chars_contexto: int, ttl: int = 86400):
        """Guardar valor con metadatos completos."""
        try:
            conn = self._get_conn()
            fecha = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT OR REPLACE INTO llm_cache
                (cache_key, prompt_hash, context_hash, model, provider, pregunta, respuesta, chars_contexto, fecha_guardado, ttl_seconds, hits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                cache_key, prompt_hash, context_hash, model, provider,
                pregunta, respuesta, chars_contexto, fecha, ttl
            ))
            conn.commit()
        except Exception:
            pass

    def get_stats(self) -> dict:
        """Estadísticas del cache persistente."""
        try:
            conn = self._get_conn()
            cur = conn.execute("SELECT COUNT(*), SUM(hits) FROM llm_cache")
            row = cur.fetchone()
            total = row[0] if row and row[0] else 0
            hits = row[1] if row and row[1] else 0
            return {
                "total_entries": total,
                "total_hits": hits,
                "db_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 2) if self.db_path.exists() else 0,
            }
        except Exception:
            return {"error": "No se pudo obtener estadísticas"}

    def clear_expired(self):
        """Limpiar entries expirados del cache persistente."""
        try:
            conn = self._get_conn()
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("DELETE FROM llm_cache WHERE fecha_guardado < ?", (now_str,))
            conn.commit()
        except Exception:
            pass

    def close(self):
        """Cerrar conexión."""
        if self._conn:
            self._conn.close()
            self._conn = None

# ──────────────────────────────────────────────────────────────────────
# Cache unificado — MemoryCache + PersistentCache
# ──────────────────────────────────────────────────────────────────────

class LLMCache:
    """Cache unificado de respuestas LLM.

    Flujo:
    1. Antes de llamar al LLM → verificar MemoryCache (rápido)
    2. Si no hay → verificar PersistentCache (más lento pero cross-session)
    3. Si hay match → devolver respuesta sin llamar al LLM
    4. Si no hay match → llamar al LLM y guardar en ambos caches
    """

    def __init__(self, memory_max_size: int = 500, default_ttl: float = 86400.0):
        self.memory = MemoryCache(max_size=memory_max_size, default_ttl=default_ttl)
        self.persistent = PersistentCache()
        self.default_ttl = default_ttl

    def get(self, prompt_hash: str, context_hash: str, model: str, provider: str) -> Optional[str]:
        """Buscar respuesta en cache.

        Args:
            prompt_hash: Hash de la pregunta del usuario
            context_hash: Hash del contexto (archivos, memoria, etc.)
            model: Nombre del modelo usado
            provider: Proveedor (lm_studio, openai, etc.)

        Returns:
            Respuesta cacheada o None si no hay match
        """
        # 1. MemoryCache primero (rápido)
        cache_key = self._make_cache_key(prompt_hash, context_hash, model, provider)
        answer = self.memory.get(cache_key)
        if answer:
            return answer

        # 2. PersistentCache segundo (cross-session)
        answer = self.persistent.get(cache_key)
        if answer:
            # Actualizar MemoryCache con el resultado
            self.memory.set(cache_key, answer, self.default_ttl)
            return answer

        return None

    def set(self, prompt_hash: str, context_hash: str, model: str, provider: str,
            respuesta: str, pregunta: str = "", chars_contexto: int = 0):
        """Guardar respuesta en ambos caches."""
        cache_key = self._make_cache_key(prompt_hash, context_hash, model, provider)
        # Guardar en MemoryCache (rápido para uso futuro)
        self.memory.set(cache_key, respuesta, self.default_ttl)
        # Guardar en PersistentCache (cross-session)
        self.persistent.set_with_metadata(
            cache_key=cache_key,
            respuesta=respuesta,
            prompt_hash=prompt_hash,
            context_hash=context_hash,
            model=model,
            provider=provider,
            pregunta=pregunta[:500],  # Limitar longitud de la pregunta
            chars_contexto=chars_contexto,
            ttl=int(self.default_ttl),
        )

    def _make_cache_key(self, prompt_hash: str, context_hash: str, model: str, provider: str) -> str:
        """Generar clave de cache única."""
        raw = f"{prompt_hash}:{context_hash}:{model}:{provider}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def clear_expired(self):
        """Limpiar entries expirados de ambos caches."""
        self.memory.clear_expired()
        self.persistent.clear_expired()

    def stats(self) -> dict:
        """Estadísticas completas del cache."""
        return {
            "memory": self.memory.stats(),
            "persistent": self.persistent.get_stats(),
        }


# Singleton para acceso global
_llm_cache_instance = None

def llm_cache() -> LLMCache:
    """Obtener el singleton del cache."""
    global _llm_cache_instance
    if _llm_cache_instance is None:
        _llm_cache_instance = LLMCache()
    return _llm_cache_instance

