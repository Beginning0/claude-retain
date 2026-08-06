"""
Extract — Extrae intercambios de sesión del historial JSONL de Claude Code.

Basado en claude-remember (Digital-Process-Tools/claude-remember)

El historial se almacena en: ~/.claude/history.jsonl
Cada línea es un JSON con tipo de mensaje y contenido.

Este módulo:
1. Lee el historial JSONL de Claude Code
2. Filtra mensajes no relevantes (system reminders, etc.)
3. Agrupa mensajes humano/agente en intercambios
4. Extrae herramientas usadas por el agente

Dependencias: ninguna (solo stdlib)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .types import SessionExchange


# Carpentas y archivos a ignorar al parsear
IGNORED_SYSTEM_TAGS = {
    "<system-reminder>",
    "</system-reminder>",
    "<reminder>",
    "</reminder>",
}

# Pattern para detectar mensajes de sistema que no son relevantes
SYSTEM_MESSAGE_PATTERNS = [
    "<system-reminder>",
    "</system-reminder>",
    "<reminder>",
    "</reminder>",
    "SessionStart",
    "UserPromptSubmit",
    "PostToolUse",
    "PreToolUse",
]


def find_session_file() -> Optional[Path]:
    """Encuentra el archivo de historial JSONL de Claude Code."""
    home = Path.home() / ".claude"
    # El historial principal
    history_file = home / "history.jsonl"
    if history_file.exists():
        return history_file

    # Buscar backups recientes
    for backup in sorted(home.glob("history.jsonl.*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if backup.exists():
            return backup

    return None


def read_history(file_path: Path) -> list[dict]:
    """Lee las líneas del historial JSONL."""
    messages = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    # Solo mensajes con contenido relevante
                    if "content" in msg and isinstance(msg["content"], str):
                        content = msg["content"]
                        # Saltar mensajes de sistema que no son relevantes
                        if any(tag in content for tag in IGNORED_SYSTEM_TAGS):
                            continue
                        messages.append(msg)
                except json.JSONDecodeError:
                    continue
    except (OSError, IOError):
        pass
    return messages


def format_tool_use(tool_name: str, tool_input: dict, tool_output: Optional[str]) -> str:
    """Formatea el uso de herramientas para compresión."""
    parts = [f"[TOOL: {tool_name}"]

    if tool_input:
        # Resumir inputs — solo los nombres de archivos/paths relevantes
        input_parts = []
        for k, v in tool_input.items():
            if isinstance(v, str) and len(v) > 10:
                input_parts.append(f"{k}={v[:50]}...")
            else:
                input_parts.append(f"{k}={v}")
        parts.append(",".join(input_parts))

    if tool_output:
        # Resumir output — solo las primeras 200 chars
        parts.append(f"→ {tool_output[:200]}...")

    parts.append("]")
    return "".join(parts)


def _is_system_message(content: str) -> bool:
    """Verifica si el contenido es un mensaje de sistema no relevante."""
    if not isinstance(content, str):
        return True
    for pattern in SYSTEM_MESSAGE_PATTERNS:
        if pattern in content:
            return True
    return False


def extract_from_messages(messages: list[dict]) -> list[SessionExchange]:
    """Extrae intercambios de sesión de una lista de mensajes JSONL.

    Agrupa mensajes en pares humano→agente basados en el tipo de mensaje.
    """
    exchanges = []
    current_human = None
    current_tools = []
    current_agent_msg = ""

    for msg in messages:
        msg_type = msg.get("type", "")
        content = msg.get("content", "")

        if not isinstance(content, str):
            continue

        # Mensaje de usuario (humano) — puede ser un nuevo intercambio
        if msg_type == "user":
            # Guardar intercambio anterior si existe
            if current_human is not None:
                exchanges.append(SessionExchange(
                    human_msg=current_human,
                    agent_msg=current_agent_msg.strip(),
                    tools_used=current_tools,
                    timestamp=datetime.now(),
                ))
            current_human = content.strip()
            current_agent_msg = ""
            current_tools = []

        # Mensaje de agente (respuesta) — acumular texto
        elif msg_type == "assistant":
            if isinstance(content, str):
                current_agent_msg += "\n" + content
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            current_agent_msg += "\n" + item.get("text", "")
                        elif item.get("type") == "tool_use":
                            tool_name = item.get("name", "?")
                            tool_input = item.get("input", {})
                            current_tools.append((tool_name, tool_input))

        # Mensaje de herramienta (resultado)
        elif msg_type == "tool":
            if isinstance(content, str):
                current_agent_msg += "\n" + content

    # Guardar último intercambio
    if current_human is not None:
        exchanges.append(SessionExchange(
            human_msg=current_human,
            agent_msg=current_agent_msg.strip(),
            tools_used=current_tools,
            timestamp=datetime.now(),
        ))

    return exchanges


def extract_session(session_id: str = None) -> list[SessionExchange]:
    """Extrae toda la sesión del historial de Claude Code.

    Args:
        session_id: ID de sesión específica (opcional — si no se pasa, usa la actual)

    Returns:
        Lista de intercambios humano/agente
    """
    history_file = find_session_file()
    if not history_file:
        return []

    messages = read_history(history_file)
    return extract_from_messages(messages)


def extract_last_exchange(session_id: str = None) -> Optional[SessionExchange]:
    """Extrae solo el último intercambio de la sesión.

    Útil para auto-save — solo necesita el último cambio, no toda la sesión.
    """
    exchanges = extract_session(session_id)
    return exchanges[-1] if exchanges else None


def extract_tool_summary(exchanges: list[SessionExchange]) -> str:
    """Genera un resumen de herramientas usadas en la sesión."""
    tool_counts = {}
    for ex in exchanges:
        for tool_name, _ in ex.tools_used:
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

    if not tool_counts:
        return ""

    parts = []
    for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
        parts.append(f"{tool}×{count}")

    return " | ".join(parts)
