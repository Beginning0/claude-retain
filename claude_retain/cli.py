"""CLI entry point para el plugin claude-retain + LLM Cache."""

import sys
import os
from pathlib import Path

# Agregar directorio del plugin al path
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m claude_retain <comando>")
        print("Comandos: stats, search, layers, graph, llm-cache-stats, llm-cache-clear, build-graph, scope-checker, checkpoints, rewind, branch, replay, delete-checkpoint")
        return

    cmd = sys.argv[1]

    if cmd == "stats":
        show_stats()
    elif cmd == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        search_memories(query)
    elif cmd == "layers":
        show_layers()
    elif cmd == "graph":
        entity = sys.argv[2] if len(sys.argv) > 2 else None
        show_graph(entity)
    elif cmd == "llm-cache-stats":
        show_llm_cache_stats()
    elif cmd == "llm-cache-clear":
        clear_llm_cache()
    elif cmd == "build-graph":
        build_project_graph()
    elif cmd == "scope-checker":
        check_scope()
    elif cmd == "checkpoints":
        list_checkpoints()
    elif cmd == "rewind":
        checkpoint_id = sys.argv[2] if len(sys.argv) > 2 else None
        rewind_memory(checkpoint_id)
    elif cmd == "branch":
        branch_from = None
        branch_name = None
        for i, arg in enumerate(sys.argv[2:], 2):
            if arg.startswith("--from="):
                branch_from = arg.split("=", 1)[1]
            elif arg.startswith("--name="):
                branch_name = arg.split("=", 1)[1]
        create_branch(branch_from, branch_name)
    elif cmd == "replay":
        checkpoint_id = sys.argv[2] if len(sys.argv) > 2 else None
        replay_checkpoint(checkpoint_id)
    elif cmd == "delete-checkpoint":
        checkpoint_id = sys.argv[2] if len(sys.argv) > 2 else None
        delete_checkpoint(checkpoint_id)
    else:
        print(f"Comando desconocido: {cmd}")
        print("Comandos: stats, search, layers, graph, llm-cache-stats, llm-cache-clear, build-graph, scope-checker, checkpoints, rewind, branch, replay, delete-checkpoint")

def show_stats():
    from claude_retain.memory import MemoryManager
    from llm_cache import llm_cache

    mm = MemoryManager()
    if not mm.initialize():
        print("claude-retain no disponible")
        return

    cache = llm_cache()

    stats = mm.stats()
    print(f"\nL0 — Identidad: {stats.get('identity_tokens', 0)} tokens")
    print(f"L1 — Historia esencial: {stats.get('essential_story_tokens', 0)} tokens")
    print(f"L2 — On-Demand: {stats.get('total_drawers', 0)} drawers")
    print(f"L3 — Deep Search: disponible")
    print(f"Grafo de conocimiento: {stats.get('knowledge_graph_triples', 0)} triples")
    print(f"\nLLM Cache:")
    if cache:
        cs = cache.stats()
        mem = cs.get("memory", {})
        pers = cs.get("persistent", {})
        print(f"  En memoria: {mem.get('total_entries', 0)} / {mem.get('max_size', 500)}")
        print(f"  Persistente: {pers.get('total_entries', 0)} entradas, {pers.get('total_hits', 0)} hits")

def search_memories(query):
    from claude_retain.memory import MemoryManager
    mm = MemoryManager()
    if not mm.initialize():
        print("claude-retain no disponible")
        return

    results = mm.search_memories(query)
    if not results:
        print("No se encontraron resultados")
        return

    for i, r in enumerate(results, 1):
        print(f"\n{i}. Sim: {r.get('similarity', 0):.3f} | Wing: {r.get('wing', '?')} | Room: {r.get('room', '?')}")
        text = r.get("text", "")
        if len(text) > 200:
            text = text[:200] + "..."
        print(f"   {text}")

def show_layers():
    from claude_retain.memory import MemoryManager
    mm = MemoryManager()
    if not mm.initialize():
        print("claude-retain no disponible")
        return

    identity = mm.get_identity()
    print(f"\nL0 — Identidad: {'[OK]' if identity else '[NO CONFIG]'} ({len(identity)//4} tokens)")

    try:
        story = mm.get_essential_story()
        print(f"L1 — Historia esencial: {'[OK]' if story else '[NO]'} ({len(story)//4} tokens)")
    except Exception:
        print("L1 — Historia esencial: [ERROR]")

    try:
        from .palace import get_collection
        col = get_collection(palace_path=mm.palace_path, create=False)
        count = col.count() if col else 0
        print(f"L2 — On-Demand: [OK] ({count} drawers)")
    except Exception:
        print("L2 — On-Demand: [ERROR]")

    print("L3 — Deep Search: [OK]")

    if mm.kg:
        try:
            triples = mm.kg.query_entity("ALL")
            print(f"Grafo: {len(triples) if triples else 0} triples")
        except Exception:
            print("Grafo: [ERROR]")

def show_graph(entity=None):
    from claude_retain.memory import MemoryManager
    mm = MemoryManager()
    if not mm.initialize():
        print("claude-retain no disponible")
        return

    if entity:
        triples = mm.get_knowledge_about(entity)
        if not triples:
            print(f"No hay conocimiento sobre '{entity}'")
            return
        for t in triples:
            print(f"{t['subject']} --{t['predicate']}--> {t['object']}")
    else:
        all_triples = mm.kg.query_entity("ALL") if mm.kg else []
        entities = set()
        for t in (all_triples or []):
            entities.add(t.get("subject", ""))
        print(f"Grafo de conocimiento ({len(all_triples) if all_triples else 0} triples):\n")
        for e in sorted(entities):
            if e and e != "ALL":
                count = sum(1 for t in (all_triples or []) if t.get("subject") == e)
                print(f"  • {e} ({count} triples)")

def show_llm_cache_stats():
    from llm_cache import llm_cache
    cache = llm_cache()
    if not cache:
        print("LLM Cache no disponible")
        return

    stats = cache.stats()
    mem = stats.get("memory", {})
    pers = stats.get("persistent", {})
    print(f"\nLLM Cache:")
    print(f"  En memoria: {mem.get('total_entries', 0)} / {mem.get('max_size', 500)}")
    print(f"  Expiradas: {mem.get('expired_entries', 0)}")
    print(f"  Persistente: {pers.get('total_entries', 0)} entradas, {pers.get('total_hits', 0)} hits")

def clear_llm_cache():
    from llm_cache import llm_cache
    cache = llm_cache()
    if not cache:
        print("LLM Cache no disponible")
        return

    cache.clear_expired()
    print("Cache LLM limpiado (entradas expiradas eliminadas)")

def build_project_graph(files=None):
    """Construir/actualizar el graph del proyecto para archivos especificados.

    Si no se pasan archivos, muestra los archivos disponibles y pide confirmación.
    """
    from claude_retain.project_graph import ProjectGraphManager

    project_root = os.getcwd()
    pm = ProjectGraphManager(project_root)

    if files:
        # Construir para archivos específicos
        result = pm.incremental_update(files, project_root)
        print(f"[claude-retain] Graph actualizado para {len(files)} archivo(s):")
        for f in files:
            print(f"  ✓ {f} — {result['edges_updated']} aristas")
    else:
        # Mostrar archivos disponibles y pedir confirmación
        from claude_retain.project_graph import IGNORED_DIRS, IGNORED_EXTENSIONS

        all_files = pm._scan_files(project_root)
        if not all_files:
            print("[claude-retain] No se encontraron archivos en el proyecto")
            return

        # Contar por tipo
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

        # Verificar si el graph ya existe
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

        # Preguntar si reconstruir todo
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
            print("\n[claude-retain] Reconstruyendo graph completo...")
            result = pm.build_graph(project_root)
            print(f"[claude-retain] OK — nodes={result['nodes_created']}, edges={result['edges_created']}")
        elif choice == "2":
            try:
                selected = input("  Archivos (separados por coma, sin espacios): ").strip()
                if not selected:
                    print("  Sin archivos seleccionados — cancelado")
                    return
                files_list = [f.strip() for f in selected.split(",")]
                # Validar que los archivos existen
                valid_files = []
                for rel_path in files_list:
                    abs_path = os.path.join(project_root, rel_path)
                    if os.path.isfile(abs_path):
                        valid_files.append(rel_path)
                    else:
                        print(f"  ⚠ Archivo no encontrado: {rel_path}")
                if valid_files:
                    result = pm.incremental_update(valid_files, project_root)
                    print(f"[claude-retain] OK — {len(valid_files)} archivo(s) actualizados, {result['edges_updated']} aristas")
                else:
                    print("  Ningún archivo válido seleccionado — cancelado")
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelado")
        else:
            print("  Cancelado")

    pm.close()

def check_scope():
    """Ejecutar scope-checker en un archivo JS/TS."""
    import subprocess
    import sys as _sys

    # Determinar script de scope-checker (Python o PowerShell)
    skill_dir = Path(__file__).parent.parent / "skills" / "scope-checker"
    py_script = skill_dir / "scope-checker.py"
    ps1_script = skill_dir / "scope-checker.ps1"

    if not py_script.exists() and not ps1_script.exists():
        print("Error: skill scope-checker no encontrada. Instalar desde G:\\Agentes\\Plugin_agente\\skills\\scope-checker\\", file=_sys.stderr)
        return

    args = ["-f", _sys.argv[2]] if len(_sys.argv) > 2 else []

    # Verificar si es PowerShell
    is_ps = False
    for i, a in enumerate(_sys.argv):
        if a == "--ps":
            is_ps = True
            break

    if is_ps and ps1_script.exists():
        script = str(ps1_script)
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script] + args
    elif py_script.exists():
        script = str(py_script)
        cmd = ["python", script] + args
    else:
        print("Error: No se encontró scope-checker.ps1 ni scope-checker.py", file=_sys.stderr)
        return

    subprocess.run(cmd)


def list_checkpoints():
    """Lista todos los checkpoints de memoria."""
    from claude_retain.checkpoints import CheckpointManager

    ckpt_mgr = CheckpointManager()
    checkpoints = ckpt_mgr.list_checkpoints()

    if not checkpoints:
        print("No hay checkpoints")
        return

    print(f"\nCheckpoints ({len(checkpoints)} total):\n")
    for ckpt in checkpoints:
        label = f" — {ckpt['label']}" if ckpt.get('label') else ""
        is_branch = " [BRANCH]" if ckpt.get('is_branch') else ""
        time_str = ""
        try:
            import datetime
            time_str = datetime.datetime.fromtimestamp(ckpt['created_at']).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        print(f"  {ckpt['checkpoint_id']}{label}{is_branch} — {time_str} ({ckpt.get('drawers_count', '?')} drawers)")

    print()


def rewind_memory(checkpoint_id=None):
    """Restaura la memoria a un checkpoint anterior."""
    from claude_retain.checkpoints import CheckpointManager

    if not checkpoint_id:
        # Mostrar checkpoints disponibles para elegir
        ckpt_mgr = CheckpointManager()
        checkpoints = ckpt_mgr.list_checkpoints()
        print("Checkpoints disponibles:")
        for ckpt in checkpoints[:5]:  # Solo los 5 más recientes
            time_str = ""
            try:
                import datetime
                time_str = datetime.datetime.fromtimestamp(ckpt['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            print(f"  {ckpt['checkpoint_id']} — {time_str}")
        checkpoint_id = input("\nCheckpoint a restaurar (ID): ").strip()
        if not checkpoint_id:
            return

    ckpt_mgr = CheckpointManager()
    result = ckpt_mgr.rewind(checkpoint_id)
    if result:
        print(f"[Checkpoint] Memoria restaurada a {checkpoint_id}")
    else:
        print(f"[Checkpoint] ERROR: no se pudo restaurar a {checkpoint_id}")


def create_branch(branch_from=None, branch_name=None):
    """Crea una bifurcación de memoria."""
    from claude_retain.checkpoints import CheckpointManager

    if not branch_from:
        # Mostrar checkpoints disponibles para elegir
        ckpt_mgr = CheckpointManager()
        checkpoints = ckpt_mgr.list_checkpoints()
        print("Checkpoints disponibles:")
        for ckpt in checkpoints[:5]:  # Solo los 5 más recientes
            time_str = ""
            try:
                import datetime
                time_str = datetime.datetime.fromtimestamp(ckpt['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            print(f"  {ckpt['checkpoint_id']} — {time_str}")
        branch_from = input("\nCheckpoint base (ID): ").strip()
        if not branch_from:
            return

    branch_id = ckpt_mgr.branch(branch_from, branch_name)
    if branch_id:
        print(f"[Checkpoint] Bifurcación creada: {branch_id}")
    else:
        print(f"[Checkpoint] ERROR: no se pudo crear bifurcación desde {branch_from}")


def replay_checkpoint(checkpoint_id=None):
    """Lista los recuerdos de un checkpoint (sin restaurar)."""
    from claude_retain.checkpoints import CheckpointManager

    if not checkpoint_id:
        # Mostrar checkpoints disponibles para elegir
        ckpt_mgr = CheckpointManager()
        checkpoints = ckpt_mgr.list_checkpoints()
        print("Checkpoints disponibles:")
        for ckpt in checkpoints[:5]:  # Solo los 5 más recientes
            time_str = ""
            try:
                import datetime
                time_str = datetime.datetime.fromtimestamp(ckpt['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            print(f"  {ckpt['checkpoint_id']} — {time_str}")
        checkpoint_id = input("\nCheckpoint a replay (ID): ").strip()
        if not checkpoint_id:
            return

    ckpt_mgr = CheckpointManager()
    result = ckpt_mgr.replay(checkpoint_id)
    if "error" in result:
        print(f"[Checkpoint] ERROR: {result['error']}")
        return

    print(f"\nReplay de {checkpoint_id}:\n")
    print(f"  Checkpoint: {result['checkpoint_id']}")
    try:
        import datetime
        time_str = datetime.datetime.fromtimestamp(result['created_at']).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  Fecha: {time_str}")
    except Exception:
        pass
    print(f"  Label: {result.get('label', 'N/A')}")
    print(f"  Drawers: {result['drawers_count']}")
    if result.get('is_branch'):
        print(f"  Base: {result.get('base_checkpoint')}")
    print()


def delete_checkpoint(checkpoint_id=None):
    """Elimina un checkpoint de la memoria."""
    from claude_retain.checkpoints import CheckpointManager

    if not checkpoint_id:
        # Mostrar checkpoints disponibles para elegir
        ckpt_mgr = CheckpointManager()
        checkpoints = ckpt_mgr.list_checkpoints()
        print("Checkpoints disponibles (para eliminar):")
        for ckpt in checkpoints[:5]:  # Solo los 5 más recientes
            time_str = ""
            try:
                import datetime
                time_str = datetime.datetime.fromtimestamp(ckpt['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            print(f"  {ckpt['checkpoint_id']} — {time_str}")
        checkpoint_id = input("\nCheckpoint a eliminar (ID): ").strip()
        if not checkpoint_id:
            return

    ckpt_mgr = CheckpointManager()
    result = ckpt_mgr.delete_checkpoint(checkpoint_id)
    if result:
        print(f"[Checkpoint] Eliminado: {checkpoint_id}")
    else:
        print(f"[Checkpoint] ERROR: no se pudo eliminar {checkpoint_id}")


if __name__ == "__main__":
    main()

