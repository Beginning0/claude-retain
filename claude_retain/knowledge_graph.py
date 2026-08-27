"""
Knowledge Graph — Grafo de conocimiento temporal con SQLite.

Proporciona:
- KnowledgeGraph: grafo temporal con valid_from/valid_to y query por fecha
- add_triple(): agregar triple al grafo
- query_entity(): consultar triples sobre una entidad (incoming, outgoing, both)
- remove_triple(): eliminar un triple del grafo

Dependencias: sqlite3 (siempre disponible en Python)
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any


DEFAULT_KG_PATH = os.path.expanduser("~/.claude-retain/knowledge_graph.sqlite3")


class KnowledgeGraph:
    """Grafo de conocimiento temporal con soporte para query por fecha."""

    def __init__(self, path: str = None):
        self.path = path or DEFAULT_KG_PATH
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self._ensure_schema()
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.commit()

    def _ensure_schema(self):
        """Asegurar que el schema de SQLite existe."""
        self.conn.execute("""CREATE TABLE IF NOT EXISTS triples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            valid_from TEXT,
            valid_to TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL
        )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_triples_object ON triples(object)")
        self.conn.commit()

    def add_triple(self, subject: str, predicate: str, obj: str,
                   valid_from: str = None, confidence: float = 1.0) -> bool:
        """Agregar un triple al grafo. Idempotente: no duplica (subject,predicate,object)."""
        # Dedupe barato: evita que el grafo se infele con triples repetidos.
        existing = self.conn.execute(
            "SELECT 1 FROM triples WHERE subject=? AND predicate=? AND object=? LIMIT 1",
            (subject, predicate, obj),
        ).fetchone()
        if existing:
            return True
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            self.conn.execute(
                "INSERT INTO triples (subject, predicate, object, valid_from, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (subject, predicate, obj, valid_from, confidence, now))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[KG] ERROR agregando triple: {e}")
            return False

    def query_entity(self, entity: str, as_of: str = None, direction: str = "both") -> List[Dict]:
        """Query triples sobre una entidad con soporte temporal."""
        if entity == "ALL":
            rows = self.conn.execute("SELECT * FROM triples").fetchall()
            return [
                {
                    "subject": r[1], "predicate": r[2], "object": r[3],
                    "valid_from": r[4], "valid_to": r[5],
                    "confidence": r[6] if len(r) > 6 else 1.0,
                }
                for r in rows
            ]

        conditions = []
        params: list = []
        if direction in ("incoming", "both"):
            conditions.append("subject = ?")
            params.append(entity)
        if direction in ("outgoing", "both"):
            conditions.append("object = ?")
            params.append(entity)

        where_clause = " OR ".join(conditions)
        if as_of:
            where_clause += " AND (valid_from IS NULL OR valid_from <= ?)"
            params.append(as_of)
            where_clause += " AND (valid_to IS NULL OR valid_to >= ?)"
            params.append(as_of)

        rows = self.conn.execute(
            f"SELECT * FROM triples WHERE {where_clause}", params).fetchall()

        return [
            {
                "subject": r[1], "predicate": r[2], "object": r[3],
                "valid_from": r[4], "valid_to": r[5],
                "confidence": r[6] if len(r) > 6 else 1.0,
            }
            for r in rows
        ]

    def search_terms(self, terms: str, limit: int = 20) -> List[Dict]:
        """Buscar triples por palabras clave en subject/predicate/object (barato, LIKE)."""
        words = [w.strip().lower() for w in terms.split() if w.strip()]
        if not words:
            return []
        clauses = []
        params: list = []
        for w in words:
            # TODAS las palabras deben aparecer (AND) en cualquier columna.
            clause = f"(LOWER(subject) LIKE ? OR LOWER(predicate) LIKE ? OR LOWER(object) LIKE ?)"
            like = f"%{w}%"
            clauses.append(clause)
            params.extend([like, like, like])
        where = " AND ".join(clauses)
        rows = self.conn.execute(
            f"SELECT * FROM triples WHERE {where} LIMIT {limit}", params
        ).fetchall()
        return [
            {
                "subject": r[1], "predicate": r[2], "object": r[3],
                "valid_from": r[4], "valid_to": r[5],
                "confidence": r[6] if len(r) > 6 else 1.0,
            }
            for r in rows
        ]

    def remove_triple(self, triple_id: int) -> bool:
        """Eliminar un triple del grafo."""
        try:
            self.conn.execute("DELETE FROM triples WHERE id = ?", (triple_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[KG] ERROR eliminando triple: {e}")
            return False

    def close(self):
        """Cerrar conexiones."""
        if self.conn:
            self.conn.close()
            self.conn = None


class _SQLiteKnowledgeGraph:
    """Fallback inline — misma funcionalidad pero sin módulo separado.

    Se usa como fallback si knowledge_graph.py no existe (raro).
    """

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        import sqlite3
        self.conn = sqlite3.connect(path)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS triples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            valid_from TEXT,
            valid_to TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL
        )""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_triples_object ON triples(object)")
        import datetime
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.commit()

    def add_triple(self, subject: str, predicate: str, obj: str, valid_from: str = None, confidence: float = 1.0):
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.conn.execute(
            "INSERT INTO triples (subject, predicate, object, valid_from, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (subject, predicate, obj, valid_from, confidence, now))
        self.conn.commit()

    def query_entity(self, entity: str, as_of: str = None, direction: str = "both"):
        if entity == "ALL":
            rows = self.conn.execute("SELECT * FROM triples").fetchall()
        else:
            conditions = []
            params = [entity]
            if direction in ("incoming", "both"):
                conditions.append("subject = ?")
                params.append(entity)
            if direction in ("outgoing", "both"):
                conditions.append("object = ?")
                params.append(entity)

            where_clause = " OR ".join(conditions)
            if as_of:
                where_clause += " AND (valid_from IS NULL OR valid_from <= ?)"
                params.append(as_of)
                where_clause += " AND (valid_to IS NULL OR valid_to >= ?)"
                params.append(as_of)

            rows = self.conn.execute(
                f"SELECT * FROM triples WHERE {where_clause}", params).fetchall()

        return [
            {
                "subject": r[1], "predicate": r[2], "object": r[3],
                "valid_from": r[4], "valid_to": r[5],
                "confidence": r[6] if len(r) > 6 else 1.0,
            }
            for r in rows
        ]

    def close(self):
        self.conn.close()
