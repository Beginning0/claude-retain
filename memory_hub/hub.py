"""
Memory Hub — Visualización en terminal de la memoria usada por Claude Code.

Proporciona:
- `!claude-retain stats` — muestra estadísticas de la memoria
- `!claude-retain search <query>` — busca en memoria y muestra resultados
- `!claude-retain layers` — muestra estado de L0-L3
- `!claude-retain graph <entity>` — muestra conocimiento sobre una entidad
- `!claude-retain llm-cache stats` — estadísticas del cache LLM
- `!claude-retain llm-cache clear` — limpia el cache LLM

Se activa como comando slash en Claude Code.
"""

import os
import sys
from typing import Dict, List, Optional
from pathlib import Path

# Fix para codificación en Windows — reemplazar caracteres Unicode al imprimir
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    _orig_write = sys.stdout.write
    def _fix_unicode(s):
        return s.encode("cp1252", errors="ignore").decode("cp1252", errors="ignore")
    sys.stdout.write = lambda s: _orig_write(_fix_unicode(s)) if isinstance(s, str) else _orig_write(s)

# ──────────────────────────────────────────────────────────────────────
# Colores ANSI para la terminal
# ──────────────────────────────────────────────────────────────────────

ANSI_RESET = "\033[0m"
ANSI_YELLOW = "\033[33m"
ANSI_GREEN = "\033[32m"
ANSI_CYAN = "\033[36m"
ANSI_MAGENTA = "\033[35m"
ANSI_BLUE = "\033[34m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_RED = "\033[31m"

# ──────────────────────────────────────────────────────────────────────
# Memory Hub
# ──────────────────────────────────────────────────────────────────────

class MemoryHub:
    """Gestiona la visualización en terminal del sistema de memoria."""

    def __init__(self, memory_manager=None, llm_cache=None):
        self.memory = memory_manager
        self.llm_cache = llm_cache

    # ──────────────────────────────────────────────────────────────────
    # Stats — `!claude-retain stats`
    # ──────────────────────────────────────────────────────────────────

    def show_stats(self) -> str:
        """Muestra estadísticas completas de la memoria."""
        if not self.memory and not self.llm_cache:
            return f"{ANSI_RED}[Memory Hub]{ANSI_RESET} Memoria no disponible — asegúrate de tener claude-retain instalado."

        lines = [f"{ANSI_BOLD}{ANSI_CYAN}═══ Memoria del Agente ═══{ANSI_RESET}"]

        # Stats de memoria
        if self.memory:
            try:
                stats = self.memory.stats()
                lines.append("")
                lines.append(f"{ANSI_YELLOW}L0 — Identidad (siempre cargada){ANSI_RESET}")
                lines.append(f"  Tokens: {stats.get('identity_tokens', '—')}")

                lines.append(f"{ANSI_GREEN}L1 — Historia esencial (auto-generada){ANSI_RESET}")
                lines.append(f"  Tokens: {stats.get('essential_story_tokens', '—')}")

                lines.append(f"{ANSI_CYAN}L2 — On-Demand (filtro por ala/habitación){ANSI_RESET}")
                lines.append(f"  Drawers: {stats.get('total_drawers', '—')}")

                lines.append(f"{ANSI_MAGENTA}L3 — Deep Search (sin límite){ANSI_RESET}")

                lines.append(f"{ANSI_BLUE}Grafo de Conocimiento{ANSI_RESET}")
                lines.append(f"  Triples: {stats.get('knowledge_graph_triples', '—')}")

                total = stats.get("total_wake_up_tokens", 0)
                if total > 0:
                    lines.append("")
                    lines.append(f"{ANSI_YELLOW}{ANSI_BOLD}Costo de inicio: ~{total} tokens{ANSI_RESET}")

            except Exception as e:
                lines.append(f"{ANSI_RED}[Error leyendo stats de memoria]{ANSI_RESET}")

        # Stats del cache LLM
        if self.llm_cache:
            try:
                cache_stats = self.llm_cache.stats()
                lines.append("")
                lines.append(f"{ANSI_MAGENTA}═══ LLM Cache ═══{ANSI_RESET}")

                mem_stats = cache_stats.get("memory", {})
                lines.append(f"{ANSI_YELLOW}Cache en memoria{ANSI_RESET}")
                lines.append(f"  Entradas: {mem_stats.get('total_entries', '—')} / {mem_stats.get('max_size', '—')}")
                lines.append(f"  Expiradas: {mem_stats.get('expired_entries', '—')}")

                pers_stats = cache_stats.get("persistent", {})
                lines.append(f"{ANSI_GREEN}Cache persistente (SQLite){ANSI_RESET}")
                lines.append(f"  Entradas: {pers_stats.get('total_entries', '—')}")
                lines.append(f"  Total hits: {pers_stats.get('total_hits', '—')}")
                size = pers_stats.get('db_size_mb', 0)
                if size > 0:
                    lines.append(f"  Tamaño DB: {size} MB")

            except Exception as e:
                lines.append(f"{ANSI_RED}[Error leyendo stats del cache]{ANSI_RESET}")

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────
    # Search — `!claude-retain search <query>`
    # ──────────────────────────────────────────────────────────────────

    def show_search(self, query: str, wing: str = None, n_results: int = 5) -> str:
        """Busca en memoria y muestra resultados."""
        if not self.memory:
            return f"{ANSI_RED}[Memory Hub]{ANSI_RESET} Memoria no disponible."

        try:
            results = self.memory.search_memories(query, wing=wing, n_results=n_results)

            if not results:
                return f"{ANSI_DIM}No se encontraron resultados para: {query}{ANSI_RESET}"

            lines = [f"{ANSI_BOLD}{ANSI_CYAN}═══ Resultados de búsqueda — '{query}' ═══{ANSI_RESET}"]

            for i, r in enumerate(results, 1):
                if "error" in r:
                    lines.append(f"{ANSI_RED}{r['error']}{ANSI_RESET}")
                    continue

                sim = r.get("similarity", 0)
                wing = r.get("wing", "?")
                room = r.get("room", "?")
                matched = r.get("matched_via", "?")

                lines.append(f"\n{i}. {ANSI_BOLD}{ANSI_GREEN}Sim: {sim:.3f}{ANSI_RESET}  "
                             f"{ANSI_YELLOW}Wing: {wing}{ANSI_RESET}  "
                             f"{ANSI_CYAN}Room: {room}{ANSI_RESET}  "
                             f"{ANSI_MAGENTA}Matched via: {matched}{ANSI_RESET}")

                text = r.get("text", "")
                if len(text) > 300:
                    text = text[:300] + "..."
                lines.append(f"   {ANSI_DIM}{text}{ANSI_RESET}")

            return "\n".join(lines)

        except Exception as e:
            return f"{ANSI_RED}[Error buscando en memoria]{ANSI_RESET}: {e}"

    # ──────────────────────────────────────────────────────────────────
    # Layers — `!claude-retain layers`
    # ──────────────────────────────────────────────────────────────────

    def show_layers(self) -> str:
        """Muestra estado de las 4 capas de memoria."""
        if not self.memory:
            return f"{ANSI_RED}[Memory Hub]{ANSI_RESET} Memoria no disponible."

        lines = [f"{ANSI_BOLD}{ANSI_CYAN}═══ Estado de Capas de Memoria ═══{ANSI_RESET}\n"]

        # L0 — Identity
        identity = self.memory.get_identity()
        identity_tokens = len(identity) // 4 if identity else 0
        lines.append(f"{ANSI_YELLOW}[L0] Identidad{ANSI_RESET} (siempre cargado)")
        lines.append(f"  Tokens: {identity_tokens}")
        lines.append(f"  Estado: {'[OK] Cargado' if identity else '[FAIL] No configurado'}")

        # L1 — Essential Story
        try:
            story = self.memory.get_essential_story()
            story_tokens = len(story) // 4 if story else 0
            lines.append(f"\n{ANSI_GREEN}[L1] Historia esencial{ANSI_RESET} (auto-generado)")
            lines.append(f"  Tokens: {story_tokens}")
            lines.append(f"  Estado: {'[OK] Generado' if story else '[FAIL] No generado'}")
        except Exception:
            lines.append(f"\n{ANSI_GREEN}[L1] Historia esencial{ANSI_RESET} (auto-generado)")
            lines.append(f"  Tokens: —")
            lines.append(f"  Estado: [FAIL] Error al generar")

        # L2 — On-Demand
        try:
            from claude_retain.palace import get_collection
            col = get_collection(palace_path=self.memory.palace_path, create=False)
            drawer_count = col.count() if col else 0
            lines.append(f"\n{ANSI_CYAN}[L2] On-Demand{ANSI_RESET} (filtro por ala/habitación)")
            lines.append(f"  Drawers activos: {drawer_count}")
            lines.append(f"  Estado: [OK]")
        except Exception:
            lines.append(f"\n{ANSI_CYAN}[L2] On-Demand{ANSI_RESET} (filtro por ala/habitación)")
            lines.append(f"  Drawers activos: —")
            lines.append(f"  Estado: [FAIL] Error al leer")

        # L3 — Deep Search
        lines.append(f"\n{ANSI_MAGENTA}[L3] Deep Search{ANSI_RESET} (sin límite)")
        lines.append(f"  Estado: [OK] (búsqueda híbrida BM25 + embeddings)")

        # Grafo de conocimiento
        if self.memory.kg:
            try:
                all_triples = self.memory.kg.query_entity("ALL")
                triple_count = len(all_triples) if all_triples else 0
                lines.append(f"\n{ANSI_BLUE}Grafo de Conocimiento Temporal{ANSI_RESET}")
                lines.append(f"  Triples: {triple_count}")
            except Exception:
                lines.append(f"\n{ANSI_BLUE}Grafo de Conocimiento Temporal{ANSI_RESET}")
                lines.append(f"  Triples: —")

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────
    # Knowledge Graph — `!claude-retain graph <entity>`
    # ──────────────────────────────────────────────────────────────────

    def show_graph(self, entity: str = None) -> str:
        """Muestra conocimiento sobre una entidad del grafo."""
        if not self.memory or not self.memory.kg:
            return f"{ANSI_RED}[Memory Hub]{ANSI_RESET} Grafo de conocimiento no disponible."

        try:
            if entity:
                triples = self.memory.get_knowledge_about(entity)
                lines = [f"{ANSI_BOLD}{ANSI_CYAN}═══ Conocimiento sobre '{entity}' ═══{ANSI_RESET}\n"]

                if not triples:
                    lines.append(f"{ANSI_DIM}No hay conocimiento sobre '{entity}'.{ANSI_RESET}")
                else:
                    for t in triples:
                        lines.append(f"  {ANSI_YELLOW}{t['subject']}{ANSI_RESET} "
                                     f"{ANSI_GREEN}{t['predicate']}{ANSI_RESET} "
                                     f"{ANSI_CYAN}{t['object']}{ANSI_RESET}")
                        if t.get("valid_from"):
                            lines.append(f"    {ANSI_DIM}válido desde: {t['valid_from']} | "
                                         f"confianza: {t.get('confidence', '1.0')}{ANSI_RESET}")
                return "\n".join(lines)

            else:
                # Mostrar entidades principales del grafo
                all_triples = self.memory.kg.query_entity("ALL")
                if not all_triples:
                    return f"{ANSI_DIM}El grafo de conocimiento está vacío.{ANSI_RESET}"

                entities = set()
                for t in all_triples:
                    entities.add(t.get("subject", ""))

                lines = [f"{ANSI_BOLD}{ANSI_CYAN}═══ Entidades en el Grafo ═══{ANSI_RESET}\n"]
                lines.append(f"  Total triples: {len(all_triples)}")
                lines.append(f"\n  {ANSI_YELLOW}Entidades:{ANSI_RESET}")
                for e in sorted(entities):
                    if e and e != "ALL":
                        triple_count = sum(1 for t in all_triples if t.get("subject") == e)
                        lines.append(f"    • {e} ({triple_count} triples)")
                return "\n".join(lines)

        except Exception as e:
            return f"{ANSI_RED}[Error leyendo el grafo]{ANSI_RESET}: {e}"

    # ──────────────────────────────────────────────────────────────────
    # LLM Cache — `!claude-retain llm-cache stats`
    # ──────────────────────────────────────────────────────────────────

    def show_llm_cache_stats(self) -> str:
        """Muestra estadísticas del cache LLM."""
        if not self.llm_cache:
            return f"{ANSI_RED}[Memory Hub]{ANSI_RESET} Cache LLM no disponible."

        try:
            stats = self.llm_cache.stats()
            lines = [f"{ANSI_BOLD}{ANSI_MAGENTA}═══ LLM Cache ═══{ANSI_RESET}\n"]

            mem = stats.get("memory", {})
            lines.append(f"{ANSI_YELLOW}Cache en memoria (LRU, TTL){ANSI_RESET}")
            lines.append(f"  Entradas: {mem.get('total_entries', '—')} / {mem.get('max_size', '—')}")
            lines.append(f"  Expiradas: {mem.get('expired_entries', '—')}")
            lines.append(f"  TTL default: {self.llm_cache.default_ttl:.0f}s")

            pers = stats.get("persistent", {})
            lines.append(f"\n{ANSI_GREEN}Cache persistente (SQLite){ANSI_RESET}")
            lines.append(f"  Entradas: {pers.get('total_entries', '—')}")
            lines.append(f"  Total hits: {pers.get('total_hits', '—')}")
            size = pers.get('db_size_mb', 0)
            if size > 0:
                lines.append(f"  Tamaño: {size} MB")

            return "\n".join(lines)

        except Exception as e:
            return f"{ANSI_RED}[Error leyendo stats del cache]{ANSI_RESET}: {e}"

    def clear_llm_cache(self) -> str:
        """Limpia el cache LLM."""
        if not self.llm_cache:
            return f"{ANSI_RED}[Memory Hub]{ANSI_RESET} Cache LLM no disponible."

        try:
            self.llm_cache.clear_expired()
            return f"{ANSI_GREEN}Cache LLM limpiado (entries expirados eliminados).{ANSI_RESET}"
        except Exception as e:
            return f"{ANSI_RED}[Error limpiando cache]{ANSI_RESET}: {e}"

    # ──────────────────────────────────────────────────────────────────
    # Parseador de comandos
    # ──────────────────────────────────────────────────────────────────

    def handle_command(self, command: str) -> str:
        """Procesa un comando del usuario en el formato `!claude-retain <comando>`.

        Comandos disponibles:
            stats — estadísticas de memoria
            search <query> [wing] — buscar en memoria
            layers — estado de las capas
            graph [entity] — grafo de conocimiento
            llm-cache stats — estadísticas del cache LLM
            llm-cache clear — limpiar cache
            help — ayuda
        """
        parts = command.strip().split()
        if not parts:
            return self._help_text()

        cmd = parts[0].lower()

        if cmd == "stats":
            return self.show_stats()
        elif cmd == "search":
            query = " ".join(parts[1:]) if len(parts) > 1 else ""
            wing = parts[-1] if len(parts) > 2 and not parts[-1].isalpha() else None
            n_results = int(parts[-1]) if len(parts) > 3 and parts[-1].isdigit() else 5
            return self.show_search(query, wing=wing, n_results=n_results)
        elif cmd == "layers":
            return self.show_layers()
        elif cmd == "graph":
            entity = parts[1] if len(parts) > 1 else None
            return self.show_graph(entity)
        elif cmd == "llm-cache" and len(parts) > 1:
            sub = parts[1].lower()
            if sub == "stats":
                return self.show_llm_cache_stats()
            elif sub == "clear":
                return self.clear_llm_cache()
            else:
                return f"{ANSI_RED}Subcomando desconocido: {sub}{ANSI_RESET}"
        elif cmd in ("help", "?"):
            return self._help_text()
        else:
            return f"{ANSI_RED}Comando desconocido: {cmd}.{ANSI_RESET}\nEscribe `!claude-retain help` para ver los comandos."

    @staticmethod
    def _help_text() -> str:
        """Devuelve el texto de ayuda."""
        return (
            f"{ANSI_BOLD}{ANSI_CYAN}═══ Comandos disponibles ═══{ANSI_RESET}\n\n"
            f"  {ANSI_YELLOW}!claude-retain stats{ANSI_RESET}               — Estadísticas de memoria\n"
            f"  {ANSI_YELLOW}!claude-retain search <query>{ANSI_RESET}      — Buscar en memoria\n"
            f"  {ANSI_YELLOW}!claude-retain layers{ANSI_RESET}              — Estado de las capas (L0-L3)\n"
            f"  {ANSI_YELLOW}!claude-retain graph [entity]{ANSI_RESET}      — Grafo de conocimiento\n"
            f"  {ANSI_YELLOW}!claude-retain llm-cache stats{ANSI_RESET}    — Estadísticas del cache LLM\n"
            f"  {ANSI_YELLOW}!claude-retain llm-cache clear{ANSI_RESET}     — Limpiar cache LLM\n"
            f"  {ANSI_YELLOW}!claude-retain help{ANSI_RESET}                — Esta ayuda\n"
        )

