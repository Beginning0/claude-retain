"""
claude-retain Plugin — Time-Travel Debugging (checkpoint/rewind/branch/replay).

Inspirado en Memvid (https://github.com/memvid/memvid) — Time-Travel Debugging.
Cada vez que se guarda un recuerdo, se crea un checkpoint. El usuario puede
navegar entre checkpoints, crear branches y hacer replay de sesiones.
"""

import os
import json
import time
import shutil
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any


CHECKPOINT_DIR = os.path.expanduser("~/.claude-retain/checkpoints")
MAX_CHECKPOINTS = 20  # Retención máxima de checkpoints (como claude-retain)


class CheckpointManager:
    """Gestiona checkpoints de la memoria para Time-Travel Debugging."""

    def __init__(self, palace_path: str = None):
        self.palace_path = palace_path or os.path.expanduser("~/.claude-retain/palace")
        Path(CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)

    # ────────────────────────────────────────────────────────────────────
    # Checkpoints
    # ────────────────────────────────────────────────────────────────────

    def create_checkpoint(self, label: str = None) -> str:
        """Crea un snapshot del estado actual de la memoria.

        Args:
            label: Etiqueta opcional para el checkpoint (ej: "antes-de-fix")

        Returns:
            ID del checkpoint creado
        """
        checkpoint_id = f"ckpt_{int(time.time())}"
        checkpoint_path = os.path.join(CHECKPOINT_DIR, checkpoint_id)

        # Copiar todo el palace como snapshot
        shutil.copytree(self.palace_path, checkpoint_path, dirs_exist_ok=True)

        # Escribir metadata
        meta = {
            "checkpoint_id": checkpoint_id,
            "created_at": time.time(),
            "label": label or "",
            "palace_path": self.palace_path,
            "drawers_count": self._get_drawer_count(),
        }
        meta_file = os.path.join(checkpoint_path, "checkpoint_meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Limpiar checkpoints antiguos (retención máxima)
        self._cleanup_old_checkpoints()

        return checkpoint_id

    def list_checkpoints(self) -> List[Dict]:
        """Lista todos los checkpoints con timestamps y metadata."""
        checkpoints = []
        for entry in os.listdir(CHECKPOINT_DIR):
            if not entry.startswith("ckpt_"):
                continue
            checkpoint_path = os.path.join(CHECKPOINT_DIR, entry)
            meta_file = os.path.join(checkpoint_path, "checkpoint_meta.json")
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                checkpoints.append(meta)

        # Ordenar por timestamp (más reciente primero)
        checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
        return checkpoints

    def rewind(self, checkpoint_id: str) -> bool:
        """Restaura la memoria a un checkpoint anterior.

        Args:
            checkpoint_id: ID del checkpoint a restaurar

        Returns:
            True si se restauró correctamente
        """
        checkpoint_path = os.path.join(CHECKPOINT_DIR, checkpoint_id)
        if not os.path.exists(checkpoint_path):
            print(f"[Checkpoint] ERROR: checkpoint no encontrado — {checkpoint_id}")
            return False

        meta_file = os.path.join(checkpoint_path, "checkpoint_meta.json")
        if not os.path.exists(meta_file):
            print(f"[Checkpoint] ERROR: metadata no encontrada — {checkpoint_id}")
            return False

        # Crear backup del palace actual antes de restaurar
        backup_name = f"palace.pre-rewind.{int(time.time())}"
        backup_path = os.path.join(os.path.expanduser("~/.claude-retain"), backup_name)
        shutil.copytree(self.palace_path, backup_path, dirs_exist_ok=True)

        # Restaurar desde el checkpoint
        try:
            shutil.rmtree(self.palace_path)
            shutil.copytree(checkpoint_path, self.palace_path)
        except Exception as e:
            print(f"[Checkpoint] ERROR restaurando: {e}")
            # Intentar rollback al backup
            try:
                shutil.rmtree(self.palace_path)
                shutil.copytree(backup_path, self.palace_path)
            except Exception:
                pass
            return False

        # Eliminar el backup (ya que se restauró correctamente)
        shutil.rmtree(backup_path)

        print(f"[Checkpoint] Rewind exitoso — {checkpoint_id} ({self._format_time(checkpoint_path)})")
        return True

    def branch(self, base_checkpoint: str, branch_name: str = None) -> str:
        """Crea una bifurcación de memoria para probar soluciones.

        Args:
            base_checkpoint: ID del checkpoint base
            branch_name: Nombre de la bifurcación (opcional)

        Returns:
            ID de la nueva bifurcación
        """
        checkpoint_path = os.path.join(CHECKPOINT_DIR, base_checkpoint)
        if not os.path.exists(checkpoint_path):
            print(f"[Checkpoint] ERROR: checkpoint base no encontrado — {base_checkpoint}")
            return ""

        branch_id = f"branch_{branch_name}_{int(time.time())}" if branch_name else f"branch_{int(time.time())}"
        branch_path = os.path.join(CHECKPOINT_DIR, branch_id)

        # Copiar el palace del checkpoint base a la bifurcación
        shutil.copytree(checkpoint_path, branch_path, dirs_exist_ok=True)

        # Escribir metadata de la bifurcación
        meta = {
            "checkpoint_id": branch_id,
            "created_at": time.time(),
            "label": branch_name or "",
            "palace_path": self.palace_path,
            "drawers_count": self._get_drawer_count(),
            "is_branch": True,
            "base_checkpoint": base_checkpoint,
        }
        meta_file = os.path.join(branch_path, "checkpoint_meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return branch_id

    def replay(self, checkpoint_id: str) -> Dict:
        """Lista los recuerdos que existían en un checkpoint (sin restaurar).

        Args:
            checkpoint_id: ID del checkpoint

        Returns:
            Dict con la información del checkpoint
        """
        meta_file = os.path.join(CHECKPOINT_DIR, checkpoint_id, "checkpoint_meta.json")
        if not os.path.exists(meta_file):
            return {"error": f"checkpoint no encontrado — {checkpoint_id}"}

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Listar los drawers del checkpoint
        palace_path = os.path.join(CHECKPOINT_DIR, checkpoint_id)
        sqlite_path = os.path.join(palace_path, "chroma.sqlite3")
        drawer_count = self._count_drawers_in_checkpoint(palace_path) if os.path.exists(sqlite_path) else 0

        return {
            "checkpoint_id": meta["checkpoint_id"],
            "created_at": meta["created_at"],
            "label": meta.get("label", ""),
            "drawers_count": drawer_count,
            "is_branch": meta.get("is_branch", False),
            "base_checkpoint": meta.get("base_checkpoint"),
        }

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Elimina un checkpoint de la memoria."""
        checkpoint_path = os.path.join(CHECKPOINT_DIR, checkpoint_id)
        if not os.path.exists(checkpoint_path):
            print(f"[Checkpoint] ERROR: checkpoint no encontrado — {checkpoint_id}")
            return False

        shutil.rmtree(checkpoint_path)
        return True

    # ────────────────────────────────────────────────────────────────────
    # Utilidades
    # ────────────────────────────────────────────────────────────────────

    def _get_drawer_count(self) -> int:
        """Cuenta los drawers en el palace actual."""
        try:
            from claude_retain.memory import _get_collection
            col = _get_collection(palace_path=self.palace_path, create=False)
            return col.count() if col else 0
        except Exception:
            return 0

    def _count_drawers_in_checkpoint(self, palace_path: str) -> int:
        """Cuenta los drawers en un checkpoint específico."""
        try:
            sqlite_path = os.path.join(palace_path, "chroma.sqlite3")
            if not os.path.exists(sqlite_path):
                return 0
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def _cleanup_old_checkpoints(self):
        """Elimina checkpoints más antiguos para mantener la retención máxima."""
        checkpoints = self.list_checkpoints()
        if len(checkpoints) > MAX_CHECKPOINTS:
            to_delete = checkpoints[MAX_CHECKPOINTS:]
            for ckpt in to_delete:
                checkpoint_path = os.path.join(CHECKPOINT_DIR, ckpt["checkpoint_id"])
                if os.path.exists(checkpoint_path):
                    shutil.rmtree(checkpoint_path)

    def _format_time(self, checkpoint_path: str) -> str:
        """Formatea el timestamp de un checkpoint en legible."""
        meta_file = os.path.join(checkpoint_path, "checkpoint_meta.json")
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            import datetime
            return datetime.datetime.fromtimestamp(meta["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        return "unknown"

