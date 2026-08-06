"""
Entry Header — Genera encabezados estructurados para sesiones.

Basado en claude-remember (Digital-Process-Tools/claude-remember)

Formato: ## HHMM | branch
- HHMM: hora de inicio de la sesión
- branch: nombre del branch git actual (si está disponible)

Ejemplo: ## 1423 | main
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path


def get_current_time_block() -> str:
    """Obtiene el bloque de tiempo actual (HHMM)."""
    return datetime.now().strftime("%H%M")


def get_git_branch(repo_path: str = None) -> str:
    """Obtiene el branch git actual del repositorio."""
    if repo_path is None:
        # Buscar directorio de trabajo actual
        repo_path = os.getcwd()

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=repo_path,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass

    return "unknown"


def build_entry_header(repo_path: str = None) -> str:
    """Construye el encabezado de entrada para la sesión.

    Formato: ## HHMM | branch

    Args:
        repo_path: Ruta del repositorio (opcional — busca por defecto)

    Returns:
        Encabezado formateado
    """
    time_block = get_current_time_block()
    branch = get_git_branch(repo_path)
    return f"## {time_block} | {branch}"


def save_entry_header(content: str, repo_path: str = None) -> bool:
    """Guarda el encabezado de entrada en el directorio de memoria.

    Crea un archivo today-YYYY-MM-DD.md con el encabezado y contenido.

    Args:
        content: Contenido del resumen de la sesión
        repo_path: Ruta del repositorio (opcional)

    Returns:
        True si se guardó correctamente
    """
    memory_dir = Path.home() / ".claude-retain" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"today-{today}.md"
    filepath = memory_dir / filename

    header = build_entry_header(repo_path)

    try:
        # Escribir encabezado + contenido
        if filepath.exists():
            existing = filepath.read_text(encoding="utf-8")
            # Append si ya existe (múltiples sesiones en un día)
            content = f"\n\n{content}"
        else:
            content = f"{header}\n\n{content}"

        filepath.write_text(content, encoding="utf-8")
        return True
    except (OSError, IOError):
        return False
