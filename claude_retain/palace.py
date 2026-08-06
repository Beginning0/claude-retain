"""
Palace — Abstraction layer para ChromaDB con sentence-transformers.

Proporciona:
- get_collection(): obtener o crear una colección ChromaDB
- add(): agregar documentos a la colección
- search(): buscar documentos por similitud semántica
- count(): contar documentos en la colección

Dependencias: chromadb, sentence-transformers
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any

DEFAULT_PALACE_PATH = os.path.expanduser("~/.claude-retain/palace")


class PalaceCollection:
    """Wrapper alrededor de una colección ChromaDB con embeddings de sentence-transformers."""

    def __init__(self, collection_name: str = "claude-retain", palace_path: str = None):
        self.collection_name = collection_name
        self.palace_path = palace_path or DEFAULT_PALACE_PATH
        self._collection = None
        self._embedding_fn = None

    def _ensure_initialized(self):
        """Inicializar ChromaDB y el embedding function si no están listos."""
        if self._collection is not None:
            return

        import chromadb
        Path(self.palace_path).mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(path=self.palace_path)

        # Intentar obtener la colección existente primero (puede tener BGE default)
        try:
            self._collection = client.get_collection(name=self.collection_name)
            self._embedding_fn = None  # Usar embedding function de la colección existente
            return
        except Exception:
            pass  # Colección no existe — crearla

        # Crear nueva colección con sentence-transformers (mejor calidad que BGE)
        try:
            from sentence_transformers import SentenceTransformer
            self._embedding_fn = SentenceTransformer("all-MiniLM-L6-v2")

            self._collection = client.create_collection(
                name=self.collection_name,
                embedding_function=lambda x: self._embedding_fn.encode(x).tolist(),
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            # sentence-transformers no disponible — usar ChromaDB default (BGE)
            self._collection = client.create_collection(self.collection_name)

    def add(
        self,
        documents: List[str],
        ids: List[str],
        metadatas: Optional[List[Dict]] = None,
    ) -> Dict:
        """Agregar documentos a la colección."""
        self._ensure_initialized()
        if metadatas is None:
            metadatas = [{}] * len(documents)
        return self._collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )

    def query(
        self,
        query_texts: Optional[List[str]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
    ) -> Dict:
        """Buscar documentos por similitud semántica."""
        self._ensure_initialized()
        if query_texts is None:
            return {"error": "query_texts requerido"}

        if where:
            results = self._collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where,
            )
        else:
            results = self._collection.query(
                query_texts=query_texts,
                n_results=n_results,
            )

        # Convertir distancias coseno a similitud
        if results.get("distances"):
            for i in range(len(results["distances"])):
                for j in range(len(results["distances"][i])):
                    results["distances"][i][j] = max(0.0, 1.0 - results["distances"][i][j])

        return results

    def count(self) -> int:
        """Contar documentos en la colección."""
        self._ensure_initialized()
        return self._collection.count()

    def get(self, limit: int = 50, offset: int = 0) -> Dict:
        """Obtener documentos de la colección."""
        self._ensure_initialized()
        try:
            return self._collection.get(limit=limit, offset=offset)
        except Exception as e:
            return {"error": str(e), "ids": [], "documents": [], "metadatas": []}

    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict] = None):
        """Eliminar documentos de la colección."""
        self._ensure_initialized()
        if ids is not None:
            return self._collection.delete(ids=ids)
        if where is not None:
            return self._collection.delete(where=where)
        return []

    def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
    ):
        """Actualizar documentos existentes."""
        self._ensure_initialized()
        return self._collection.update(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def reset(self):
        """Eliminar toda la colección y recrearla vacía."""
        if self._collection is None:
            return
        import chromadb
        client = chromadb.PersistentClient(path=self.palace_path)
        client.delete_collection(self.collection_name)
        self._collection = None

    def close(self):
        """Cerrar recursos (ChromaDB no requiere cierre explícito)."""
        self._collection = None


def get_collection(palace_path: str = None, create: bool = True) -> Optional[PalaceCollection]:
    """Obtener o crear una colección Palace.

    Args:
        palace_path: Ruta a la base de datos ChromaDB
        create: Si True, crea la colección si no existe

    Returns:
        PalaceCollection o None si hay error
    """
    try:
        return PalaceCollection(
            collection_name="claude-retain",
            palace_path=palace_path,
        )
    except Exception as e:
        if create:
            print(f"[palace] ERROR: no se pudo crear colección: {e}")
        return None
