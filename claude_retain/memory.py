"""
claude-retain Plugin — Integración con claude-retain para Claude Code.

Proporciona:
- Búsqueda de memoria persistente (search_memories)
- Guardado de memoria (guardar_memoria)
- Grafo de conocimiento temporal (KnowledgeGraph)
- 4 capas de memoria (L0-L3) con costo controlado de tokens
- Detección automática de entidades

Dependencias: claude-retain (pip install claude-retain)
"""

import os
from pathlib import Path
from typing import Optional, List, Dict

# ──────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────

DEFAULT_PALACE_PATH = os.path.expanduser("~/.claude-retain/palace")
DEFAULT_KG_PATH = os.path.expanduser("~/.claude-retain/knowledge_graph.sqlite3")
IDENTITY_FILE = os.path.expanduser("~/.claude-retain/identity.txt")


# ──────────────────────────────────────────────────────────────────────
# MemoryManager
# ──────────────────────────────────────────────────────────────────────

class MemoryManager:
    """Gestiona la memoria persistente del agente usando claude-retain."""

    def __init__(self, palace_path: str = None, kg_path: str = None):
        self.palace_path = palace_path or DEFAULT_PALACE_PATH
        self.kg_path = kg_path or DEFAULT_KG_PATH
        self._initialized = False
        self.wal = None  # WriteAheadLog instance (initialized lazily)

    def initialize(self) -> bool:
        """Inicializar claude-retain. Se llama una vez al inicio."""
        if self._initialized:
            return True
        try:
            # Asegurar que la carpeta existe
            Path(self.palace_path).mkdir(parents=True, exist_ok=True)
            Path(self.kg_path).parent.mkdir(parents=True, exist_ok=True)

            # Verificar ChromaDB disponible (base de datos de memoria)
            try:
                import chromadb
                self._chromadb_available = True
            except ImportError:
                self._chromadb_available = False
                return False

            # Inicializar knowledge graph temporal
            try:
                from .knowledge_graph import KnowledgeGraph
                self.kg = KnowledgeGraph(self.kg_path)
            except ImportError:
                # Fallback: SQLite inline
                try:
                    self.kg = _SQLiteKnowledgeGraph(self.kg_path)
                except Exception:
                    self.kg = None

            # Inicializar WAL (recovery si hay operaciones pendientes)
            try:
                from claude_retain.wal import WriteAheadLog
                self.wal = WriteAheadLog()
                recovered = self.wal.recover()
                if recovered > 0:
                    print(f"[claude-retain] WAL recovery: {recovered} operaciones recuperadas")
            except Exception as e:
                print(f"[claude-retain] Error inicializando WAL: {e}")

            # Inicializar identity
            self._identity = None
            if os.path.exists(IDENTITY_FILE):
                try:
                    with open(IDENTITY_FILE, "r", encoding="utf-8") as f:
                        self._identity = f.read().strip()
                except Exception:
                    self._identity = ""

            self._initialized = True
            return True
        except Exception as e:
            print(f"[claude-retain] Error de inicialización: {e}")
            self._chromadb_available = False
            self._initialized = True  # No crash, but mark as unavailable
            return False

    # ────────────────────────────────────────────────────────────────────
    # Búsqueda de memoria (L3 — Deep Search)
    # ────────────────────────────────────────────────────────────────────

    def search_memories(self, query: str, wing: str = None, room: str = None,
                       n_results: int = 5, max_distance: float = 1.0) -> List[Dict]:
        """Buscar en la memoria persistente usando búsqueda híbrida (BM25 + embeddings).

        Args:
            query: Consulta natural en lenguaje
            wing: Filtro por ala/proyecto (opcional)
            room: Filtro por habitación/aspecto (opcional)
            n_results: Máximo de resultados a devolver
            max_distance: Máxima distancia coseno para filtrar (0.0 = sin filtro)

        Returns:
            Lista de resultados con similitud, fuente y texto
        """
        if not self._initialized and not self.initialize():
            return [{"error": "claude-retain no está disponible"}]

        try:
            from .searcher import search_memories as _search_memories
            results = _search_memories(
                query=query,
                palace_path=self.palace_path,
                wing=wing,
                room=room,
                n_results=n_results,
                max_distance=max_distance,
            )
            if not results or "error" in results:
                return []
            # Formatear resultados para Claude Code
            formatted = []
            for hit in results.get("hits", []):
                formatted.append({
                    "similarity": hit.get("similarity", 0),
                    "source": hit.get("source_file", "?"),
                    "wing": hit.get("wing", "?"),
                    "room": hit.get("room", "?"),
                    "text": hit.get("text", ""),
                    "matched_via": hit.get("matched_via", "unknown"),
                })
            return formatted
        except Exception as e:
            return [{"error": f"Error buscando memoria: {e}"}]

    # ────────────────────────────────────────────────────────────────────
    # Guardado de memoria (Drawers)
    # ────────────────────────────────────────────────────────────────────

    def save_memory(self, content: str, wing: str = "general", room: str = "general",
                    importance: float = 1.0, auto_checkpoint: bool = True) -> bool:
        """Guardar un recuerdo en la memoria persistente con WAL + checkpoint automático.

        Args:
            content: Contenido del recuerdo (verbatim, sin resumen)
            wing: Ala del recuerdo (proyecto o tema)
            room: Habitación del recuerdo (aspecto)
            importance: Importancia del recuerdo (0-3, default 1.0)
            auto_checkpoint: Si True, crea checkpoint automático después de guardar

        Returns:
            True si se guardó correctamente
        """
        if not self._initialized and not self.initialize():
            return False

        try:
            import time
            import hashlib

            # Iniciar WAL y agregar operación
            if self.wal:
                tx_id = self.wal.begin()
            else:
                tx_id = None

            from .palace import get_collection
            col = get_collection(palace_path=self.palace_path)
            unique_id = hashlib.md5(f"{time.time()}{content}".encode()).hexdigest()[:16]

            meta = {
                "source": "claude_code_plugin",
                "timestamp": time.time(),
                "wing": wing,
                "room": room,
                "importance": importance,
                "normalize_version": 2,
            }

            # Agregar operación al WAL
            if self.wal and tx_id:
                self.wal.append("CREATE", doc=content, meta=meta, id_=f"mem_{unique_id}")
                # Confirmar transacción
                applied = self.wal.commit()

            # También agregar directamente para consistencia inmediata
            col.add(
                documents=[content],
                ids=[f"mem_{unique_id}"],
                metadatas=[meta],
            )

            # Crear checkpoint automático después de guardar
            if auto_checkpoint:
                try:
                    from claude_retain.checkpoints import CheckpointManager
                    ckpt_mgr = CheckpointManager(self.palace_path)
                    checkpoint_id = ckpt_mgr.create_checkpoint(label=f"after-save-{time.strftime('%H%M%S')}")
                except Exception as e:
                    print(f"[claude-retain] Warning: no se pudo crear checkpoint: {e}")

            return True
        except Exception as e:
            # Si hay error, rollback del WAL
            if self.wal and tx_id:
                try:
                    self.wal.rollback()
                except Exception:
                    pass
            print(f"[claude-retain] Error guardando memoria: {e}")
            return False

    # ────────────────────────────────────────────────────────────────────
    # L0 — Identity (siempre cargado)
    # ────────────────────────────────────────────────────────────────────

    def get_identity(self) -> str:
        """Obtener la identidad del agente (L0)."""
        if not self._initialized and not self.initialize():
            return ""
        return self._identity or ""

    def set_identity(self, identity_text: str):
        """Guardar la identidad del agente."""
        try:
            Path(IDENTITY_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(IDENTITY_FILE, "w", encoding="utf-8") as f:
                f.write(identity_text.strip())
            self._identity = identity_text.strip()
            return True
        except Exception as e:
            print(f"[claude-retain] Error guardando identidad: {e}")
            return False

    # ────────────────────────────────────────────────────────────────────
    # L1 — Essential Story (auto-generado)
    # ────────────────────────────────────────────────────────────────────

    def get_essential_story(self, wing: str = None, max_chars: int = 3200) -> str:
        """Obtener la historia esencial del agente (L1).

        Auto-generado desde los drawers de mayor peso en claude-retain.
        """
        if not self._initialized and not self.initialize():
            return ""

        try:
            from .layers import Layer1
            layer = Layer1(palace_path=self.palace_path, wing=wing)
            story = layer.generate()
            if len(story) > max_chars:
                return story[:max_chars - 3] + "..."
            return story
        except Exception:
            return ""

    # ────────────────────────────────────────────────────────────────────
    # L2 — On-Demand (wing/room filtered)
    # ────────────────────────────────────────────────────────────────────

    def get_on_demand(self, wing: str = None, room: str = None, n_results: int = 10) -> List[Dict]:
        """Obtener memoria on-demand filtrada por wing/room (L2)."""
        if not self._initialized and not self.initialize():
            return []

        try:
            from .layers import Layer2
            layer = Layer2(palace_path=self.palace_path)
            results = layer.retrieve(wing=wing, room=room, n_results=n_results)
            # Convertir a formato esperado
            return [
                {
                    "text": r["text"],
                    "wing": r["wing"],
                    "room": r["room"],
                    "importance": r["importance"],
                    "score": r["score"],
                }
                for r in results
            ]
        except Exception:
            return []

    # ────────────────────────────────────────────────────────────────────
    # Grafo de Conocimiento (temporal)
    # ────────────────────────────────────────────────────────────────────

    def add_knowledge_triple(self, subject: str, predicate: str, object_: str,
                            valid_from: str = None, confidence: float = 1.0) -> bool:
        """Agregar un triple al grafo de conocimiento temporal."""
        if not self.kg:
            return False
        try:
            self.kg.add_triple(subject, predicate, object_,
                             valid_from=valid_from, confidence=confidence)
            return True
        except Exception as e:
            print(f"[claude-retain] Error agregando triple: {e}")
            return False

    def get_knowledge_about(self, entity: str, as_of: str = None, direction: str = "both") -> List[Dict]:
        """Obtener todo el conocimiento sobre una entidad del grafo."""
        if not self.kg:
            return []
        try:
            triples = self.kg.query_entity(entity, as_of=as_of, direction=direction)
            return [
                {
                    "subject": t["subject"],
                    "predicate": t["predicate"],
                    "object": t["object"],
                    "valid_from": t.get("valid_from"),
                    "valid_to": t.get("valid_to"),
                    "confidence": t.get("confidence", 1.0),
                }
                for t in triples
            ]
        except Exception:
            return []

    # ────────────────────────────────────────────────────────────────────
    # Detección de entidades (automática)
    # ────────────────────────────────────────────────────────────────────

    def detect_entities_from_text(self, text: str) -> List[Dict]:
        """Detectar personas y proyectos de un texto dado."""
        try:
            from .entity_detector import detect_entities as _detect
            results = _detect([{"path": "conversation", "content": text}])
            return [
                {
                    "name": r.get("name", ""),
                    "type": r.get("type", "unknown"),
                    "score": r.get("score", 0),
                }
                for r in results
            ]
        except Exception:
            # Fallback regex básico
            import re
            names = re.findall(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b', text)
            stop_words = {'EL', 'LA', 'LOS', 'LAS', 'UN', 'UNA', 'DE', 'DEL', 'EN', 'QUE', 'CON', 'POR', 'PARA', 'NO', 'SOB'}
            proper_names = [n for n in re.findall(r'\b([A-Z]{3,})\b', text) if n not in stop_words]
            files = re.findall(r'\b(\w+\.\w+)\b', text)

            entities = []
            for name in names:
                entities.append({"name": name, "type": "person", "score": 1.0})
            for name in proper_names:
                entities.append({"name": name, "type": "project", "score": 0.8})
            for f in files:
                entities.append({"name": f, "type": "file", "score": 0.6})

            seen = set()
            unique = []
            for e in entities:
                if e["name"] not in seen:
                    seen.add(e["name"])
                    unique.append(e)
            return unique

    # ────────────────────────────────────────────────────────────────────
    # Stats y utilidad
    # ────────────────────────────────────────────────────────────────────

    def stats(self) -> Dict:
        """Estadísticas completas de la memoria."""
        stats = {
            "identity_tokens": len(self.get_identity()) // 4 if self.get_identity() else 0,
            "essential_story_tokens": 0,
            "total_drawers": 0,
            "knowledge_graph_triples": 0,
        }

        # Tokens de L1
        try:
            story = self.get_essential_story()
            stats["essential_story_tokens"] = len(story) // 4 if story else 0
        except Exception:
            pass

        # Drawers totales (ChromaDB collection count)
        try:
            from .palace import get_collection
            col = get_collection(palace_path=self.palace_path, create=False)
            stats["total_drawers"] = col.count() if col else 0
        except Exception:
            pass

        # Triples del grafo
        if self.kg:
            try:
                stats["knowledge_graph_triples"] = len(self.kg.query_entity("ALL"))
            except Exception:
                pass

        stats["total_wake_up_tokens"] = stats["identity_tokens"] + stats["essential_story_tokens"]
        return stats

    def close(self):
        """Cerrar recursos."""
        if self.kg:
            self.kg.close()

