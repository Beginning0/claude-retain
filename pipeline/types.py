"""
Tipos de datos para el pipeline de compresión de sesiones.

Basado en claude-remember (Digital-Process-Tools/claude-remember)
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SessionExchange:
    """Una interacción completa en la sesión: humano + agente."""
    human_msg: str  # Texto del mensaje del usuario
    agent_msg: str  # Texto de respuesta del agente
    tools_used: list[str] = field(default_factory=list)  # Herramientas usadas por el agente
    timestamp: Optional[datetime] = None


@dataclass
class DailySummary:
    """Resumen diario de una sesión comprimida."""
    date: str  # YYYY-MM-DD
    time_block: str  # HHMM-HHMM (ej: "0848-0922")
    summary: str  # Texto comprimido no destructivo
    branch: Optional[str] = None


@dataclass
class WeeklySummary:
    """Resumen semanal agrupando resúmenes diarios."""
    week_label: str  # YYYY-Www (ej: "2026-W32")
    daily_summaries: list[DailySummary] = field(default_factory=list)
    consolidated: Optional[str] = None  # Texto consolidado de la semana


@dataclass
class CompressionResult:
    """Resultado de la compresión de una sesión."""
    success: bool
    compressed_text: str  # Texto comprimido
    skipped: bool = False  # Si se saltó (no hay trabajo sustantivo)
    reason: Optional[str] = None  # Razón de skip si aplica
    tokens_before: int = 0
    tokens_after: int = 0
