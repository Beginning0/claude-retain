"""
Spawn Guard — Previene consolidación concurrente.

Basado en claude-remember (Digital-Process-Tools/claude-remember)

Si dos sesiones intentan consolidar al mismo tiempo, se corrompe la memoria.
Este módulo usa un archivo de bloqueo para evitar que múltiples procesos
ejecuten la consolidación simultáneamente.
"""

import fcntl
import os
from pathlib import Path


LOCK_FILE = Path.home() / ".claude-retain" / "consolidation.lock"


def acquire_lock() -> bool:
    """Intenta adquirir el lock de consolidación.

    Returns:
        True si se adquirió el lock, False si ya está en uso
    """
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Intentar lock exclusivo no bloqueante
        fd = open(LOCK_FILE, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        return True
    except (IOError, OSError):
        # Ya hay otro proceso con el lock
        return False


def release_lock():
    """Libera el lock de consolidación."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except (OSError, IOError):
        pass
