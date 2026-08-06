"""
Auto-Permission — Permisos automáticos para Claude Code.

Categoriza operaciones:
- READ (sin permiso): leer archivos, listar directorios
- SAFE_WRITE (sin permiso): crear archivos nuevos, editar archivos existentes
- DANGEROUS (con backup automático): borrar, mover, renombrar archivos
- DESTRUCTIVE (con confirmación): borrar directorios, operaciones en lote

El sistema de permisos usa un JSON de configuración (~/.claude-retain/auto_permission.json)
donde el usuario puede personalizar qué categorías están habilitadas.
"""

import os
import sys
import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

# Fix para codificación en Windows — reemplazar caracteres Unicode al imprimir
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    _orig_write = sys.stdout.write
    def _fix_unicode(s):
        return s.encode("cp1252", errors="ignore").decode("cp1252", errors="ignore")
    sys.stdout.write = lambda s: _orig_write(_fix_unicode(s)) if isinstance(s, str) else _orig_write(s)

# ──────────────────────────────────────────────────────────────────────
# Colores ANSI
# ──────────────────────────────────────────────────────────────────────

ANSI_RESET = "\033[0m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_CYAN = "\033[36m"
ANSI_BOLD = "\033[1m"

# ──────────────────────────────────────────────────────────────────────
# Categorías de operación
# ──────────────────────────────────────────────────────────────────────

class PermissionLevel:
    READ = "read"
    SAFE_WRITE = "safe_write"
    DANGEROUS = "dangerous"
    DESTRUCTIVE = "destructive"

# Mapeo de operaciones a categorías
OPERATION_CATEGORIES = {
    # Lectura — siempre permitido
    "ls": PermissionLevel.READ,
    "list_dir": PermissionLevel.READ,
    "read_file": PermissionLevel.READ,
    "cat": PermissionLevel.READ,
    "head": PermissionLevel.READ,
    "tail": PermissionLevel.READ,
    "grep": PermissionLevel.READ,
    "find": PermissionLevel.READ,

    # Escritura segura — siempre permitido
    "write_file": PermissionLevel.SAFE_WRITE,
    "create_file": PermissionLevel.SAFE_WRITE,
    "edit_file": PermissionLevel.SAFE_WRITE,
    "append_file": PermissionLevel.SAFE_WRITE,
    "mkdir": PermissionLevel.SAFE_WRITE,

    # Operaciones peligrosas — backup automático
    "rm": PermissionLevel.DANGEROUS,
    "delete_file": PermissionLevel.DANGEROUS,
    "move_file": PermissionLevel.DANGEROUS,
    "rename_file": PermissionLevel.DANGEROUS,
    "copy_file": PermissionLevel.DANGEROUS,

    # Operaciones destructivas — requieren confirmación explícita
    "rm_rf": PermissionLevel.DESTRUCTIVE,
    "delete_dir": PermissionLevel.DESTRUCTIVE,
    "chmod": PermissionLevel.DESTRUCTIVE,
    "chown": PermissionLevel.DESTRUCTIVE,
}

# ──────────────────────────────────────────────────────────────────────
# Auto-Permission
# ──────────────────────────────────────────────────────────────────────

class AutoPermission:
    """Gestiona permisos automáticos para operaciones de Claude Code."""

    # Carpeta donde se guardan los backups automáticos
    BACKUP_DIR = os.path.expanduser("~/.claude-retain/backups")

    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.expanduser("~/.claude-retain/auto_permission.json")
        self._config = self._load_config()

    # ──────────────────────────────────────────────────────────────────
    # Configuración
    # ──────────────────────────────────────────────────────────────────

    def _load_config(self) -> Dict:
        """Carga la configuración desde el archivo JSON."""
        default = {
            "enabled": True,
            "max_backup_size_mb": 50,
            "backup_retention_days": 7,
            "categories": {
                PermissionLevel.READ: {"allowed": True},
                PermissionLevel.SAFE_WRITE: {"allowed": True},
                PermissionLevel.DANGEROUS: {"allowed": True, "auto_backup": True},
                PermissionLevel.DESTRUCTIVE: {"allowed": False},  # Requiere confirmación
            },
        }

        if not os.path.exists(self.config_path):
            return default

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Merge con defaults
            for cat, cat_config in default["categories"].items():
                if cat not in loaded.get("categories", {}):
                    loaded.setdefault("categories", {})[cat] = cat_config
            return loaded
        except Exception:
            return default

    def save_config(self) -> bool:
        """Guarda la configuración actual."""
        try:
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def is_allowed(self, operation: str) -> bool:
        """Verifica si una operación está permitida."""
        if not self._config.get("enabled", True):
            return False

        category = OPERATION_CATEGORIES.get(operation)
        if category is None:
            # Categoría desconocida → denegar por defecto
            return False

        cat_config = self._config.get("categories", {}).get(category, {})
        return cat_config.get("allowed", False)

    def get_category(self, operation: str) -> Optional[str]:
        """Obtiene la categoría de una operación."""
        return OPERATION_CATEGORIES.get(operation)

    # ──────────────────────────────────────────────────────────────────
    # Backup automático (para operaciones DANGEROUS)
    # ──────────────────────────────────────────────────────────────────

    def auto_backup(self, file_path: str, operation: str) -> Optional[str]:
        """Crea un backup automático antes de una operación peligrosa.

        Returns:
            Ruta del backup o None si falló.
        """
        if not self.is_allowed(operation):
            return None

        category = self.get_category(operation)
        if category != PermissionLevel.DANGEROUS:
            return None

        backup_config = self._config.get("categories", {}).get(category, {})
        if not backup_config.get("auto_backup", True):
            return None

        file = Path(file_path)
        if not file.exists():
            return None

        try:
            # Crear carpeta de backup
            backup_dir = Path(self.BACKUP_DIR) / operation / file.parent.name
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Generar nombre con timestamp
            ts = time.strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"{file.stem}_backup_{ts}{file.suffix}"

            # Verificar tamaño (no backup archivos demasiado grandes)
            if file.stat().st_size > self._config.get("max_backup_size_mb", 50) * 1024 * 1024:
                return None

            # Copiar archivo
            shutil.copy2(str(file), str(backup_file))
            return str(backup_file)

        except Exception:
            return None

    def cleanup_old_backups(self):
        """Elimina backups antiguos según el tiempo de retención."""
        try:
            retention_days = self._config.get("backup_retention_days", 7)
            cutoff = time.time() - (retention_days * 86400)

            backup_path = Path(self.BACKUP_DIR)
            if not backup_path.exists():
                return

            for op_dir in backup_path.iterdir():
                if not op_dir.is_dir():
                    continue
                for backup_file in op_dir.iterdir():
                    if backup_file.stat().st_mtime < cutoff:
                        backup_file.unlink()

        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────
    # Verificación de permisos (con mensajes en terminal)
    # ──────────────────────────────────────────────────────────────────

    def check_permission(self, operation: str, path: str = None) -> Dict:
        """Verifica permisos y devuelve el estado.

        Returns:
            Dict con keys: allowed (bool), category (str), requires_backup (bool), backup_path (str|None)
        """
        result = {
            "allowed": False,
            "category": None,
            "requires_backup": False,
            "backup_path": None,
        }

        category = self.get_category(operation)
        if category is None:
            return result

        result["category"] = category
        result["allowed"] = self.is_allowed(operation)

        # Para operaciones DANGEROUS, crear backup automático
        if category == PermissionLevel.DANGEROUS and path:
            result["requires_backup"] = True
            result["backup_path"] = self.auto_backup(path, operation)

        return result

    def format_permission_message(self, result: Dict, operation: str, path: str = None) -> str:
        """Formatea un mensaje de permisos para mostrar al usuario."""
        if not result["allowed"]:
            cat_name = {
                PermissionLevel.READ: "lectura",
                PermissionLevel.SAFE_WRITE: "escritura segura",
                PermissionLevel.DANGEROUS: "operación peligrosa",
                PermissionLevel.DESTRUCTIVE: "operación destructiva",
            }.get(result["category"], "desconocida")

            if result["category"] == PermissionLevel.DESTRUCTIVE:
                return (f"{ANSI_RED}{ANSI_BOLD}[WARN] Permiso denegado:{ANSI_RESET} "
                        f"La operación '{operation}' es destructiva y requiere confirmación manual.")

            return (f"{ANSI_YELLOW}[WARN] Operación no permitida:{ANSI_RESET} "
                    f"'{operation}' está deshabilitada en la configuración.")

        # Permiso concedido
        if result["category"] == PermissionLevel.READ:
            return f"{ANSI_GREEN}[OK] Permiso automático:{ANSI_RESET} Lectura permitida."

        if result["category"] == PermissionLevel.SAFE_WRITE:
            return f"{ANSI_GREEN}[OK] Permiso automático:{ANSI_RESET} Escritura segura permitida."

        if result["category"] == PermissionLevel.DANGEROUS and result.get("backup_path"):
            return (f"{ANSI_YELLOW}[WARN] Permiso automático:{ANSI_RESET} "
                    f"Operación '{operation}' permitida con backup automático: {result['backup_path']}")

        return f"{ANSI_GREEN}[OK] Permiso automático concedido.{ANSI_RESET}"

    # ──────────────────────────────────────────────────────────────────
    # Estado y utilidades
    # ──────────────────────────────────────────────────────────────────

    def status(self) -> str:
        """Muestra el estado actual del sistema de permisos."""
        lines = [f"{ANSI_BOLD}{ANSI_CYAN}═══ Auto-Permission ═══{ANSI_RESET}\n"]

        enabled = self._config.get("enabled", True)
        lines.append(f"  Estado: {'[OK] Habilitado' if enabled else '[FAIL] Deshabilitado'}")

        # Permisos por categoría
        for cat, cat_config in self._config.get("categories", {}).items():
            allowed = cat_config.get("allowed", False)
            auto_backup = cat_config.get("auto_backup", False)

            cat_name = {
                PermissionLevel.READ: "Lectura",
                PermissionLevel.SAFE_WRITE: "Escritura segura",
                PermissionLevel.DANGEROUS: "Peligrosa (backup)",
                PermissionLevel.DESTRUCTIVE: "Destructiva",
            }.get(cat, cat)

            status = "[OK]" if allowed else "[FAIL]"
            extra = f" (auto-backup)" if auto_backup else ""
            lines.append(f"  {status} {cat_name}{extra}")

        return "\n".join(lines)

