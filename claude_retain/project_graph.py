"""
Project Graph — Motor del graph del proyecto.

Claude "estudia" el proyecto una vez y luego consulta ese conocimiento en lugar
de releer todo cada vez. 3 capas de almacenamiento:

1. ChromaDB → búsqueda semántica ("¿Qué hace la autenticación?")
2. SQLite → relaciones estructurales ("¿Qué archivos importan auth.py?")
3. Texto comprimido (index.md) → resumen para Claude sin perder contexto
"""

import ast
import os
import re
import sys
import json
import time
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


# ──────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────

GRAPH_DB_PATH = os.path.expanduser("~/.claude-retain/project_graph.db")
INDEX_FILE = os.path.expanduser("~/.claude-retain/project_graph/index.md")
QUERY_LOG_FILE = os.path.expanduser("~/.claude-retain/project_graph/queries.jsonl")

# Umbral de compactación
NODE_COMPACT_THRESHOLD = 50       # nodos → compactar los con < 3 cambios recientes
INDEX_COMPACT_LINES = 1000        # líneas en index.md → resumir módulos antiguos
STALE_QUERY_WINDOW = 24           # horas sin consultas → mover a compacted/
CONTEXT_BUFFER_TOKENS = 5000      # tokens de margen antes del límite

# Extensiones a ignorar (no relevantes para el graph)
IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico",
    ".mp4", ".avi", ".mov", ".wmv", ".flv",
    ".mp3", ".wav", ".ogg", ".flac",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
}

# Mapeo de tipo de proyecto → skills recomendadas
PROJECT_SKILL_MAP = {
    # Python
    "python": ["code-review", "superpowers:systematic-debugging", "ponytail:ponytail"],
    # JavaScript/TypeScript
    "javascript": ["code-review", "frontend-design", "ponytail:ponytail"],
    # Frontend/UI
    "frontend": ["frontend-design", "dataviz", "superpowers:test-driven-development"],
    # Backend/API
    "backend": ["code-review", "ponytail:ponytail", "fewer-permission-prompts"],
    # Full stack
    "fullstack": ["code-review", "frontend-design", "dataviz", "ponytail:ponytail"],
    # Data science / ML
    "datascience": ["dataviz", "superpowers:test-driven-development", "superpowers:brainstorming"],
    # DevOps / infraestructura
    "devops": ["fewer-permission-prompts", "update-config", "superpowers:requesting-code-review"],
}

# Carpetas a ignorar
IGNORED_DIRS = {
    "node_modules", ".git", "__pycache__", ".tox", ".mypy_cache",
    ".pytest_cache", ".venv", "venv", "env", ".env",
    "dist", "build", "target", "out", "bin", "obj",
    ".next", ".nuxt", ".cache", ".idea", ".vscode",
}

# ──────────────────────────────────────────────────────────────────────
# SQLite helpers
# ──────────────────────────────────────────────────────────────────────

def _get_db_path(project_root: str) -> str:
    """DB local por proyecto."""
    project_hash = hashlib.md5(project_root.encode()).hexdigest()[:8]
    db_dir = os.path.expanduser("~/.claude-retain")
    return os.path.join(db_dir, f"project_graph_{project_hash}.db")


def _init_db(db_path: str) -> sqlite3.Connection:
    """Inicializar schema de SQLite si no existe."""
    Path(Path(db_path).parent).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    # Migrar columnas nuevas si la DB existe sin ellas (Phase 2 + Phase 4)
    try:
        conn.execute("ALTER TABLE nodes ADD COLUMN file_hash TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    try:
        conn.execute("ALTER TABLE nodes ADD COLUMN cruxes TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        file_hash TEXT,          -- SHA-256 del contenido (Phase 4)
        cruxes TEXT              -- JSON array de cruxes por archivo (Phase 2)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        relation TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS node_stats (
        node_id TEXT PRIMARY KEY,
        query_count INTEGER DEFAULT 0,
        last_query TEXT,
        change_count INTEGER DEFAULT 0,
        FOREIGN KEY (node_id) REFERENCES nodes(id)
    )""")
    # Tabla de skills instaladas (por proyecto — puede variar por carpeta)
    conn.execute("""CREATE TABLE IF NOT EXISTS project_skills (
        skill_name TEXT PRIMARY KEY,
        source TEXT NOT NULL,       -- "plugin.json" | "appdata" | "claude-retain"
        description TEXT,
        recommended_for TEXT,       -- JSON: ["python", "backend"]
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS skill_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_skill TEXT NOT NULL,  -- "code-review"
        target_node TEXT NOT NULL,   -- "auth.py"
        relation TEXT NOT NULL,      -- "applies_to" | "recommended_for"
        created_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_node_stats_last_query ON node_stats(last_query)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_edges_source ON skill_edges(source_skill)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_edges_target ON skill_edges(target_node)")
    conn.commit()
    return conn

# ──────────────────────────────────────────────────────────────────────
# ProjectGraphManager
# ──────────────────────────────────────────────────────────────────────

class ProjectGraphManager:
    """Motor principal del graph del proyecto."""

    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.db_path = _get_db_path(self.project_root)
        self.conn = None

    # ──────── Conexión ────────

    def ensure_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = _init_db(self.db_path)
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ──────── build_graph — reconstrucción completa ────────

    def build_graph(self, project_root: str = None) -> Dict[str, Any]:
        """Construir o reconstruir el graph completo del proyecto.

        Escanea archivos de código, detecta imports/referencias, crea nodos
        y aristas. También actualiza ChromaDB con embeddings semánticos.
        """
        project_root = project_root or self.project_root
        conn = self.ensure_conn()
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Limpiar graph anterior
        conn.execute("DELETE FROM edges")
        conn.execute("DELETE FROM nodes")
        conn.execute("DELETE FROM node_stats")
        conn.execute("DELETE FROM project_skills")
        conn.execute("DELETE FROM skill_edges")
        conn.commit()
        # Checkpoint WAL to ensure data is visible to other connections
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        # Descubrir skills instaladas del usuario
        skills = self._discover_skills(project_root)
        if skills:
            for skill in skills:
                conn.execute("""INSERT OR REPLACE INTO project_skills
                    (skill_name, source, description, recommended_for, created_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (skill["name"], skill["source"], skill["description"],
                     json.dumps(skill.get("recommended_for", [])), now))

            # Crear aristas entre skills y nodos del proyecto basado en tipo
            project_type = self._detect_project_type(project_root)
            if project_type:
                recommended_skills = PROJECT_SKILL_MAP.get(project_type, [])
                for skill_name in recommended_skills:
                    conn.execute("""INSERT INTO skill_edges (source_skill, target_node, relation, created_at)
                        VALUES (?, 'ALL_PROJECT', 'recommended_for', ?)""",
                        (skill_name, now))

            # Aristas por tipo de archivo → skill
            file_type_skill_map = {
                ".py": ["code-review", "ponytail:ponytail"],
                ".js": ["code-review", "frontend-design"],
                ".ts": ["code-review", "frontend-design"],
                ".jsx": ["frontend-design"],
                ".tsx": ["frontend-design"],
                ".css": ["frontend-design"],
                ".html": ["frontend-design"],
                ".json": [],
                ".yml": ["fewer-permission-prompts", "update-config"],
                ".yaml": ["fewer-permission-prompts", "update-config"],
                ".toml": ["fewer-permission-prompts"],
                ".md": ["superpowers:brainstorming"],
                ".py.test": ["superpowers:test-driven-development"],
            }

        # Escanear archivos
        files = self._scan_files(project_root)
        nodes_created = 0
        edges_created = 0

        for fpath, rel_path in files:
            # Crear nodo del archivo con file_hash y cruxes (Phase 2 + Phase 4)
            summary = self._summarize_file(fpath)
            file_hash = self._compute_file_hash(fpath)
            cruxes = self._extract_cruxes(fpath) if Path(fpath).suffix.lower() == ".py" else []
            conn.execute("""INSERT OR REPLACE INTO nodes
                (id, name, type, summary, created_at, updated_at, file_hash, cruxes)
                VALUES (?, ?, 'file', ?, ?, ?, ?, ?)""",
                (rel_path, rel_path, summary, now, now, file_hash,
                 json.dumps(cruxes) if cruxes else None))
            nodes_created += 1

            # Aristas de archivo → skill basado en tipo de archivo
            ext = Path(fpath).suffix.lower()
            file_skill_map = {
                ".py": ["code-review", "ponytail:ponytail"],
                ".js": ["code-review", "frontend-design"],
                ".ts": ["code-review", "frontend-design"],
                ".jsx": ["frontend-design"],
                ".tsx": ["frontend-design"],
                ".css": ["frontend-design"],
                ".html": ["frontend-design"],
                ".json": [],
                ".yml": ["fewer-permission-prompts", "update-config"],
                ".yaml": ["fewer-permission-prompts", "update-config"],
                ".toml": ["fewer-permission-prompts"],
                ".md": ["superpowers:brainstorming"],
            }
            for skill_name in file_skill_map.get(ext, []):
                conn.execute("""INSERT OR IGNORE INTO skill_edges
                    (source_skill, target_node, relation, created_at)
                    VALUES (?, ?, 'applies_to', ?)""",
                    (skill_name, rel_path, now))

            # Detectar imports/referencias — con AST para Python
            imports = self._detect_imports(fpath, project_root)
            for imp in imports:
                conn.execute("""INSERT INTO edges (source, target, relation, created_at)
                    VALUES (?, ?, 'imports', ?)""",
                    (rel_path, imp, now))
                edges_created += 1

            # Detectar definiciones de clases/funciones — con AST para Python
            defs = self._detect_definitions(fpath)
            for ref in defs:
                conn.execute("""INSERT OR IGNORE INTO nodes
                    (id, name, type, summary, created_at, updated_at)
                    VALUES (?, ?, 'definition', '', ?, ?)""",
                    (ref, ref, now, now))
                conn.execute("""INSERT INTO edges (source, target, relation, created_at)
                    VALUES (?, ?, 'defines', ?)""",
                    (rel_path, ref, now))
                edges_created += 1

            # Detectar relaciones de herencia (extends) — solo para Python
            if ext == ".py":
                extends = self._detect_inheritance(fpath, project_root)
                for src, tgt in extends:
                    conn.execute("""INSERT OR IGNORE INTO nodes
                        (id, name, type, summary, created_at, updated_at)
                        VALUES (?, ?, 'module', '', ?, ?)""",
                        (tgt, tgt, now, now))
                    conn.execute("""INSERT OR REPLACE INTO edges
                        (source, target, relation, created_at)
                        VALUES (?, ?, 'extends', ?)""",
                        (src, tgt, now))
                    edges_created += 1

        # Registrar consultas previas para este proyecto
        self._record_query(project_root, "build_graph")

        return {"nodes_created": nodes_created, "edges_created": edges_created}

    # ──────── incremental_update — actualización por cambios ────────

    def incremental_update(self, changed_files: List[str], project_root: str = None) -> Dict[str, Any]:
        """Actualizar solo los archivos que cambiaron.

        Args:
            changed_files: Lista de rutas relativas de archivos modificados
            project_root: Root del proyecto (default: constructor)
        """
        project_root = project_root or self.project_root
        conn = self.ensure_conn()
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Eliminar aristas viejas de estos archivos
        placeholders = ",".join("?" for _ in changed_files)
        conn.execute(f"DELETE FROM edges WHERE source IN ({placeholders})", changed_files)
        conn.execute(f"DELETE FROM edges WHERE target IN ({placeholders})", changed_files)

        edges_created = 0
        for rel_path in changed_files:
            fpath = os.path.join(project_root, rel_path)
            if not os.path.isfile(fpath):
                continue

            # Phase 4: Solo reconstruir si el hash cambió
            current_hash = self._compute_file_hash(fpath)
            existing = conn.execute("SELECT file_hash FROM nodes WHERE id = ?", (rel_path,)).fetchone()
            if existing and existing[0] == current_hash:
                continue  # Contenido sin cambios — saltar

            # Actualizar nodo (o crearlo si es nuevo) con file_hash y cruxes
            summary = self._summarize_file(fpath)
            cruxes = self._extract_cruxes(fpath) if Path(fpath).suffix.lower() == ".py" else []
            conn.execute("""INSERT OR REPLACE INTO nodes
                (id, name, type, summary, created_at, updated_at, file_hash, cruxes)
                VALUES (?, ?, 'file', ?, ?, ?, ?, ?)""",
                (rel_path, rel_path, summary, now, now, current_hash,
                 json.dumps(cruxes) if cruxes else None))

            # Actualizar aristas — con AST para Python
            imports = self._detect_imports(fpath, project_root)
            for imp in imports:
                conn.execute("""INSERT OR IGNORE INTO nodes
                    (id, name, type, summary, created_at, updated_at)
                    VALUES (?, ?, 'module', '', ?, ?)""",
                    (imp, imp, now, now))
                conn.execute("""INSERT OR REPLACE INTO edges
                    (source, target, relation, created_at)
                    VALUES (?, ?, 'imports', ?)""",
                    (rel_path, imp, now))
                edges_created += 1

            # Definiciones — con AST para Python
            defs = self._detect_definitions(fpath)
            for ref in defs:
                conn.execute("""INSERT OR IGNORE INTO nodes
                    (id, name, type, summary, created_at, updated_at)
                    VALUES (?, ?, 'definition', '', ?, ?)""",
                    (ref, ref, now, now))
                conn.execute("""INSERT OR REPLACE INTO edges
                    (source, target, relation, created_at)
                    VALUES (?, ?, 'defines', ?)""",
                    (rel_path, ref, now))
                edges_created += 1

            # Herencia — solo para Python
            ext = Path(fpath).suffix.lower()
            if ext == ".py":
                extends = self._detect_inheritance(fpath, project_root)
                for src, tgt in extends:
                    conn.execute("""INSERT OR IGNORE INTO nodes
                        (id, name, type, summary, created_at, updated_at)
                        VALUES (?, ?, 'module', '', ?, ?)""",
                        (tgt, tgt, now, now))
                    conn.execute("""INSERT OR REPLACE INTO edges
                        (source, target, relation, created_at)
                        VALUES (?, ?, 'extends', ?)""",
                        (src, tgt, now))
                    edges_created += 1

        conn.commit()
        # Checkpoint WAL to ensure data is visible to other connections
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return {"edges_updated": edges_created}

    # ──────── query_semantic — ChromaDB ────────

    def query_semantic(self, query: str, n_results: int = 5) -> List[Dict]:
        """Buscar en ChromaDB semánticamente.

        Usa claude-retain.palace.get_collection() para buscar archivos/módulos
        relevantes por similitud semántica.
        """
        try:
            from .palace import get_collection
            col = get_collection(palace_path=os.path.expanduser("~/.claude-retain/palace"))
            if not col:
                return []
            results = col.search(query=query, n_results=n_results)
            # Formatear resultados
            formatted = []
            for hit in results.get("hits", []):
                formatted.append({
                    "type": "semantic",
                    "similarity": hit.get("similarity", 0),
                    "source": hit.get("source_file", "?"),
                    "text": hit.get("text", ""),
                })
            return formatted
        except Exception as e:
            return [{"error": f"Error buscando semánticamente: {e}"}]

    # ──────── query_structural — SQLite ────────

    def query_structural(self, node_name: str) -> Dict[str, Any]:
        """Consultar relaciones estructurales de un nodo.

        Retorna:
            - imports: archivos que este importa
            - imported_by: archivos que importan este
            - calls: llamadas cruzadas (funciones/classes referenciadas)
            - defines: definiciones de clases/funciones en este archivo
            - extends: clases que extiende (herencia)
            - cruxes: líneas de lógica central (Phase 2)
        """
        conn = self.ensure_conn()

        # Importa de
        imports = [row[0] for row in conn.execute(
            "SELECT target FROM edges WHERE source = ? AND relation = 'imports'",
            (node_name,)).fetchall()]

        # Importado por
        imported_by = [row[0] for row in conn.execute(
            "SELECT source FROM edges WHERE target = ? AND relation = 'imports'",
            (node_name,)).fetchall()]

        # Llamadas cruzadas
        calls = [row[0] for row in conn.execute(
            "SELECT target FROM edges WHERE source = ? AND relation = 'calls'",
            (node_name,)).fetchall()]

        # Definiciones de clases/funciones
        defines = [row[0] for row in conn.execute(
            "SELECT target FROM edges WHERE source = ? AND relation = 'defines'",
            (node_name,)).fetchall()]

        # Herencia (extends) — ¿qué clases extiende este archivo?
        extends = [row[0] for row in conn.execute(
            "SELECT target FROM edges WHERE source = ? AND relation = 'extends'",
            (node_name,)).fetchall()]

        # Node info
        node = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_name,)).fetchone()
        node_info = None
        if node:
            node_info = {
                "id": node[0], "name": node[1], "type": node[2],
                "summary": node[3], "updated_at": node[5],
                "file_hash": node[6] if len(node) > 6 else None,
            }
            # Incluir cruxes si existen (Phase 2)
            if len(node) > 7 and node[7]:
                try:
                    node_info["cruxes"] = json.loads(node[7])
                except (json.JSONDecodeError, TypeError):
                    node_info["cruxes"] = []

        # Stats de consulta
        stats = conn.execute(
            "SELECT query_count, last_query FROM node_stats WHERE node_id = ?",
            (node_name,)).fetchone()
        query_stats = None
        if stats:
            query_stats = {"query_count": stats[0], "last_query": stats[1]}

        self._record_query(node_name)

        return {
            "node": node_info,
            "imports": imports,
            "imported_by": imported_by,
            "calls": calls,
            "defines": defines,
            "extends": extends,
            "query_stats": query_stats,
        }

    # ──────── read_index — texto comprimido ────────

    def read_index(self) -> str:
        """Leer el index.md (texto comprimido para Claude)."""
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    # ──────── auto_compact — Claude decide cuándo compactar ────────

    def should_compact(self) -> Dict[str, Any]:
        """Evaluar si el graph necesita compactación.

        Reglas:
        1. Graph > 50 nodos → compactar nodos con < 3 cambios recientes
        2. index.md > 1000 líneas → resumir módulos antiguos a 1 línea
        3. Node con 0 consultas en 24h → mover a compacted/
        """
        conn = self.ensure_conn()
        reasons = []

        # Regla 1: nodos totales
        total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        if total_nodes > NODE_COMPACT_THRESHOLD:
            stale_time = (datetime.utcnow() - timedelta(hours=STALE_QUERY_WINDOW)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            stale_nodes = conn.execute(
                "SELECT node_id FROM node_stats WHERE query_count = 0 AND last_query < ?",
                (stale_time,)
            ).fetchall()
            if stale_nodes:
                reasons.append({
                    "rule": "stale_nodes",
                    "detail": f"{len(stale_nodes)} nodos sin consultas en 24h",
                    "nodes": [n[0] for n in stale_nodes],
                })

        # Regla 2: index.md tamaño
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > INDEX_COMPACT_LINES:
                reasons.append({
                    "rule": "index_too_large",
                    "detail": f"index.md tiene {len(lines)} líneas (umbral: {INDEX_COMPACT_LINES})",
                })
        except FileNotFoundError:
            pass

        # Regla 3: nodos sin cambios recientes
        recent_threshold = (datetime.utcnow() - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ")
        no_changes = conn.execute(
            "SELECT id FROM nodes WHERE updated_at < ?", (recent_threshold,)
        ).fetchall()
        if len(no_changes) > total_nodes * 0.3 and total_nodes > 20:
            reasons.append({
                "rule": "too_many_stale_nodes",
                "detail": f"{len(no_changes)} nodos sin cambios en 72h",
            })

        return {
            "needs_compact": len(reasons) > 0,
            "reasons": reasons,
            "total_nodes": total_nodes,
        }

    def compact(self) -> Dict[str, Any]:
        """Compactar el graph según las reglas de Claude.

        Devuelve resumen de lo que se compactó.
        """
        conn = self.ensure_conn()
        compacted = {"stale_nodes_moved": 0, "index_summarized": False}

        # Mover nodos obsoletos a compacted/
        stale_time = (datetime.utcnow() - timedelta(hours=STALE_QUERY_WINDOW)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        stale_nodes = conn.execute(
            "SELECT node_id FROM node_stats WHERE query_count = 0 AND last_query < ?",
            (stale_time,)
        ).fetchall()

        # Crear carpeta compacted si no existe
        compacted_dir = os.path.join(Path(INDEX_FILE).parent, "compacted")
        Path(compacted_dir).mkdir(parents=True, exist_ok=True)

        for node_id in [n[0] for n in stale_nodes]:
            # Guardar resumen antes de eliminar
            node = conn.execute("SELECT summary FROM nodes WHERE id = ?", (node_id,)).fetchone()
            if node and node[0]:
                compacted_file = os.path.join(compacted_dir, f"{node_id}.md")
                with open(compacted_file, "w", encoding="utf-8") as f:
                    f.write(f"# {node_id}\n\n{node[0]}\n")
            # Eliminar aristas y nodo
            conn.execute("DELETE FROM edges WHERE source = ?", (node_id,))
            conn.execute("DELETE FROM edges WHERE target = ?", (node_id,))
            conn.execute("DELETE FROM node_stats WHERE node_id = ?", (node_id,))
            conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            compacted["stale_nodes_moved"] += 1

        conn.commit()
        # Checkpoint WAL to ensure data is visible to other connections
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        # Resumir index.md si es muy grande
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content.split("\n")) > INDEX_COMPACT_LINES:
                # Resumir secciones antiguas a 1 línea
                compacted["index_summarized"] = True
                self._summarize_index(content)
        except FileNotFoundError:
            pass

        return compacted

    # ──────── Query logging ────────

    def _record_query(self, node_name: str = None, query_type: str = None):
        """Registrar una consulta en el log y actualizar stats."""
        os.makedirs(os.path.dirname(QUERY_LOG_FILE), exist_ok=True)

        # Registrar en log
        log_entry = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "node": node_name,
            "type": query_type,
        }
        with open(QUERY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Actualizar stats del nodo
        if node_name:
            conn = self.ensure_conn()
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute("""INSERT OR REPLACE INTO node_stats
                (node_id, query_count, last_query)
                VALUES (?, 1, ?)""", (node_name, now))
            conn.commit()

    # ──────── Helpers internos ────────

    def _scan_files(self, project_root: str) -> List[tuple]:
        """Escanea archivos de código del proyecto.

        Returns:
            Lista de (ruta_absoluta, ruta_relativa)
        """
        files = []
        for root, dirs, filenames in os.walk(project_root):
            # Ignorar carpetas
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS
                       and not d.startswith(".")]

            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in IGNORED_EXTENSIONS:
                    continue
                if fname.startswith(".") and ext not in {".py", ".js", ".ts", ".json", ".yml", ".yaml", ".toml", ".md"}:
                    continue

                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, project_root)
                files.append((abs_path, rel_path))

        return files

    def _summarize_file(self, file_path: str) -> str:
        """Genera un resumen breve de lo que hace un archivo.

        Para Python usa AST para contar clases y funciones con precisión.
        Para otros archivos mantiene la heurística regex.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(8000)  # Limitar lectura

            lines = content.split("\n")
            first_comments = []
            for line in lines[:30]:
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("'''"):
                    first_comments.append(stripped)
                elif stripped:
                    break

            parts = []
            if first_comments:
                parts.append(" ".join(first_comments[:3]))

            # Detectar tipos de definición — usar AST para Python (preciso), regex fallback
            ext = Path(file_path).suffix.lower()
            if ext == ".py":
                try:
                    tree = ast.parse(content, filename=file_path)
                    classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                    functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
                    async_funcs = sum(1 for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef))
                except SyntaxError:
                    # Fallback a regex si hay error de sintaxis
                    classes = len(re.findall(r"\bclass\s+\w+", content[:4000]))
                    functions = len(re.findall(r"\bdef\s+\w+", content[:4000]))
                    async_funcs = len(re.findall(r"\basync\s+def\s+\w+", content[:4000]))
            else:
                classes = len(re.findall(r"\bclass\s+\w+", content[:4000]))
                functions = len(re.findall(r"\bdef\s+\w+", content[:4000]))
                async_funcs = len(re.findall(r"\basync\s+def\s+\w+", content[:4000]))

            if classes or functions:
                details = []
                if classes:
                    details.append(f"{classes} clase{'s' if classes > 1 else ''}")
                if functions:
                    details.append(f"{functions} función{'es' if functions > 1 else ''}")
                if async_funcs:
                    details.append(f"{async_funcs} async")
                parts.append(", ".join(details))

            return " | ".join(parts) if parts else ""
        except Exception:
            return ""

    def _detect_imports(self, file_path: str, project_root: str) -> List[str]:
        """Detecta imports del archivo — usa AST para Python, regex para JS/TS."""
        try:
            ext = Path(file_path).suffix.lower()
            if ext == ".py":
                return self._detect_python_imports(file_path, project_root)

            # JS/TS — mantener regex (funciona bien para ESM/CommonJS)
            imports = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(10000)
            for match in re.finditer(r"require\s*\(\s*['\"](\.\.?\/[^'\"]+)['\"]\s*\)", content):
                imports.append(match.group(1))
            for match in re.finditer(r"import\s+.*\s+from\s+['\"](\.\.?\/[^'\"]+)['\"]", content):
                imports.append(match.group(1))
            return list(set(imports))
        except Exception:
            return []

    def _detect_python_imports(self, file_path: str, project_root: str) -> List[str]:
        """Parsea AST de Python para extraer todos los imports de forma precisa.

        Detecta:
        - import X
        - import X.Y.Z
        - import X as Y
        - from . import X (imports relativos)
        - from X import Y
        - from X.Y import Z as W
        - from .X import Y (relativos con nombre)
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(10000)
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            # Archivos con errores de sintaxis — fallback a regex
            return self._detect_imports_fallback(file_path, project_root)

        module_dir = os.path.relpath(os.path.dirname(file_path), project_root)
        file_rel = os.path.relpath(file_path, project_root)
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # import X, import X.Y.Z, import X as Y
                    mod_name = alias.name.split(".")[0]  # resolver al modulo de nivel superior
                    imp = self._resolve_import(mod_name, module_dir, project_root)
                    if imp and imp != file_rel:
                        imports.add(imp)

            elif isinstance(node, ast.ImportFrom):
                # from X import Y | from .X import Y | from ..X import Y
                level = node.level or 0  # 1+ = relative (from . import X)

                if level > 0:
                    # Import relativo — resolver desde el directorio actual
                    parts = module_dir.split(os.sep)
                    # Retroceder 'level' niveles (desde la carpeta del archivo)
                    base_parts = parts[:-level] if len(parts) >= level else parts
                    base_path = os.path.join(project_root, *base_parts)

                    if node.module:
                        # from .X import Y → resolver X desde base_path
                        candidate = os.path.join(base_path, node.module.replace(".", os.sep))
                        for ext in [".py"]:
                            if os.path.isfile(candidate + ext):
                                imp = os.path.relpath(candidate + ext, project_root)
                                if imp != file_rel:
                                    imports.add(imp)
                                break
                        else:
                            # Es un paquete — buscar __init__.py
                            init_file = os.path.join(candidate, "__init__.py")
                            if os.path.isfile(init_file):
                                imp = os.path.relpath(os.path.join(module_dir.replace(os.sep, "."), node.module.split(".")[0]), project_root)
                                # Resolver de nuevo desde base_path
                                candidate2 = os.path.join(base_path, node.module.replace(".", os.sep))
                                if os.path.isfile(candidate2 + ".py") or os.path.isdir(candidate2):
                                    imp = os.path.relpath(candidate2, project_root)
                                    if imp != file_rel:
                                        imports.add(imp)
                    else:
                        # from . import X — cada alias es un modulo en la carpeta actual
                        for alias in node.names:
                            candidate = os.path.join(base_path, alias.name.replace(".", os.sep))
                            for ext in [".py"]:
                                if os.path.isfile(candidate + ext):
                                    imp = os.path.relpath(candidate + ext, project_root)
                                    if imp != file_rel:
                                        imports.add(imp)
                                    break
                            else:
                                # Buscar como paquete
                                candidate_pkg = os.path.join(base_path, alias.name.replace(".", os.sep))
                                if os.path.isdir(candidate_pkg):
                                    imp = os.path.relpath(candidate_pkg, project_root)
                                    if imp != file_rel:
                                        imports.add(imp)
                else:
                    # Import absoluto — from X.Y import Z
                    parts = node.module.split(".")
                    mod_name = parts[0]

                    # Resolver el modulo completo (X.Y.Z) primero como archivo directo
                    candidate = os.path.join(project_root, *parts)
                    found = False
                    for ext in [".py"]:
                        if os.path.isfile(candidate + ext):
                            imp = os.path.relpath(candidate + ext, project_root)
                            if imp != file_rel:
                                imports.add(imp)
                            found = True
                            break

                    # Si no se encontro como archivo, buscar como paquete
                    if not found:
                        for i in range(len(parts)):
                            pkg_candidate = os.path.join(project_root, *parts[:i + 1], "__init__.py")
                            if os.path.isfile(pkg_candidate):
                                imp = os.path.relpath(os.path.join(project_root, *parts[:i + 1]), project_root)
                                # Ajustar: usar el nombre del modulo, no la ruta completa
                                imp_resolved = self._resolve_import(".".join(parts[:i + 1]), module_dir, project_root)
                                if imp_resolved and imp_resolved != file_rel:
                                    imports.add(imp_resolved)
                                break

        return list(imports)

    def _detect_imports_fallback(self, file_path: str, project_root: str) -> List[str]:
        """Fallback regex para archivos Python con errores de sintaxis."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(10000)

            module_dir = os.path.relpath(os.path.dirname(file_path), project_root)
            module_path = os.path.relpath(file_path, project_root)

            imports = []
            for match in re.finditer(r"\bimport\s+(\w+)", content):
                mod_name = match.group(1)
                imp = self._resolve_import(mod_name, module_dir, project_root)
                if imp and imp != module_path:
                    imports.append(imp)
            for match in re.finditer(r"\bfrom\s+(\w+[\.\w]*)\s+import\b", content):
                mod_name = match.group(1)
                imp = self._resolve_import(mod_name, module_dir, project_root)
                if imp and imp != module_path:
                    imports.append(imp)
            return list(set(imports))
        except Exception:
            return []

    def _detect_definitions(self, file_path: str) -> List[str]:
        """Extrae definiciones de clases y funciones de un archivo usando AST.

        Reemplaza a _detect_cross_refs que producía falsos positivos.
        Ahora solo devuelve nombres de clases y funciones reales.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(10000)

            tree = ast.parse(content, filename=file_path)
            defs = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Incluir el nombre de la clase
                    defs.add(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Incluir el nombre de la función/método
                    defs.add(node.name)

            return list(defs)
        except Exception:
            return []

    def _detect_cross_refs(self, file_path: str, project_root: str) -> List[str]:
        """Detecta referencias cruzadas a funciones/classes de otros archivos.

        DEPRECATED — usar _detect_definitions en su lugar.
        Mantenida por compatibilidad con llamadas existentes.
        """
        return self._detect_definitions(file_path)

    def _resolve_import(self, module_name: str, current_dir: str, project_root: str) -> Optional[str]:
        """Intenta resolver un import a una ruta relativa del proyecto.

        Soporta:
        - imports absolutos: `import X`, `from X.Y import Z`
        - imports relativos: `from . import X`, `from .X import Y`
        - módulos como archivos directos o paquetes con __init__.py
        """
        # Si module_name es un path relativo (ej: "." o ".." o ".claude-retain")
        if module_name.startswith("."):
            parts = module_name.lstrip(".").split(".")
            # Calcular el directorio base basado en los puntos
            level = len(module_name) - len(module_name.lstrip("."))
            base_parts = current_dir.split(os.sep)
            if level > 0:
                # Retroceder 'level' niveles desde la carpeta actual
                base_parts = base_parts[:-level] if len(base_parts) >= level + 1 else []
            base_path = os.path.join(project_root, *base_parts)

            # Buscar como archivo directo
            candidate = os.path.join(base_path, ".".join(parts))
            for ext in [".py"]:
                if os.path.isfile(candidate + ext):
                    return os.path.relpath(candidate + ext, project_root)

            # Buscar como paquete (con __init__.py)
            for ext in [".py"]:
                candidate_pkg = os.path.join(base_path, ".".join(parts))
                init_file = os.path.join(candidate_pkg, "__init__.py")
                if os.path.isdir(candidate_pkg):
                    return os.path.relpath(candidate_pkg, project_root)

            return None

        # Intentar como módulo local (Python)
        parts = module_name.split(".")
        candidate = os.path.join(project_root, *parts)

        # Si es un archivo directo
        for ext in [".py", ".js", ".ts"]:
            if os.path.isfile(candidate + ext):
                return os.path.relpath(candidate + ext, project_root)

        # Si es un directorio con __init__ o index
        for init_file in ["__init__.py", "index.py", "index.ts", "index.js"]:
            candidate_file = os.path.join(candidate, init_file)
            if os.path.isfile(candidate_file):
                return os.path.relpath(os.path.join(module_name, Path(init_file).stem), project_root)

        # Si está en el mismo directorio
        local_candidate = os.path.join(current_dir, module_name.replace(".", "/"))
        for ext in [".py", ".js", ".ts"]:
            if os.path.isfile(local_candidate + ext):
                return os.path.relpath(local_candidate + ext, project_root)

        return None

    # ──────── Phase 4: Hash-based incremental ────────

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file content for change detection."""
        h = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return ""

    # ──────── Phase 2: Cruxes extraction ────────

    def _extract_cruxes(self, file_path: str) -> List[Dict]:
        """Extraer líneas de lógica central (clases, funciones, métodos)."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(50000)  # Límite mayor para cruxes

            tree = ast.parse(content, filename=file_path)
            source_lines = content.split("\n")
            cruxes = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    start_line = node.lineno  # 1-indexed
                    end_line = getattr(node, 'end_lineno', None)
                    if end_line is not None:
                        end_line += 1  # Convertir a 1-indexado para slicing
                    else:
                        continue  # Python < 3.8 — sin end_lineno

                    # Extraer el bloque de código
                    crux_text = "\n".join(source_lines[start_line - 1:end_line]).strip()
                    if crux_text and len(crux_text) > 10:  # Saltar one-liners triviales
                        cruxes.append({
                            "type": "class" if isinstance(node, ast.ClassDef) else "function",
                            "name": node.name,
                            "start_line": start_line,
                            "end_line": end_line,
                            "crux_text": crux_text[:500],  # Limitar para DB storage
                        })

            return cruxes
        except Exception:
            return []

    # ──────── Phase 3: Typed relationships (extends) ────────

    def _detect_inheritance(self, file_path: str, project_root: str) -> List[tuple]:
        """Detecta relaciones de herencia (extends) usando AST."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(50000)

            tree = ast.parse(content, filename=file_path)
            module_dir = os.path.relpath(os.path.dirname(file_path), project_root)
            file_rel = os.path.relpath(file_path, project_root)
            relationships = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        # base could be Name(id='ParentClass') or Attribute(value=Name(id='M'), attr='Mixin')
                        if isinstance(base, ast.Name):
                            parent_name = base.id
                            resolved = self._resolve_import(parent_name, module_dir, project_root)
                            if resolved and resolved != file_rel:
                                relationships.append((file_rel, resolved))
                        elif isinstance(base, ast.Attribute):
                            # e.g., M.Mixin — resolver la parte del modulo
                            parent_name = base.value.id if isinstance(base.value, ast.Name) else ""
                            if parent_name:
                                resolved = self._resolve_import(parent_name, module_dir, project_root)
                                if resolved and resolved != file_rel:
                                    relationships.append((file_rel, resolved))

            return relationships
        except Exception:
            return []

    def _summarize_index(self, content: str):
        """Resumir secciones antiguas del index.md a 1 línea."""
        # Encontrar secciones por encabezado de nivel 2+3
        sections = re.split(r"^(#{2,6}\s+.+)$", content, flags=re.MULTILINE)

        new_content = []
        for i, section in enumerate(sections):
            if i % 2 == 1:  # Encabezado
                new_content.append(section)
            else:  # Contenido
                lines = section.split("\n")
                if len(lines) > 15:  # Secciones largas → resumir
                    # Mantener solo los primeros 3 puntos y añadir resumen
                    summary_lines = [f"- ... ({len(lines)} líneas resumidas)"]
                    new_content.extend(summary_lines)
                else:
                    new_content.append(section)

        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(new_content))

    # ──────── Discovery de skills ────────

    def _discover_skills(self, project_root: str) -> List[Dict]:
        """Descubre las skills/plugins instalados del usuario.

        Busca en:
        1. %APPDATA%/Claude/skills/ (skills de Claude Code)
        2. .claude-plugin/plugin.json (skills del plugin local)
        3. ~/.claude/skills/ (skills globales del usuario)
        4. settings.json mcpServers (MCP servers del usuario)

        Returns:
            Lista de dicts con info de cada skill disponible
        """
        skills = []

        # 1. Skills de Claude Code en %APPDATA%
        claude_skills_dir = os.path.join(
            os.environ.get("APPDATA", ""), "Claude", "skills"
        )
        if os.path.isdir(claude_skills_dir):
            for skill_name in os.listdir(claude_skills_dir):
                skill_path = os.path.join(claude_skills_dir, skill_name)
                if os.path.isdir(skill_path):
                    skill_file = os.path.join(skill_path, "SKILL.md")
                    description = ""
                    if os.path.isfile(skill_file):
                        try:
                            with open(skill_file, "r", encoding="utf-8") as f:
                                content = f.read(500)
                                # Extraer descripción del frontmatter
                                desc_match = re.search(
                                    r"name:\s*(.+)\s*description:\s*(.+)", content
                                )
                                if desc_match:
                                    description = desc_match.group(2).strip()
                        except Exception:
                            pass
                    skills.append({
                        "name": skill_name,
                        "source": "claude_code",
                        "description": description or f"Skill de Claude Code: {skill_name}",
                    })

        # 2. Skills globales del usuario en ~/.claude/skills/
        global_skills_dir = os.path.expanduser("~/.claude/skills")
        if os.path.isdir(global_skills_dir):
            for skill_name in os.listdir(global_skills_dir):
                skill_path = os.path.join(global_skills_dir, skill_name)
                if os.path.isdir(skill_path):
                    skill_file = os.path.join(skill_path, "SKILL.md")
                    description = ""
                    if os.path.isfile(skill_file):
                        try:
                            with open(skill_file, "r", encoding="utf-8") as f:
                                content = f.read(500)
                                desc_match = re.search(
                                    r"name:\s*(.+)\s*description:\s*(.+)", content
                                )
                                if desc_match:
                                    description = desc_match.group(2).strip()
                        except Exception:
                            pass
                    skills.append({
                        "name": skill_name,
                        "source": "global",
                        "description": description or f"Skill global: {skill_name}",
                    })

        # 3. Skills del plugin local (plugin.json)
        plugin_json = os.path.join(project_root, ".claude-plugin", "plugin.json")
        if os.path.isfile(plugin_json):
            try:
                with open(plugin_json, "r", encoding="utf-8") as f:
                    config = json.load(f)
                for skill_dir in config.get("skills", []):
                    skill_path = os.path.join(project_root, skill_dir)
                    if os.path.isdir(skill_path):
                        skill_file = os.path.join(skill_path, "SKILL.md")
                        description = ""
                        if os.path.isfile(skill_file):
                            try:
                                with open(skill_file, "r", encoding="utf-8") as f2:
                                    content = f2.read(500)
                                    desc_match = re.search(
                                        r"name:\s*(.+)\s*description:\s*(.+)", content
                                    )
                                    if desc_match:
                                        description = desc_match.group(2).strip()
                            except Exception:
                                pass
                        skills.append({
                            "name": os.path.basename(skill_dir),
                            "source": "plugin",
                            "description": description or f"Skill del plugin: {os.path.basename(skill_dir)}",
                        })
            except Exception:
                pass

        # 4. MCP servers del usuario (settings.json)
        settings_path = os.path.join(
            os.environ.get("APPDATA", ""), "Claude", "settings.json"
        )
        if os.path.isfile(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                for server_name in settings.get("mcpServers", {}):
                    skills.append({
                        "name": server_name,
                        "source": "mcp_server",
                        "description": f"MCP server: {server_name}",
                    })
            except Exception:
                pass

        # 5. Detectar skills por tipo de proyecto del usuario
        project_type = self._detect_project_type(project_root)
        if project_type:
            for skill_name in PROJECT_SKILL_MAP.get(project_type, []):
                # Solo agregar si no está ya en la lista
                if not any(s["name"] == skill_name for s in skills):
                    skills.append({
                        "name": skill_name,
                        "source": "auto",
                        "description": f"Skill recomendado para tipo de proyecto: {project_type}",
                        "recommended_for": [project_type],
                    })

        return skills

    def _detect_project_type(self, project_root: str) -> Optional[str]:
        """Detecta el tipo de proyecto basado en archivos existentes.

        Returns:
            Tipo del proyecto o None si no se detecta
        """
        # Python project
        if (os.path.isfile(os.path.join(project_root, "pyproject.toml")) or
            os.path.isfile(os.path.join(project_root, "setup.py")) or
            os.path.isdir(os.path.join(project_root, "src"))):
            return "python"

        # JavaScript/TypeScript project
        if (os.path.isfile(os.path.join(project_root, "package.json")) or
            os.path.isfile(os.path.join(project_root, "tsconfig.json"))):
            return "javascript"

        # Full stack (tiene tanto package.json como pyproject.toml/setup.py)
        has_package = os.path.isfile(os.path.join(project_root, "package.json"))
        has_python = os.path.isfile(os.path.join(project_root, "pyproject.toml")) or \
                     os.path.isfile(os.path.join(project_root, "setup.py"))
        if has_package and has_python:
            return "fullstack"

        # Frontend (package.json + frontend dirs)
        if has_package:
            if any(os.path.isdir(os.path.join(project_root, d)) for d in ["src/components", "frontend", "app"]):
                return "frontend"
            return "javascript"  # default JS project

        # Backend Python
        if has_python:
            return "backend"

        return None

    def query_skills(self) -> Dict[str, Any]:
        """Consulta las skills instaladas para este proyecto.

        Returns:
            Skills disponibles con sus relaciones al proyecto
        """
        conn = self.ensure_conn()

        # Skills del usuario
        all_skills = []
        for row in conn.execute("""
            SELECT ps.skill_name, ps.source, ps.description, ps.recommended_for, se.target_node, se.relation
            FROM project_skills ps
            LEFT JOIN skill_edges se ON ps.skill_name = se.source_skill
            ORDER BY ps.source DESC
        """).fetchall():
            all_skills.append({
                "name": row[0],
                "source": row[1],
                "description": row[2] or "",
                "recommended_for": json.loads(row[3]) if row[3] else [],
                "applies_to": row[4] if row[4] and row[4] != "ALL_PROJECT" else None,
                "relation": row[5],
            })

        # Skills recomendadas para el tipo de proyecto actual
        project_type = self._detect_project_type(self.project_root)
        recommended_skills = PROJECT_SKILL_MAP.get(project_type, []) if project_type else []

        return {
            "project_type": project_type or "unknown",
            "recommended_skills": recommended_skills,
            "installed_skills": all_skills,
            "total": len(all_skills),
        }

    # ──────── Phase 4: Blast-radius ────────

    def blast_radius(self, node_name: str) -> Dict[str, Any]:
        """Análisis de blast-radius — qué nodos se afectan si cambia este.

        Traza todos los dependientes directos (quien importa este nodo)
        e indirectos (2do grado) para dar visibilidad del impacto de cambios.
        """
        conn = self.ensure_conn()

        # Dependientes directos (quien importa este node)
        direct_dependents = [row[0] for row in conn.execute(
            "SELECT source FROM edges WHERE target = ? AND relation = 'imports'",
            (node_name,)
        ).fetchall()]

        # Extend: who depends on those dependents (2nd degree)
        if direct_dependents:
            placeholders = ",".join("?" for _ in direct_dependents)
            indirect_dependents = [row[0] for row in conn.execute(
                f"SELECT source FROM edges WHERE target IN ({placeholders}) AND relation = 'imports'",
                direct_dependents
            ).fetchall()]
        else:
            indirect_dependents = []

        # Quien llama a este node
        called_by = [row[0] for row in conn.execute(
            "SELECT source FROM edges WHERE target = ? AND relation = 'calls'",
            (node_name,)
        ).fetchall()]

        return {
            "node": node_name,
            "direct_dependents": direct_dependents,
            "indirect_dependents": indirect_dependents,
            "called_by": called_by,
            "total_affected": len(set(direct_dependents + indirect_dependents)),
        }


# ──────── CLI entry point ────────

def main():
    """CLI para el Project Graph — acceso directo."""
    import argparse

    parser = argparse.ArgumentParser(description="Project Graph — Motor del graph del proyecto")
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # build
    sub = subparsers.add_parser("build", help="Construir/reconstruir el graph completo")
    sub.add_argument("--project-root", default=os.getcwd(), help="Root del proyecto")

    # overview
    sub = subparsers.add_parser("overview", help="Overview del proyecto")
    sub.add_argument("--project-root", default=os.getcwd(), help="Root del proyecto")

    # query_semantic
    sub = subparsers.add_parser("query_semantic", help="Búsqueda semántica (ChromaDB)")
    sub.add_argument("query", help="Consulta de búsqueda")
    sub.add_argument("--n-results", type=int, default=5, help="Número de resultados")

    # query_structural
    sub = subparsers.add_parser("query_structural", help="Consulta estructural (SQLite)")
    sub.add_argument("node", help="Nombre del nodo/archivo")

    # skills
    subparsers.add_parser("skills", help="Skills instaladas y recomendadas para este proyecto")

    # skills_for
    sub = subparsers.add_parser("skills_for", help="Skills que aplican para un archivo o tarea")
    sub.add_argument("target", help="Archivo/nodo o descripción de la tarea")
    sub.add_argument("--file", action="store_true", help="El target es un archivo/nodo, no una tarea")

    # check_compact
    subparsers.add_parser("check_compact", help="Verificar si necesita compactación")

    # compact
    subparsers.add_parser("compact", help="Compactar manualmente el graph")

    # blast_radius (Phase 4)
    sub = subparsers.add_parser("blast_radius", help="Análisis de blast-radius (qué nodos afectan cambios)")
    sub.add_argument("node", help="Nombre del nodo/archivo a analizar")

    # build_graph
    sub = subparsers.add_parser("build_graph", help="Construir graph para archivos específicos o todo el proyecto")
    sub.add_argument("files", nargs="*", help="Archivos a indexar (opcional — si no se pasan, pregunta)")
    sub.add_argument("--project-root", default=os.getcwd(), help="Root del proyecto")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    pm = ProjectGraphManager(args.project_root if hasattr(args, 'project_root') else os.getcwd())

    try:
        if args.command == "build":
            result = pm.build_graph()
            print(f"[claude-retain] Graph construido — nodes={result['nodes_created']}, edges={result['edges_created']}")

        elif args.command == "overview":
            from .graph_query import GraphQueryEngine
            engine = GraphQueryEngine(pm.project_root)
            overview = engine.get_project_overview()
            print(f"[claude-retain] Overview del proyecto:")
            print(f"  Nodos: {overview['total_nodes']}")
            print(f"  Aristas: {overview['total_edges']}")
            project_type = overview.get("project_type", "unknown")
            print(f"  Tipo de proyecto: {project_type}")

            # Relaciónes tipadas (Phase 3)
            if overview.get("top_extends"):
                print("\n  Herencia (extends):")
                for ext in overview["top_extends"][:5]:
                    print(f"    {ext['source']} -> {ext['target']} ({ext['count']} refs)")
            if overview.get("top_defines"):
                print("\n  Definiciones (defines):")
                for defn in overview["top_defines"][:5]:
                    print(f"    {defn['source']} -> {defn['target']} ({defn['count']} refs)")

            # Cruxes (Phase 2)
            if overview.get("files_with_cruxes", 0) > 0:
                print(f"\n  Archivos con cruxes: {overview['files_with_cruxes']}")

            recommended = overview.get("recommended_skills", [])
            installed_count = overview.get("installed_skills_count", 0)
            if recommended:
                print(f"\n  Skills recomendadas para este proyecto:")
                for skill in recommended:
                    print(f"    - {skill}")
            if installed_count > 0:
                print(f"\n  Skills instaladas: {installed_count} total")
            if overview.get("top_imports"):
                print("\n  Top imports:")
                for imp in overview["top_imports"][:5]:
                    print(f"    {imp['node']}: {imp['count']} dependencias")
            if overview.get("needs_compact"):
                print("\n  ⚠️ Necesita compactación")

        elif args.command == "query_semantic":
            results = pm.query_semantic(args.query, args.n_results)
            for r in results:
                if r.get("error"):
                    print(f"  Error: {r['error']}")
                else:
                    print(f"\n  [{r['type']}] similitud={r['similarity']:.4f} — {r['source']}")
                    if r.get("text"):
                        print(f"    {r['text'][:200]}...")

        elif args.command == "query_structural":
            result = pm.query_structural(args.node)
            if result.get("node"):
                print(f"\n  Nodo: {result['node']['name']} ({result['node']['type']})")
                if result['node'].get('summary'):
                    summary_text = result['node']['summary'][:200]
                    try:
                        print(f"  Resumen: {summary_text}")
                    except UnicodeEncodeError:
                        print(f"  Resumen: {summary_text.encode('utf-8', 'replace').decode()}")
            if result.get("imports"):
                print(f"\n  Importa:")
                for imp in result["imports"]:
                    print(f"    -> {imp}")
            if result.get("imported_by"):
                print(f"\n  Importado por:")
                for imp in result["imported_by"]:
                    print(f"    <- {imp}")
            if result.get("defines"):
                print(f"\n  Definiciones:")
                for def_name in result["defines"]:
                    print(f"    -> {def_name}")
            if result.get("extends"):
                print(f"\n  Herencia (extends):")
                for ext in result["extends"]:
                    print(f"    -> {ext}")
            if result.get("calls"):
                print(f"\n  Llamadas cruzadas:")
                for call in result["calls"]:
                    print(f"    -> {call}")

        # ── blast-radius (Phase 4) ──
        elif args.command == "blast_radius":
            result = pm.blast_radius(args.node)
            if result.get("node"):
                print(f"\n  Blast radius para: {result['node']}")
            if result.get("direct_dependents"):
                print(f"\n  Dependientes directos:")
                for dep in result["direct_dependents"]:
                    print(f"    <- {dep}")
            if result.get("indirect_dependents"):
                print(f"\n  Dependientes indirectos:")
                for dep in result["indirect_dependents"]:
                    print(f"    <- {dep}")
            if result.get("called_by"):
                print(f"\n  Llamado por:")
                for caller in result["called_by"]:
                    print(f"    <- {caller}")
            if result.get("total_affected") is not None:
                print(f"\n  Total afectados: {result['total_affected']}")

        elif args.command == "skills":
            from .project_graph import PROJECT_SKILL_MAP
            skills = pm.query_skills()
            project_type = skills.get("project_type", "unknown")
            recommended = skills.get("recommended_skills", [])
            installed = skills.get("installed_skills", [])

            print(f"[claude-retain] Skills para proyecto tipo: {project_type}")
            if recommended:
                print(f"\n  Recomendadas para este proyecto:")
                for skill in recommended:
                    print(f"    - {skill}")
            if installed:
                print(f"\n  Instaladas ({len(installed)} total):")
                by_source = {}
                for s in installed:
                    by_source.setdefault(s["source"], []).append(s)
                for source, src_skills in sorted(by_source.items()):
                    print(f"\n    [{source}]")
                    for s in src_skills:
                        desc = s["description"] or ""
                        applies = f" (aplica a: {s['applies_to']})" if s.get("applies_to") else ""
                        rec = f" [RECOMENDADO]" if s["name"] in recommended else ""
                        print(f"      - {s['name']}: {desc}{applies}{rec}")

        elif args.command == "skills_for":
            from .graph_query import GraphQueryEngine
            engine = GraphQueryEngine(pm.project_root)
            if args.file:
                result = engine.get_applicable_skills(node_name=args.target)
            else:
                result = engine.get_applicable_skills(task_context=args.target)

            project_type = result.get("project_type", "unknown")
            print(f"[claude-retain] Skills para {args.target} (proyecto: {project_type})")

            always = result.get("always_applicable", [])
            if always:
                print(f"\n  Siempre aplicables ({len(always)}):")
                for skill in always:
                    print(f"    - {skill}")

            context_specific = result.get("context_specific", [])
            if context_specific:
                print(f"\n  Por contexto de tarea ({len(context_specific)}):")
                for skill in context_specific:
                    print(f"    - {skill}")

            node_specific = result.get("node_specific", [])
            if node_specific:
                print(f"\n  Por relación directa ({len(node_specific)}):")
                for ns in node_specific:
                    print(f"    - {ns['skill']} (aplica a: {ns['applies_to']})")

            top = result.get("top_recommended", [])
            if top and len(top) > len(always):
                print(f"\n  Top recomendadas ({len(top)}):")
                for skill in top:
                    rec = " [RECOMENDADO]" if skill in always else ""
                    ctx = " [POR TAREA]" if skill in context_specific else ""
                    print(f"    - {skill}{rec}{ctx}")

        elif args.command == "check_compact":
            check = pm.should_compact()
            if check["needs_compact"]:
                print("[claude-retain] ! El graph necesita compactacion")
                for reason in check["reasons"]:
                    print(f"  - {reason['rule']}: {reason['detail']}")
            else:
                print("[claude-retain] OK Graph en buen estado")

        elif args.command == "compact":
            compacted = pm.compact()
            print(f"[claude-retain] Compactación completada:")
            print(f"  Nodos movidos a compacted/: {compacted['stale_nodes_moved']}")
            print(f"  Index resumido: {compacted['index_summarized']}")

        elif args.command == "build_graph":
            if args.files:
                result = pm.incremental_update(args.files, args.project_root)
                print(f"[claude-retain] Graph actualizado para {len(args.files)} archivo(s):")
                for f in args.files:
                    print(f"  ✓ {f} — {result['edges_updated']} aristas")
            else:
                # Mostrar archivos y pedir confirmación
                all_files = pm._scan_files(args.project_root)
                if not all_files:
                    print("[claude-retain] No se encontraron archivos en el proyecto")
                    return

                by_ext = {}
                for fpath, rel_path in all_files:
                    ext = os.path.splitext(fpath)[1].lower()
                    by_ext.setdefault(ext, []).append(rel_path)

                print(f"[claude-retain] Archivos disponibles para indexar ({len(all_files)} total):")
                for ext in sorted(by_ext.keys()):
                    count = len(by_ext[ext])
                    files_list = ", ".join(sorted(by_ext[ext])[:10])
                    if count > 10:
                        files_list += f" (+{count - 10} más)"
                    print(f"\n  {ext}: {count} archivo(s)")
                    print(f"    -> {files_list}")

                db_path = os.path.expanduser("~/.claude-retain/project_graph.db")
                if os.path.exists(db_path):
                    import sqlite3
                    try:
                        conn = sqlite3.connect(db_path)
                        total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                        conn.close()
                        print(f"\n  ⚡ Graph existente: {total_nodes} nodos, {len(all_files)} archivos sin cambios recientes")
                    except Exception:
                        pass

                import sys
                if sys.stdin.isatty():
                    print("\n  Opciones:")
                    print("    [1] Reconstruir TODO el graph (todos los archivos)")
                    print("    [2] Solo archivos seleccionados — ingresa nombres separados por coma")
                    print("    [3] Cancelar")

                    try:
                        choice = input("\n  Elige una opción (1/2/3): ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n  Cancelado")
                        return

                    if choice == "1":
                        print("\n[ m empalace ] Reconstruyendo graph completo...")
                        result = pm.build_graph(args.project_root)
                        print(f"[claude-retain] OK — nodes={result['nodes_created']}, edges={result['edges_created']}")
                    elif choice == "2":
                        try:
                            selected = input("  Archivos (separados por coma, sin espacios): ").strip()
                            if not selected:
                                print("  Sin archivos seleccionados — cancelado")
                                return
                            files_list = [f.strip() for f in selected.split(",")]
                            valid_files = []
                            for rel_path in files_list:
                                abs_path = os.path.join(args.project_root, rel_path)
                                if os.path.isfile(abs_path):
                                    valid_files.append(rel_path)
                                else:
                                    print(f"  ⚠ Archivo no encontrado: {rel_path}")
                            if valid_files:
                                result = pm.incremental_update(valid_files, args.project_root)
                                print(f"[claude-retain] OK — {len(valid_files)} archivo(s) actualizados, {result['edges_updated']} aristas")
                            else:
                                print("  Ningún archivo válido seleccionado — cancelado")
                        except (EOFError, KeyboardInterrupt):
                            print("\n  Cancelado")
                    else:
                        print("  Cancelado")
                else:
                    # No es tty — reconstruir todo automáticamente
                    print("[claude-retain] No hay terminal interactiva — reconstruyendo graph completo...")
                    result = pm.build_graph(args.project_root)
                    print(f"[claude-retain] OK — nodes={result['nodes_created']}, edges={result['edges_created']}")

    except Exception as e:
        print(f"[claude-retain] Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        pm.close()


if __name__ == "__main__":
    main()

