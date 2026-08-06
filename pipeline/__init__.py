"""
Pipeline — Compresión de sesiones de Claude Code.

Basado en claude-remember (Digital-Process-Tools/claude-remember)

Módulos:
- extract: Extrae intercambios del historial JSONL
- compress: Comprime con el LLM disponible (Haiku, local, llama.cpp)
- consolidate: Fusiona diarios en semanales/mensuales

Configuración por variable de entorno:
- CLAUDE_REMEMBER_USE_HAIKU=auto|haiku|local — qué LLM usar (default: auto)
- CLAUDE_REMEMBER_MODEL=/ruta/al/modelo.gguf — modelo a usar si no hay Haiku
- CLAUDE_REMEMBER_MAX_TOKENS=2048 — máximo de tokens de salida
- CLAUDE_REMEMBER_TIMEOUT=60 — timeout en segundos

Ejemplo:
    from pipeline import compress_last_session, has_haiku_cli, has_local_llm
    print(f"Haiku disponible: {has_haiku_cli()}")
    print(f"LLM local disponible: {has_local_llm()}")
"""

from .types import SessionExchange, DailySummary, WeeklySummary, CompressionResult
from .extract import extract_session, extract_last_exchange
from .compress import (
    compress_session,
    compress_last_session,
    has_haiku_cli,
    has_claude_code_cli,
    call_llm,
)
from .consolidate import run_consolidation, read_daily_summaries

__all__ = [
    "SessionExchange",
    "DailySummary",
    "WeeklySummary",
    "CompressionResult",
    "extract_session",
    "extract_last_exchange",
    "compress_session",
    "compress_last_session",
    "has_haiku_cli",
    "has_claude_code_cli",
    "call_llm",
    "run_consolidation",
    "read_daily_summaries",
]
