"""
Compress — Comprime una sesión usando el LLM disponible.

Detecta automáticamente qué LLM está disponible y lo usa:
1. Haiku vía CLI de Claude (si existe y OAuth está configurado) → mejor compresión
2. LLM local vía CLI de Claude Code (si no hay Haiku) → funciona siempre
3. llama.cpp CLI directo (fallback si Claude CLI no está en PATH)

Esto hace que el plugin funcione con cualquier configuración:
- Si tienes Claude CLI + OAuth → usas Haiku para compresión óptima
- Si solo tienes un modelo local → usas ese modelo sin problemas

Precios Haiku:
- Input: $0.80 / 1M tokens
- Output: $4.00 / 1M tokens
- Cache: $0.08 / 1M tokens

Para una sesión típica de 5000 tokens → compresión ~60% → 2000 tokens
Costo por compresión con Haiku: ~$0.004 (0.4 centavos)
"""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .types import CompressionResult, SessionExchange


# Umbral mínimo de tokens para intentar compresión
MIN_TOKENS_FOR_COMPRESSION = 500

# Umbral de compresión — si el resultado es menos del 30% del original, saltar
COMPRESSION_RATIO_THRESHOLD = 0.3

# Patrón para detectar cuando el LLM rechaza la solicitud
REJECT_PATTERN = (
    r"^\s*("
    r"i (cannot|can't|can not|won't|will not|am unable|'m unable|am not able)|"
    r"could you|please (provide|paste|share)|i'm sorry|i am sorry"
    r")\b"
)

# Extensiones de modelos soportadas para llama.cpp
SUPPORTED_EXTENSIONS = {".gguf", ".ggml", ".bin"}

# Variables de entorno para configurar el comportamiento
COMPRESS_USE_HAIKU = os.environ.get("CLAUDE_REMEMBER_USE_HAIKU", "auto")  # auto, haiku, local
COMPRESS_MODEL = os.environ.get("CLAUDE_REMEMBER_MODEL", "")  # Modelo a usar (si no hay Haiku)
COMPRESS_MAX_TOKENS = int(os.environ.get("CLAUDE_REMEMBER_MAX_TOKENS", "2048"))
COMPRESS_TIMEOUT = int(os.environ.get("CLAUDE_REMEMBER_TIMEOUT", "60"))


# ──────────────────────────────────────────────────────────────────────
# Detección de LLM disponible
# ──────────────────────────────────────────────────────────────────────

def has_haiku_cli() -> bool:
    """Verifica si la CLI de Claude con Haiku está disponible.

    Requiere:
    - claude CLI instalado en PATH
    - OAuth configurado (token válido)
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return False

    # Verificar que la CLI responde (OAuth configurado)
    try:
        result = subprocess.run(
            [claude_bin, "chat", "--help"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def has_claude_code_cli() -> bool:
    """Verifica si Claude Code CLI está disponible."""
    # Verificar CLAUDE_BIN primero
    claude_bin = os.environ.get("CLAUDE_CODE_BIN") or os.environ.get("CLAUDE_BIN")
    if claude_bin and Path(claude_bin).exists():
        return True

    # Buscar en PATH
    return shutil.which("claude") is not None


def find_claude_code_path() -> Optional[str]:
    """Encuentra la instalación de Claude Code (Windows/Linux/macOS)."""
    # Windows — AppData
    appdata = os.environ.get("APPDATA", "")
    claude_win = Path(appdata) / "Claude" / "clau.exe"
    if claude_win.exists():
        return str(claude_win)

    # Linux/macOS — ~/.claude/bin/claude
    home = Path.home()
    claude_linux = home / ".claude" / "bin" / "claude"
    if claude_linux.exists():
        return str(claude_linux)

    return None


def find_llama_cpp_cli() -> Optional[str]:
    """Encuentra llama.cpp CLI en PATH."""
    # Verificar LLAMA_CPP_BIN primero
    llama_cpp = os.environ.get("LLAMA_CPP_BIN")
    if llama_cpp and Path(llama_cpp).exists():
        return llama_cpp

    # Buscar en PATH
    return shutil.which("llama-cli") or shutil.which("llama-cpp")


def find_model_path() -> Optional[str]:
    """Encuentra la ruta del modelo local configurado."""
    # Verificar CLAUDE_CODE_MODEL_PATH primero
    model = os.environ.get("CLAUDE_CODE_MODEL_PATH", COMPRESS_MODEL)
    if model and Path(model).exists():
        return str(Path(model))

    # Buscar en directorio por defecto
    for ext in SUPPORTED_EXTENSIONS:
        default_model = Path.home() / ".claude-retain" / f"model{ext}"
        if default_model.exists():
            return str(default_model)

    return None


# ──────────────────────────────────────────────────────────────────────
# Llamadas a los diferentes LLMs
# ──────────────────────────────────────────────────────────────────────

def call_haiku(prompt: str, max_tokens: int = COMPRESS_MAX_TOKENS) -> Optional[str]:
    """Llama a Haiku vía CLI de Claude para compresión.

    Requiere OAuth configurado y conectividad de red.
    Es el método preferido porque Haiku es rápido y barato.

    Args:
        prompt: Prompt para compresión
        max_tokens: Máximo de tokens de salida

    Returns:
        Texto comprimido o None si falla
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return None

    try:
        # Aislar el entorno — eliminar variables de sesión para evitar hooks
        env = os.environ.copy()
        for key in list(env.keys()):
            if key.startswith("CLAUDE_") or key == "CLAUDECODE":
                del env[key]

        # Llamar a Claude CLI con Haiku — sin herramientas
        result = subprocess.run(
            [claude_bin, "chat", "--model", "haiku", "--output-format", "json",
             "--max-turns", "1", "--allowedTools", ""],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=COMPRESS_TIMEOUT,
            env=env,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        if not output:
            return None

        # Verificar si Haiku rechazó la solicitud
        if re.search(REJECT_PATTERN, output, re.IGNORECASE):
            return None

        return output

    except (subprocess.TimeoutExpired, OSError, RuntimeError):
        return None


def call_local_via_claude_cli(prompt: str, max_tokens: int = COMPRESS_MAX_TOKENS) -> Optional[str]:
    """Llama al LLM local usando la CLI de Claude Code.

    Funciona con cualquier modelo local (Qwopus, Gemma, Mistral, etc.)
    El truco: --allowedTools "" desactiva herramientas y evita hooks.

    Args:
        prompt: Prompt para compresión
        max_tokens: Máximo de tokens de salida

    Returns:
        Texto comprimido o None si falla
    """
    claude_bin = find_claude_cli() or find_claude_code_path()
    if not claude_bin:
        return None

    try:
        # Aislar el entorno
        env = os.environ.copy()
        for key in list(env.keys()):
            if key.startswith("CLAUDE_") or key == "CLAUDECODE":
                del env[key]

        # Llamar a Claude Code con --allowedTools "" para desactivar herramientas
        result = subprocess.run(
            [claude_bin, "chat", "--output-format", "json",
             "--max-turns", "1", "--allowedTools", ""],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=COMPRESS_TIMEOUT,
            env=env,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        if not output:
            return None

        # Verificar si el LLM rechazó la solicitud
        if re.search(REJECT_PATTERN, output, re.IGNORECASE):
            return None

        return output

    except (subprocess.TimeoutExpired, OSError, RuntimeError):
        return None


def call_llama_cpp(prompt: str, model_path: Optional[str] = None) -> Optional[str]:
    """Llama directamente a llama.cpp si está disponible.

    Es un fallback — usa llama.cpp CLI sin pasar por Claude Code.

    Args:
        prompt: Prompt para compresión
        model_path: Ruta al modelo (opcional — busca automáticamente)

    Returns:
        Texto comprimido o None si falla
    """
    llama_cpp = find_llama_cpp_cli()
    if not llama_cpp:
        return None

    # Buscar modelo si no se especifica
    if model_path is None:
        model_path = find_model_path()

    if not model_path or not Path(model_path).exists():
        return None  # No hay modelo configurado

    try:
        env = os.environ.copy()
        for key in list(env.keys()):
            if key.startswith("CLAUDE_") or key == "CLAUDECODE":
                del env[key]

        result = subprocess.run(
            [llama_cpp, "-m", model_path, "-p", prompt,
             "-n", str(COMPRESS_MAX_TOKENS), "--temp", "0.1"],
            input="",
            capture_output=True,
            text=True,
            timeout=COMPRESS_TIMEOUT,
            env=env,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        return output if output else None

    except (subprocess.TimeoutExpired, OSError):
        return None


# ──────────────────────────────────────────────────────────────────────
# Orquestador — decide qué LLM usar y llama
# ──────────────────────────────────────────────────────────────────────

def call_llm(prompt: str) -> Optional[str]:
    """Llama al LLM para compresión — elige automáticamente según disponibilidad.

    Orden de prioridad:
    1. Haiku (si COMPRESS_USE_HAIKU=haiku o auto y está disponible)
    2. Claude Code CLI con modelo local (si COMPRESS_USE_HAIKU=local o haiku no está disponible)
    3. llama.cpp directo (fallback)

    Args:
        prompt: Prompt para compresión

    Returns:
        Texto comprimido o None si falla
    """
    global COMPRESS_USE_HAIKU

    if COMPRESS_USE_HAIKU == "haiku":
        # Forzar Haiku — verificar disponibilidad
        if not has_haiku_cli():
            return None  # No hay Haiku, no forzar
        result = call_haiku(prompt)
        if result:
            return result  # Haiku funcionó

    elif COMPRESS_USE_HAIKU == "local":
        # Forzar local — verificar disponibilidad
        claude_cli = find_claude_cli() or find_claude_code_path()
        if not claude_cli and not find_llama_cpp_cli():
            return None  # No hay LLM disponible
        result = call_local_via_claude_cli(prompt)
        if result:
            return result
        return call_llama_cpp(prompt)

    else:
        # auto — detectar y usar el mejor disponible
        # Intentar Haiku primero (mejor compresión)
        if has_haiku_cli():
            result = call_haiku(prompt)
            if result:
                return result  # Haiku funcionó

        # Fallback a Claude Code CLI con modelo local
        claude_cli = find_claude_cli() or find_claude_code_path()
        if claude_cli:
            result = call_local_via_claude_cli(prompt)
            if result:
                return result

        # Último fallback — llama.cpp directo
        return call_llama_cpp(prompt)

    return None


# ──────────────────────────────────────────────────────────────────────
# Funciones de compresión
# ──────────────────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Estimación rápida de tokens (1 token ≈ 3-4 caracteres para texto en español)."""
    if not text:
        return 0
    return max(1, len(text) // 3)


def load_compress_prompt() -> str:
    """Carga la plantilla de compresión no destructiva."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_file = prompts_dir / "compress-ndc.prompt.txt"

    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")

    # Fallback inline — plantilla de compresión no destructiva
    return """Apply maximum non-destructive compression. Rules:
- Keep ALL facts, ALL refs, ALL verbs, ALL relationships. Zero information loss.
- Drop: articles (a/the/an), prepositions where context is clear, filler words, prose connectors
- Use shortest form preserving same semantic vector: conf, env, MR, infra, impl, perm, EM, etc
- No prose. Raw signal. Like developer shorthand notes.
- Group entries by subject: if multiple entries describe the same work (same issue, same feature, same file), merge into ONE time-blocked entry (e.g. 08:48-09:22). This is the biggest compression win — 5 entries about the same skill becoming 1 entry.
- Parentheses for context: "script.sh (dev detect via git conf)"
- Semicolons to separate facts within one entry
- Preserve ## timestamp | branch format
- Maintain chronological order — entries must appear oldest to newest
- Every verb, every object, every causal link must survive

No preamble. Just the compressed output.

Text:
{{NOW_CONTENT}}"""


def build_compress_prompt(exchanges: list[SessionExchange]) -> str:
    """Construye el prompt para compresión de sesión."""
    parts = []
    current_date = None

    for ex in exchanges:
        if ex.timestamp and ex.timestamp.date() != current_date:
            current_date = ex.timestamp.date()
            parts.append(f"\n## {current_date.strftime('%Y-%m-%d')} | {ex.timestamp.strftime('%H%M')}-{datetime.now().strftime('%H%M')}")

        # Mensaje humano (resumido)
        if ex.human_msg:
            human_preview = ex.human_msg[:200]
            parts.append(f"\n> {human_preview}")

        # Herramientas usadas
        for tool_name, tool_input in ex.tools_used:
            parts.append(f"\n[TOOL: {tool_name}]")
            if isinstance(tool_input, dict):
                for k, v in list(tool_input.items())[:3]:
                    val = str(v)
                    if len(val) > 50:
                        val = val[:50] + "..."
                    parts.append(f"  {k}: {val}")

        # Respuesta del agente (resumida)
        if ex.agent_msg:
            agent_preview = ex.agent_msg[:200]
            parts.append(f"\n> {agent_preview}...")

    compressed_text = "\n".join(parts)

    # Cargar y rellenar plantilla
    template = load_compress_prompt()
    return template.replace("{{NOW_CONTENT}}", compressed_text)


def compress_session(exchanges: list[SessionExchange]) -> CompressionResult:
    """Comprime una sesión de Claude Code con el LLM disponible.

    Funciona con cualquier configuración:
    - Haiku vía CLI → compresión óptima (más precisa, ~$0.004 por sesión)
    - Modelo local vía Claude Code CLI → funciona siempre sin dependencias extra
    - llama.cpp directo → último fallback

    Args:
        exchanges: Lista de intercambios humano/agente de la sesión

    Returns:
        CompressionResult con el texto comprimido o skip reason
    """
    if not exchanges:
        return CompressionResult(
            success=False, skipped=True, reason="No hay intercambios en la sesión"
        )

    # Calcular tamaño aproximado
    total_text = "\n".join(ex.human_msg + ex.agent_msg for ex in exchanges)
    original_tokens = estimate_tokens(total_text)

    if original_tokens < MIN_TOKENS_FOR_COMPRESSION:
        return CompressionResult(
            success=False, skipped=True, reason=f"Sesión muy corta ({original_tokens} tokens)",
            tokens_before=original_tokens, tokens_after=0
        )

    # Construir prompt y llamar al LLM
    prompt = build_compress_prompt(exchanges)
    compressed_text = call_llm(prompt)

    if compressed_text is None:
        return CompressionResult(
            success=False, skipped=True, reason="LLM no respondió o rechazó",
            tokens_before=original_tokens, tokens_after=0
        )

    # Verificar ratio de compresión
    compressed_tokens = estimate_tokens(compressed_text)
    compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

    if compression_ratio < COMPRESSION_RATIO_THRESHOLD:
        return CompressionResult(
            success=False, skipped=True, reason=f"Compresión demasiado agresiva ({compression_ratio:.0%})",
            tokens_before=original_tokens, tokens_after=compressed_tokens
        )

    return CompressionResult(
        success=True,
        compressed_text=compressed_text,
        tokens_before=original_tokens,
        tokens_after=compressed_tokens,
    )


def compress_last_session() -> Optional[CompressionResult]:
    """Comprime la última sesión del historial.

    Atajo — no necesita una lista de intercambios previa.
    """
    from .extract import extract_session
    exchanges = extract_session()
    if not exchanges:
        return None
    return compress_session(exchanges)
