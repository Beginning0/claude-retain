"""
Slug — Genera slugs basados en contenido para archivos de memoria.

Basado en claude-remember (Digital-Process-Tools/claude-remember)

Los slugs son identificadores únicos basados en el hash del contenido,
en vez de timestamps aleatorios. Esto permite:
- Identificar duplicados (mismo contenido → mismo slug)
- Evitar archivos duplicados
- Recuperar archivos por contenido

Formato: {prefix}-{hash8}.md
Ejemplo: today-1a2b3c4d.md
"""

import hashlib
from pathlib import Path


def compute_slug(content: str, prefix: str = "mem", length: int = 8) -> str:
    """Genera un slug basado en el hash del contenido.

    Args:
        content: Contenido para generar slug
        prefix: Prefijo del slug (ej: "today", "recent")
        length: Longitud del hash en hex (8 = 32 bits)

    Returns:
        Slug formateado como {prefix}-{hash}.md
    """
    if not content:
        return f"{prefix}-empty.md"

    # Hash SHA-256 del contenido
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{content_hash}.md"


def find_by_slug(prefix: str, slug: str) -> Path | None:
    """Busca un archivo de memoria por su slug.

    Args:
        prefix: Prefijo del archivo (ej: "today")
        slug: Slug a buscar (sin extensión)

    Returns:
        Ruta al archivo o None si no existe
    """
    memory_dir = Path.home() / ".claude-retain" / "memory"
    if not memory_dir.exists():
        return None

    # Buscar por nombre de archivo
    for file in memory_dir.glob(f"{prefix}-{slug}*.md"):
        if file.stem == f"{prefix}-{slug}":
            return file

    return None


def is_duplicate(content: str, prefix: str = "today") -> bool:
    """Verifica si el contenido ya existe como archivo de memoria.

    Args:
        content: Contenido a verificar
        prefix: Prefijo del archivo (ej: "today")

    Returns:
        True si es un duplicado, False si es nuevo
    """
    slug = compute_slug(content, prefix, length=8)
    return find_by_slug(prefix, slug) is not None
