"""
Consolidate — Fusiona resúmenes diarios en resúmenes semanales/mensuales.

Basado en claude-remember (Digital-Process-Tools/claude-remember)

Proceso:
1. Leer resúmenes diarios actuales (today-*.md)
2. Llamar al LLM para consolidar en weekly.md y monthly.md
3. Rotar resúmenes antiguos a archive.md

Separación de secciones:
===RECENT=== — Resumen de la semana actual
===ARCHIVE=== — Resúmenes de semanas anteriores (rotados)

Si el LLM rechaza o la entrada es demasiado grande, se salta la consolidación.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .compress import call_llm, estimate_tokens
from .types import DailySummary, WeeklySummary


# Directorio donde se almacenan los resúmenes
MEMORY_DIR = Path.home() / ".claude-retain" / "memory"

# Umbral de tokens para saltar consolidación (demasiado grande)
MAX_CONSOLIDATE_TOKENS = 8000

# Patrón de separadores de sección
RECENT_SEPARATOR = "===RECENT==="
ARCHIVE_SEPARATOR = "===ARCHIVE==="

# Cuántos días mantener en memoria antes de rotar a archivo
DAYS_BEFORE_ARCHIVE = 7


def ensure_memory_dir() -> Path:
    """Asegura que el directorio de memoria existe."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR


def read_daily_summaries() -> list[DailySummary]:
    """Lee todos los resúmenes diarios del directorio de memoria."""
    summaries = []
    memory_dir = ensure_memory_dir()

    for file in sorted(memory_dir.glob("today-*.md")):
        try:
            content = file.read_text(encoding="utf-8")
            # Parsear fecha desde nombre de archivo (today-YYYY-MM-DD.md)
            name = file.stem  # "today-2026-08-05"
            date_str = name.replace("today-", "")

            parts = content.split("\n", 1)
            if len(parts) == 2:
                header = parts[0]
                summary_text = parts[1].strip()
            else:
                header = ""
                summary_text = content.strip()

            summaries.append(DailySummary(
                date=date_str,
                time_block="",
                summary=summary_text,
                branch=None,
            ))
        except (OSError, IOError):
            continue

    return summaries


def read_recent_summary() -> Optional[str]:
    """Lee el resumen semanal actual si existe."""
    recent_file = ensure_memory_dir() / "recent.md"
    if not recent_file.exists():
        return None

    content = recent_file.read_text(encoding="utf-8")
    # Buscar sección RECENT
    if RECENT_SEPARATOR in content:
        parts = content.split(RECENT_SEPARATOR)
        if len(parts) > 1:
            return parts[1].split(ARCHIVE_SEPARATOR)[0] if ARCHIVE_SEPARATOR in parts[1] else parts[1]
    return None


def read_archive_summary() -> Optional[str]:
    """Lee el resumen de archivos si existe."""
    archive_file = ensure_memory_dir() / "archive.md"
    if not archive_file.exists():
        return None
    return archive_file.read_text(encoding="utf-8")


def load_consolidate_prompt() -> str:
    """Carga la plantilla de consolidación."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_file = prompts_dir / "consolidate-staging.prompt.txt"

    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")

    # Fallback inline — plantilla de consolidación
    return """You are a memory consolidation assistant. Merge the following daily summaries into a single structured weekly summary.

Rules:
- NEVER add content that wasn't in the source — you compress, you don't create.
- Group entries by subject when multiple days mention the same work.
- Keep chronological order within each section.
- Output MUST use exactly these section headers:
  ===RECENT===
  [weekly summary of last 7 days]
  ===ARCHIVE===
  [older summaries, rotated to archive]

No preamble or explanation. Just the structured output.

Recent summaries:
{{RECENT_CONTENT}}

Archive summaries (if any):
{{ARCHIVE_CONTENT}}"""


def consolidate_daily_summaries(daily_summaries: list[DailySummary]) -> Optional[str]:
    """Consolida resúmenes diarios en un resumen semanal/semestral.

    Args:
        daily_summaries: Lista de resúmenes diarios a consolidar

    Returns:
        Texto consolidado con secciones ===RECENT=== y ===ARCHIVE===
        o None si falla la consolidación
    """
    if not daily_summaries:
        return None

    # Calcular tamaño total
    total_text = "\n".join(s.summary for s in daily_summaries)
    total_tokens = estimate_tokens(total_text)

    if total_tokens > MAX_CONSOLIDATE_TOKENS:
        # Demasiado grande para consolidar — saltar y mantener diarios separados
        return None

    # Separar en recientes (últimos 7 días) y archivos
    recent = [s for s in daily_summaries if _is_recent(s.date)]
    archive = [s for s in daily_summaries if not _is_recent(s.date)]

    recent_content = "\n".join(s.summary for s in recent)
    archive_content = "\n".join(s.summary for s in archive)

    # Construir prompt para consolidación
    template = load_consolidate_prompt()
    prompt = template.replace("{{RECENT_CONTENT}}", recent_content)
    prompt = prompt.replace("{{ARCHIVE_CONTENT}}", archive_content)

    # Llamar al LLM para consolidar
    consolidated = call_llm(prompt)
    if consolidated is None:
        return None

    # Verificar que la respuesta contiene los separadores esperados
    if RECENT_SEPARATOR not in consolidated or ARCHIVE_SEPARATOR not in consolidated:
        # Haiku no siguió el formato — usar texto original
        return recent_content

    return consolidated


def _is_recent(date_str: str) -> bool:
    """Verifica si una fecha está dentro de los últimos 7 días."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (datetime.now().date() - date).days <= DAYS_BEFORE_ARCHIVE
    except ValueError:
        return True  # Si no se puede parsear, asumir reciente


def save_consolidated(recent_text: str, archive_text: Optional[str] = None):
    """Guarda el resumen consolidado en archivos."""
    memory_dir = ensure_memory_dir()

    # Guardar sección RECENT
    recent_file = memory_dir / "recent.md"
    recent_file.write_text(f"{RECENT_SEPARATOR}\n\n{recent_text}", encoding="utf-8")

    # Guardar sección ARCHIVE si existe
    if archive_text:
        archive_file = memory_dir / "archive.md"
        archive_file.write_text(f"{ARCHIVE_SEPARATOR}\n\n{archive_text}", encoding="utf-8")


def run_consolidation() -> bool:
    """Ejecuta la consolidación de memoria.

    Proceso completo:
    1. Leer resúmenes diarios
    2. Leer resumen semanal actual
    3. Llamar al LLM para consolidar todo
    4. Guardar resultado

    Returns:
        True si la consolidación fue exitosa, False si se saltó
    """
    daily_summaries = read_daily_summaries()
    if not daily_summaries:
        return False

    # Intentar consolidar
    consolidated = consolidate_daily_summaries(daily_summaries)

    if consolidated is None:
        # Demasiado grande — mantener diarios separados
        return False

    # Guardar resultado
    save_consolidated(consolidated)

    # Rotar archivos antiguos a archive.md
    rotate_old_daily_summaries()

    return True


def rotate_old_daily_summaries():
    """Mueve resúmenes diarios antiguos a archivo."""
    memory_dir = ensure_memory_dir()
    now = datetime.now().date()

    for file in sorted(memory_dir.glob("today-*.md")):
        try:
            date_str = file.stem.replace("today-", "")
            date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if (now - date).days > DAYS_BEFORE_ARCHIVE:
                # Mover a archivo — renombrar a archive-YYYY-MM-DD.md
                archive_dir = memory_dir / "archive"
                archive_dir.mkdir(exist_ok=True)
                archive_file = archive_dir / f"archive-{date_str}.md"

                # Copiar contenido antes de eliminar
                content = file.read_text(encoding="utf-8")
                archive_file.write_text(content, encoding="utf-8")

                # Eliminar archivo diario original
                file.unlink()

        except (ValueError, OSError):
            continue
