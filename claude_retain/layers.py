"""
Layers — Capas de memoria L1 y L2.

Proporciona:
- Layer0: Identidad del agente (siempre cargada)
- Layer1: Historia esencial con priorización por importancia
- Layer2: On-demand filtering por wing/room
- Layer3: Deep Search (usar searcher.search_memories directamente)

Dependencias: palace, sentence-transformers (opcional)
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any

DEFAULT_PALACE_PATH = os.path.expanduser("~/.claude-retain/palace")


class Layer0:
    """L0 — Identidad del agente (siempre cargada).

    Se guarda en ~/.claude-retain/identity.txt y se carga automáticamente.
    """

    IDENTITY_FILE = os.path.expanduser("~/.claude-retain/identity.txt")

    def __init__(self):
        self._identity = None

    def load(self) -> str:
        """Cargar la identidad."""
        if self._identity is not None:
            return self._identity
        if os.path.exists(self.IDENTITY_FILE):
            try:
                with open(self.IDENTITY_FILE, "r", encoding="utf-8") as f:
                    self._identity = f.read().strip()
            except Exception:
                self._identity = ""
        else:
            self._identity = ""
        return self._identity

    def save(self, identity_text: str) -> bool:
        """Guardar la identidad."""
        try:
            Path(self.IDENTITY_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(self.IDENTITY_FILE, "w", encoding="utf-8") as f:
                f.write(identity_text.strip())
            self._identity = identity_text.strip()
            return True
        except Exception as e:
            print(f"[Layer0] ERROR guardando identidad: {e}")
            return False

    def tokens(self) -> int:
        """Estimar tokens de la identidad."""
        return len(self.load()) // 4 if self.load() else 0


class Layer1:
    """L1 — Historia esencial con priorización.

    Genera un resumen compacto de los recuerdos más importantes del agente.
    Prioriza por:
    1. Importancia (campo importance del metadata)
    2. Recencia (campo timestamp del metadata)
    3. Relevancia semántica (si hay embeddings disponibles)
    """

    MAX_CHARS = 3200  # Límite de caracteres para L1
    TOP_N = 15  # Número máximo de recuerdos a incluir

    def __init__(self, palace_path: str = None, wing: str = None):
        self.palace_path = palace_path or DEFAULT_PALACE_PATH
        self.wing = wing

    def generate(self) -> str:
        """Generar la historia esencial."""
        try:
            from .palace import get_collection
            col = get_collection(palace_path=self.palace_path, create=False)
            if not col:
                return "(sin recuerdos suficientes)"

            results = col.get(limit=50)
            if not results or not results.get("documents"):
                return "(sin recuerdos suficientes)"

            docs = results["documents"]
            metas = results["metadatas"]

            # Calcular score de priorización: importance * 2 + recency_score * 1.5
            scored = []
            now = __import__("time").time()
            for i, meta in enumerate(metas):
                importance = meta.get("importance", 0)
                timestamp = meta.get("timestamp", 0)
                recency = (now - timestamp) / (60 * 60 * 24) if timestamp else 100  # días desde
                recency_score = max(0, 1.0 - (recency / 30))  # decay exponencial de 30 días

                score = importance * 2 + recency_score * 1.5

                # Si está en un wing específico, filtrar
                if self.wing and meta.get("wing") != self.wing:
                    continue

                scored.append({
                    "score": score,
                    "doc": docs[i],
                    "meta": meta,
                })

            # Ordenar por score descendente
            scored.sort(key=lambda x: x["score"], reverse=True)
            top = scored[:self.TOP_N]

            parts = []
            for item in top:
                meta = item["meta"]
                doc = item["doc"]
                wing = meta.get("wing", "?")
                room = meta.get("room", "?")
                importance = meta.get("importance", 1.0)
                # Icono según importancia
                icon = "⭐" if importance >= 2 else "📌" if importance >= 1 else "•"
                parts.append(f"- {icon} [{wing}/{room}] {doc[:100]}")

            story = "\n".join(parts) if parts else "(sin recuerdos suficientes)"

            # Limitar longitud
            if len(story) > self.MAX_CHARS:
                story = story[:self.MAX_CHARS - 3] + "..."

            return story
        except Exception as e:
            print(f"[Layer1] ERROR generando historia esencial: {e}")
            return ""


class Layer2:
    """L2 — On-demand filtering por wing/room.

    Obtiene recuerdos filtrados por ala (wing) y/o habitación (room).
    Ordena por importancia y recencia dentro del filtro.
    """

    MAX_RESULTS = 20

    def __init__(self, palace_path: str = None):
        self.palace_path = palace_path or DEFAULT_PALACE_PATH

    def retrieve(self, wing: str = None, room: str = None, n_results: int = 10) -> List[Dict]:
        """Obtener recuerdos filtrados por wing/room."""
        try:
            from .palace import get_collection
            col = get_collection(palace_path=self.palace_path, create=False)
            if not col:
                return []

            results = col.get(limit=self.MAX_RESULTS)
            if not results or not results.get("documents"):
                return []

            docs = results["documents"]
            metas = results["metadatas"]

            # Filtrar por wing/room
            filtered = []
            now = __import__("time").time()
            for doc, meta in zip(docs, metas):
                if wing and meta.get("wing") != wing:
                    continue
                if room and meta.get("room") != room:
                    continue

                # Calcular score de priorización
                importance = meta.get("importance", 1.0)
                timestamp = meta.get("timestamp", 0)
                recency = (now - timestamp) / (60 * 60 * 24) if timestamp else 100
                recency_score = max(0, 1.0 - (recency / 30))
                score = importance * 2 + recency_score * 1.5

                filtered.append({
                    "score": score,
                    "text": doc,
                    "wing": meta.get("wing", "?"),
                    "room": meta.get("room", "?"),
                    "importance": importance,
                })

            # Ordenar por score y limitar
            filtered.sort(key=lambda x: x["score"], reverse=True)
            return filtered[:n_results]
        except Exception as e:
            print(f"[Layer2] ERROR recuperando recuerdos: {e}")
            return []
