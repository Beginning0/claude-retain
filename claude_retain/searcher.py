"""
Searcher — Búsqueda híbrida BM25 + embeddings con SQLite FTS5.

Proporciona:
- search_memories(): búsqueda híbrida (BM25 keyword + embedding semántica)
- index_document(): indexar un documento para búsqueda BM25
- get_collection(): obtener colección Palace (ChromaDB)

Dependencias: sqlite3, palace, sentence-transformers (opcional)
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any

DEFAULT_PALACE_PATH = os.path.expanduser("~/.claude-retain/palace")
FTS5_DB_PATH = os.path.expanduser("~/.claude-retain/fts5.db")


def _ensure_fts_db():
    """Asegurar que la base de datos FTS5 existe y tiene las tablas necesarias."""
    import sqlite3
    Path(FTS5_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(FTS5_DB_PATH)
    # Tabla principal de documentos (BM25 index). FTS5 no acepta tipos de columna,
    # solo nombres: fts5(a, b, c). Declarar "a TEXT" lanza OperationalError.
    conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(content, wing, room, importance, timestamp, source)""")
    # Tabla para tracking de documentos (evitar duplicados)
    conn.execute("""CREATE TABLE IF NOT EXISTS document_index (
        id TEXT PRIMARY KEY,
        palace_id TEXT,
        indexed_at TEXT NOT NULL
    )""")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.commit()
    return conn


def index_document(
    doc_id: str,
    content: str,
    wing: str = "general",
    room: str = "general",
    importance: float = 1.0,
    timestamp: float = None,
    source: str = "",
    palace_id: str = None,
):
    """Indexar un documento para búsqueda BM25."""
    try:
        conn = _ensure_fts_db()
        now = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("""INSERT OR REPLACE INTO memories_fts
            (content, wing, room, importance, timestamp, source)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (content, wing, room, importance, timestamp or __import__("time").time(), source))
        conn.execute("""INSERT OR REPLACE INTO document_index
            (id, palace_id, indexed_at) VALUES (?, ?, ?)""",
            (doc_id, palace_id or "", now))
        conn.commit()
        return True
    except Exception as e:
        print(f"[searcher] ERROR indexando documento: {e}")
        return False


def search_memories(
    query: str,
    palace_path: str = None,
    wing: str = None,
    room: str = None,
    n_results: int = 5,
    max_distance: float = 1.0,
):
    """Búsqueda híbrida BM25 + embeddings.

    Combina:
    1. BM25 (SQLite FTS5) — búsqueda por palabras clave con scoring de relevancia
    2. Embeddings semánticos (sentence-transformers) — búsqueda por similitud conceptual

    Returns dict con 'hits' — lista de resultados combinados y reordenados.
    """
    palace_path = palace_path or DEFAULT_PALACE_PATH

    # ── Paso 1: BM25 keyword search ──
    bm25_hits = _search_bm25(query, wing=wing, room=room)

    # ── Paso 2: Embedding semantic search ──
    semantic_hits = _search_semantic(palace_path=palace_path, query=query, n_results=n_results * 3)

    # ── Paso 3: Combinar resultados ──
    combined = _combine_results(bm25_hits, semantic_hits, n_results)

    return {"hits": combined}


def _search_bm25(query: str, wing: str = None, room: str = None) -> List[Dict]:
    """Búsqueda BM25 con SQLite FTS5."""
    try:
        conn = _ensure_fts_db()
        where_clause = ""
        params = []

        # FTS query — usar MATCH para BM25 scoring. Los terminos van sin comillas:
        # "'x'" da fts5: syntax error; la busqueda por columna es wing:value.
        fts_query = query
        if wing:
            fts_query += f" AND wing:{wing}"
        if room:
            fts_query += f" AND room:{room}"

        results = conn.execute(
            f"""SELECT rowid, content, wing, room, importance, timestamp, source
                FROM memories_fts
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT {100}""",
            (fts_query,),
        ).fetchall()

        hits = []
        for r in results:
            # rank de FTS5: más bajo = más relevante
            # Convertir a score: 1 / (1 + rank) — importance es el peso del recuerdo (col 4),
            # no source (col 6): abs(str) lanzaría TypeError.
            score = 1.0 / (1.0 + abs(r[4] if len(r) > 4 else 0))
            hits.append({
                "similarity": round(score, 3),
                "source_file": r[6] if len(r) > 6 else "",
                "wing": r[2] or "?",
                "room": r[3] or "?",
                "matched_via": "bm25",
                "text": r[1][:500] if r[1] else "",
                "bm25_rank": r[4] if len(r) > 4 else 0,
            })

        return hits
    except Exception:
        return []


def _search_semantic(palace_path: str = None, query: str = None, n_results: int = 10):
    """Buscar por similitud semántica con sentence-transformers."""
    palace_path = palace_path or DEFAULT_PALACE_PATH

    try:
        from sentence_transformers import SentenceTransformer
        import chromadb

        # Cargar modelo de embeddings
        model = SentenceTransformer("all-MiniLM-L6-v2")

        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection("claude-retain")
        if not col:
            return []

        results = col.query(
            query_texts=[query],
            n_results=n_results,
        )

        hits = []
        for doc, dist, meta in zip(
                results.get("documents", [[]])[0] or [],
                results.get("distances", [[]])[0] or [],
                results.get("metadatas", [[]])[0] or []):
            # Convertir distancia coseno a similitud (ChromaDB usa cosine distance)
            similarity = max(0.0, 1.0 - dist) if dist >= 0 else 0.0
            hits.append({
                "similarity": round(similarity, 3),
                "source_file": meta.get("source", "?"),
                "wing": meta.get("wing", "?"),
                "room": meta.get("room", "?"),
                "matched_via": "embedding",
                "text": doc[:500] if doc else "",
            })

        return hits
    except ImportError:
        # sentence-transformers no disponible — fallback a ChromaDB default (BGE)
        try:
            import chromadb
            client = chromadb.PersistentClient(path=palace_path)
            col = client.get_collection("claude-retain")
            if not col:
                return []

            results = col.query(
                query_texts=[query],
                n_results=n_results,
            )

            hits = []
            for doc, dist, meta in zip(
                    results.get("documents", [[]])[0] or [],
                    results.get("distances", [[]])[0] or [],
                    results.get("metadatas", [[]])[0] or []):
                similarity = max(0.0, 1.0 - dist) if dist >= 0 else 0.0
                hits.append({
                    "similarity": round(similarity, 3),
                    "source_file": meta.get("source", "?"),
                    "wing": meta.get("wing", "?"),
                    "room": meta.get("room", "?"),
                    "matched_via": "embedding",
                    "text": doc[:500] if doc else "",
                })
            return hits
        except Exception:
            return []


def _combine_results(bm25_hits, semantic_hits, n_results):
    """Combinar resultados BM25 y semánticos con scoring ponderado.

    Regla:
    - Hit que aparece en ambos → score = 0.7 * bm25_score + 0.3 * semantic_score
    - Solo BM25 → score = bm25_score * 1.2 (boost por keyword exacta)
    - Solo embedding → score = semantic_score * 0.8 (penalty menor por no tener keyword)
    """
    # Indexar por texto para deduplicar
    bm25_by_text = {h["text"]: h for h in bm25_hits}
    semantic_by_text = {h["text"]: h for h in semantic_hits}

    all_texts = set(bm25_by_text.keys()) | set(semantic_by_text.keys())
    combined = []

    for text in all_texts:
        in_bm25 = text in bm25_by_text
        in_semantic = text in semantic_by_text

        if in_bm25 and in_semantic:
            # Hit en ambos — score combinado
            bm25_score = bm25_by_text[text]["similarity"]
            sem_score = semantic_by_text[text]["similarity"]
            final_score = 0.7 * bm25_score + 0.3 * sem_score
            matched_via = "hybrid"
        elif in_bm25:
            # Solo BM25 — boost por keyword exacta
            final_score = bm25_by_text[text]["similarity"] * 1.2
            matched_via = "bm25"
        else:
            # Solo embedding — menor prioridad
            final_score = semantic_by_text[text]["similarity"] * 0.8
            matched_via = "embedding"

        # Tomar los datos del hit correspondiente
        source_file = (bm25_by_text.get(text) or semantic_by_text.get(text))["source_file"]
        wing = (bm25_by_text.get(text) or semantic_by_text.get(text))["wing"]
        room = (bm25_by_text.get(text) or semantic_by_text.get(text))["room"]

        combined.append({
            "similarity": round(final_score, 3),
            "source_file": source_file,
            "wing": wing,
            "room": room,
            "matched_via": matched_via,
            "text": text[:500] if text else "",
        })

    # Ordenar por score descendente y limitar
    combined.sort(key=lambda x: x["similarity"], reverse=True)
    return combined[:n_results]
