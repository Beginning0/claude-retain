"""
claude-retain Plugin — Write-Ahead Log (WAL) para crash safety.

Cada operación de escritura va al WAL primero. Cuando se confirma la transacción,
se aplican las operaciones a ChromaDB y se limpia el WAL. Si hay crash,
el recovery aplica las operaciones pendientes del WAL.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any


WAL_DIR = os.path.expanduser("~/.claude-retain/wal")


class WriteAheadLog:
    """Write-Ahead Log para garantizar crash safety en operaciones de escritura."""

    def __init__(self):
        self._current_tx: Optional[Dict] = None
        Path(WAL_DIR).mkdir(parents=True, exist_ok=True)

    def begin(self) -> str:
        """Inicia una nueva transacción. Retorna tx_id."""
        tx_id = f"{int(time.time() * 1000)}"
        self._current_tx = {
            "tx_id": tx_id,
            "started_at": time.time(),
            "operations": [],
        }
        # Escribir WAL activo en disco
        wal_file = os.path.join(WAL_DIR, "wal_current.log")
        with open(wal_file, "w", encoding="utf-8") as f:
            json.dump(self._current_tx, f)
        return tx_id

    def append(self, op: str, doc: str = None, meta: Dict = None,
               id_: str = None) -> bool:
        """Agrega una operación al WAL actual.

        Args:
            op: Tipo de operación — "CREATE", "DELETE", "UPDATE"
            doc: Contenido del documento (para CREATE/UPDATE)
            meta: Metadatos del documento (wing, room, importance, etc.)
            id_: ID del documento (para DELETE/UPDATE)
        """
        if not self._current_tx:
            raise RuntimeError("No hay transacción activa. Llama begin() primero.")

        operation = {
            "tx_id": self._current_tx["tx_id"],
            "op": op,
            "doc": doc,
            "meta": meta,
            "id": id_,
        }
        self._current_tx["operations"].append(operation)

        # Persistir WAL en disco
        wal_file = os.path.join(WAL_DIR, "wal_current.log")
        with open(wal_file, "w", encoding="utf-8") as f:
            json.dump(self._current_tx, f)
        return True

    def commit(self) -> int:
        """Confirma la transacción — aplica operaciones al palace y limpia WAL.

        Returns:
            Número de operaciones aplicadas
        """
        if not self._current_tx:
            raise RuntimeError("No hay transacción activa.")

        applied = 0
        try:
            # Aplicar cada operación al palace
            for operation in self._current_tx["operations"]:
                op_type = operation["op"]
                if op_type == "CREATE":
                    self._apply_create(operation)
                    applied += 1
                elif op_type == "DELETE":
                    self._apply_delete(operation)
                    applied += 1
            # Limpiar WAL después de commit exitoso
            wal_file = os.path.join(WAL_DIR, "wal_current.log")
            if os.path.exists(wal_file):
                os.remove(wal_file)
        except Exception as e:
            print(f"[WAL] Error aplicando operaciones al palace: {e}")
            raise

        self._current_tx = None
        return applied

    def rollback(self):
        """Deshace la transacción — no aplica nada al palace y limpia WAL."""
        if not self._current_tx:
            return

        # Limpiar WAL sin aplicar operaciones
        wal_file = os.path.join(WAL_DIR, "wal_current.log")
        if os.path.exists(wal_file):
            os.remove(wal_file)
        self._current_tx = None

    def recover(self) -> int:
        """En caso de crash, re-aplica operaciones pendientes del WAL.

        Returns:
            Número de operaciones recuperadas
        """
        wal_file = os.path.join(WAL_DIR, "wal_current.log")
        if not os.path.exists(wal_file):
            return 0

        try:
            with open(wal_file, "r", encoding="utf-8") as f:
                tx_data = json.load(f)

            operations = tx_data.get("operations", [])
            applied = 0

            for operation in operations:
                op_type = operation["op"]
                if op_type == "CREATE":
                    self._apply_create(operation)
                    applied += 1
                elif op_type == "DELETE":
                    self._apply_delete(operation)
                    applied += 1

            # WAL recuperado, limpiar archivo
            os.remove(wal_file)
            print(f"[WAL] Recovery: {applied} operaciones recuperadas")
            return applied
        except Exception as e:
            print(f"[WAL] Error en recovery: {e}")
            return 0

    # ────────────────────────────────────────────────────────────────────
    # Operaciones internas
    # ────────────────────────────────────────────────────────────────────

    def _apply_create(self, operation: Dict):
        """Aplica una operación CREATE al palace."""
        from .palace import get_collection
        col = get_collection(palace_path=self.palace_path)
        if col:
            doc = operation.get("doc")
            meta = operation.get("meta", {})
            id_ = f"mem_{operation['tx_id']}"
            # Usar tx_id como ID para consistencia
            if "id" in meta:
                id_ = meta["id"]
            col.add(
                documents=[doc],
                ids=[id_],
                metadatas=[meta],
            )

    def _apply_delete(self, operation: Dict):
        """Aplica una operación DELETE al palace."""
        from .palace import get_collection
        col = get_collection(palace_path=self.palace_path)
        if col:
            id_ = operation.get("id")
            if id_:
                col.delete(ids=[id_])

    # Propiedad para acceder al palace_path
    @property
    def palace_path(self):
        """Obtiene el palace_path desde el entorno o configuración."""
        import os
        return os.path.expanduser(os.environ.get(
            "claude-retain_PALACE_PATH",
            os.path.expanduser("~/.claude-retain/palace")
        ))

