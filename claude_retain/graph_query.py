"""
Graph Query Engine — Combina ChromaDB + SQLite + texto comprimido.

Query engine para Claude que combina las 3 capas de almacenamiento:
1. ChromaDB (búsqueda semántica)
2. SQLite (relaciones estructurales)
3. Texto comprimido (resumen para Claude)

Retorna resultados ordenados por relevancia y sugiere qué archivos leer.
"""

from typing import List, Dict, Any
from .project_graph import ProjectGraphManager


# ──────────────────────────────────────────────────────────────────────
# GraphQueryEngine
# ──────────────────────────────────────────────────────────────────────

class GraphQueryEngine:
    """Engine de consultas que combina las 3 capas del graph."""

    def __init__(self, project_root: str = None):
        self.graph = ProjectGraphManager(project_root)

    def query(self, question: str, n_results: int = 5) -> Dict[str, Any]:
        """Query principal — combina todas las capas.

        Flujo:
        1. ChromaDB (semántica) → resultados por similitud
        2. SQLite (estructural) → relaciones del nodo más relevante
        3. index.md (texto) → contexto de alto nivel

        Returns:
            Resultados combinados con tipo y relevancia.
        """
        # Paso 1: Búsqueda semántica
        semantic_results = self.graph.query_semantic(question, n_results)

        # Paso 2: Si ChromaDB no devuelve resultados, usar SQLite
        structural_results = []
        if not semantic_results or semantic_results[0].get("error"):
            # Buscar por keyword en el graph estructural
            keywords = self._extract_keywords(question)
            for kw in keywords[:3]:
                result = self.graph.query_structural(kw)
                if result.get("node") and (result["imports"] or result["imported_by"] or result.get("defines") or result.get("extends")):
                    structural_results.append({
                        "type": "structural",
                        "keyword": kw,
                        "imports": result["imports"],
                        "imported_by": result["imported_by"],
                        "calls": result["calls"],
                        "defines": result.get("defines", []),
                        "extends": result.get("extends", []),
                    })

        # Paso 3: Contexto del index.md
        index_context = ""
        if semantic_results and len(semantic_results) > 0 and not semantic_results[0].get("error"):
            # Si ChromaDB devolvió resultados, buscar el nodo más relevante en SQLite
            most_relevant = semantic_results[0]
            source = most_relevant.get("source", "")
            if source:
                structural_info = self.graph.query_structural(source)
                if structural_info.get("node"):
                    index_context = f"\n### Relaciones de {source}\n"
                    if structural_info["imports"]:
                        index_context += f"- Importa: {', '.join(structural_info['imports'])}\n"
                    if structural_info["imported_by"]:
                        index_context += f"- Importado por: {', '.join(structural_info['imported_by'])}\n"
                    if structural_info.get("defines"):
                        index_context += f"- Definiciones: {', '.join(structural_info['defines'])}\n"
                    if structural_info.get("extends"):
                        index_context += f"- Herencia (extends): {', '.join(structural_info['extends'])}\n"

        # Paso 4: Evaluar si necesita compactación
        compact_check = self.graph.should_compact()

        # Paso 5: Sugerir archivos si necesita más detalle
        file_suggestions = []
        if semantic_results and not any(r.get("error") for r in semantic_results):
            # Sugerir leer los archivos más relevantes
            for result in semantic_results[:3]:
                source = result.get("source", "")
                if source:
                    file_suggestions.append({
                        "file": source,
                        "relevance": result.get("similarity", 0),
                    })

        return {
            "question": question,
            "semantic_results": semantic_results,
            "structural_results": structural_results,
            "index_context": index_context,
            "needs_compact": compact_check["needs_compact"],
            "compact_reasons": compact_check.get("reasons", []),
            "file_suggestions": file_suggestions,
        }

    def query_node(self, node_name: str) -> Dict[str, Any]:
        """Query estructural de un nodo específico."""
        result = self.graph.query_structural(node_name)

        # Agregar contexto semántico si está disponible
        semantic_context = self.graph.read_index()
        if semantic_context:
            # Buscar sección del nodo en el index
            import re
            pattern = rf"###\s+{re.escape(node_name)}\s*\n(.*?)(?=###|$)"
            match = re.search(pattern, semantic_context, re.DOTALL)
            if match:
                result["index_detail"] = match.group(1).strip()

        return result

    def get_project_overview(self) -> Dict[str, Any]:
        """Overview del proyecto — resumen de alto nivel.

        Incluye:
        - Stats generales (nodos, aristas)
        - Top imports y calls
        - Relaciónes tipadas (extends, defines) — Phase 3
        - Archivos con cruxes — Phase 2
        """
        conn = self.graph.ensure_conn()

        # Stats generales
        total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        total_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        # Top imports (archivos con más imports)
        top_imports = conn.execute("""
            SELECT target, COUNT(*) as cnt
            FROM edges WHERE relation = 'imports'
            GROUP BY target ORDER BY cnt DESC LIMIT 10
        """).fetchall()

        # Top llamadas cruzadas
        top_calls = conn.execute("""
            SELECT source, target, COUNT(*) as cnt
            FROM edges WHERE relation = 'calls'
            GROUP BY source, target ORDER BY cnt DESC LIMIT 10
        """).fetchall()

        # Top defines (Phase 3)
        top_defines = conn.execute("""
            SELECT source, target, COUNT(*) as cnt
            FROM edges WHERE relation = 'defines'
            GROUP BY source, target ORDER BY cnt DESC LIMIT 10
        """).fetchall()

        # Top extends (Phase 3)
        top_extends = conn.execute("""
            SELECT source, target, COUNT(*) as cnt
            FROM edges WHERE relation = 'extends'
            GROUP BY source, target ORDER BY cnt DESC LIMIT 10
        """).fetchall()

        # Archivos con cruxes (Phase 2)
        files_with_cruxes = conn.execute("""
            SELECT COUNT(*) FROM nodes
            WHERE cruxes IS NOT NULL AND cruxes != ''
        """).fetchone()[0]

        # Node types
        node_types = conn.execute("""
            SELECT type, COUNT(*) as cnt
            FROM nodes GROUP BY type ORDER BY cnt DESC
        """).fetchall()

        # Compact check
        compact_check = self.graph.should_compact()

        # Skills instaladas y recomendadas
        skills = self.graph.query_skills()
        recommended = skills.get("recommended_skills", [])
        installed = skills.get("installed_skills", [])

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "top_imports": [{"node": r[0], "count": r[1]} for r in top_imports],
            "top_calls": [{"source": r[0], "target": r[1], "count": r[2]} for r in top_calls],
            "top_defines": [{"source": r[0], "target": r[1], "count": r[2]} for r in top_defines],
            "top_extends": [{"source": r[0], "target": r[1], "count": r[2]} for r in top_extends],
            "files_with_cruxes": files_with_cruxes,
            "node_types": [{"type": r[0], "count": r[1]} for r in node_types],
            "needs_compact": compact_check["needs_compact"],
            "project_type": skills.get("project_type", "unknown"),
            "recommended_skills": recommended,
            "installed_skills_count": len(installed),
        }

    def get_applicable_skills(self, node_name: str = None, task_context: str = None) -> Dict[str, Any]:
        """Devuelve las skills que aplican para un archivo o tarea específica.

        Combina:
        1. Skills recomendadas para el tipo de proyecto (siempre disponibles)
        2. Skills que se aplican a archivos específicos (por extension/tipo)
        3. Skills sugeridas por contexto de la tarea (keyword matching)

        Args:
            node_name: Archivo/nodo específico (opcional)
            task_context: Texto de la tarea/contexto (opcional)

        Returns:
            Dict con skills recomendadas y su relevancia
        """
        # Siempre: skills recomendadas para el tipo de proyecto
        skills_info = self.graph.query_skills()
        project_recommended = set(skills_info.get("recommended_skills", []))

        # Si hay un nodo específico, verificar si alguna skill se aplica directamente
        node_specific = []
        if node_name:
            conn = self.graph.ensure_conn()
            for row in conn.execute("""
                SELECT source_skill, target_node, relation
                FROM skill_edges WHERE target_node = ?
            """, (node_name,)).fetchall():
                node_specific.append({
                    "skill": row[0],
                    "applies_to": row[1],
                    "relation": row[2],
                })

        # Si hay contexto de tarea, hacer keyword matching
        context_skills = []
        if task_context:
            context_lower = task_context.lower()
            for skill_name in project_recommended:
                skill_desc = ""
                # Buscar descripción en installed_skills
                for s in skills_info.get("installed_skills", []):
                    if s["name"] == skill_name:
                        skill_desc = (s.get("description") or "").lower()
                        break
                # Check si la skill es relevante para el contexto
                keywords = {
                    "code-review": ["review", "revisar", "audit", "code review"],
                    "superpowers:systematic-debugging": ["debug", "debugging", "error", "problema", "bug"],
                    "ponytail:ponytail": ["lazy", "eficiente", "simplificar", "refactor", "clean code"],
                    "frontend-design": ["design", "UI", "visual", "estilo", "diseño"],
                    "dataviz": ["chart", "gráfico", "data", "datos", "visualization"],
                    "superpowers:test-driven-development": ["test", "prueba", "TDD"],
                    "fewer-permission-prompts": ["permission", "permiso", "prompt"],
                    "update-config": ["config", "configurar", "settings"],
                }
                for kw in keywords.get(skill_name, []):
                    if kw in context_lower or kw in skill_desc:
                        context_skills.append(skill_name)
                        break

        # Combinar y ordenar por relevancia
        all_applicable = set(project_recommended | set(context_skills))
        return {
            "project_type": skills_info.get("project_type", "unknown"),
            "node": node_name,
            "task_context": task_context,
            "always_applicable": list(project_recommended),
            "context_specific": context_skills,
            "node_specific": node_specific,
            "top_recommended": list(all_applicable)[:5],  # Top 5 más relevantes
        }

    # ──────── Helpers internos ────────

    def _extract_keywords(self, question: str) -> List[str]:
        """Extraer palabras clave de la pregunta para buscar en SQLite."""
        # Eliminar palabras comunes
        stop_words = {
            "qué", "es", "de", "la", "el", "los", "las", "un", "una",
            "what", "is", "of", "the", "in", "to", "for", "and", "or",
            "how", "does", "where", "when", "which", "who",
        }

        # Tokenizar y filtrar
        words = question.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Añadir sufijos comunes de archivos
        suffixes = [".py", ".js", ".ts", ".java", ".go", ".rs", ".rb"]
        for suffix in suffixes:
            keywords.extend(f"{w}{suffix}" for w in words if w not in stop_words)

        return list(set(keywords))  # Deduplicar
