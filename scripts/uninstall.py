#!/usr/bin/env python3
"""Desinstala claude-retain de Claude Code.

Solo desinstala el paquete Python con pip y limpia configuracion residual.
No toca hooks ni MCP — esos los maneja el sistema de plugins de Claude Code.
"""

import json
import subprocess
import sys
from pathlib import Path


def get_user_claude_dir():
    """Obtener el directorio .claude del usuario."""
    return Path.home() / ".claude"


def uninstall_pip():
    """Desinstalar el paquete Python con pip."""
    print("  Desinstalando paquete Python con pip...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "claude-retain-claude-plugin"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        # Puede fallar si no esta instalado por pip
        print(f"  Aviso: pip uninstall falló (quizás no estaba instalado con pip)")
        return False
    print("  Paquete desinstalado correctamente.")
    return True


def remove_skills(claude_dir):
    """Eliminar archivos .skill de claude-retain que quedaron de instalaciones manuales."""
    skills_dir = claude_dir / "skills"
    removed = []

    if not skills_dir.exists():
        return removed

    # Eliminar todos los archivos .skill de claude-retain y orquestación
    patterns = ["claude-retain-*.skill", "*-orchestration.skill"]
    for pattern in patterns:
        for skill_file in list(skills_dir.glob(pattern)):
            try:
                skill_file.unlink()
                removed.append(skill_file.name)
            except Exception as e:
                print(f"  ERROR al eliminar {skill_file.name}: {e}")

    return removed


def disable_plugin(user_claude_dir):
    """Remover claude-retain de enabledPlugins en settings.json."""
    settings_path = user_claude_dir / "settings.json"
    if not settings_path.exists():
        return False, False

    with open(settings_path, 'r', encoding='utf-8') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            return False, False

    modified = False
    # Remover claude-retain@claude-retain-local (formato correcto)
    if "enabledPlugins" in config:
        key = "claude-retain@claude-retain-local"
        if key in config["enabledPlugins"]:
            del config["enabledPlugins"][key]
            modified = True
        # También remover formato antiguo por compatibilidad
        if "claude-retain" in config["enabledPlugins"] and "claude-retain@claude-retain-local" not in config["enabledPlugins"]:
            del config["enabledPlugins"]["claude-retain"]
            modified = True
        # Si enabledPlugins queda vacio, eliminarlo
        if config.get("enabledPlugins") == {}:
            del config["enabledPlugins"]

    if modified:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    return modified, True


def remove_marketplace(user_claude_dir):
    """Remover el marketplace de claude-retain de extraKnownMarketplaces."""
    settings_path = user_claude_dir / "settings.json"
    if not settings_path.exists():
        return False

    with open(settings_path, 'r', encoding='utf-8') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            return False

    modified = False
    if "extraKnownMarketplaces" in config and "claude-retain" in config["extraKnownMarketplaces"]:
        del config["extraKnownMarketplaces"]["claude-retain"]
        modified = True
        # Si extraKnownMarketplaces queda vacio, eliminarlo
        if config.get("extraKnownMarketplaces") == {}:
            del config["extraKnownMarketplaces"]

    if modified:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    return modified


def main():
    print("Desinstalando claude-retain de Claude Code...")
    print()

    user_claude_dir = get_user_claude_dir()
    claude_dir = Path.home() / "AppData" / "Roaming" / "Claude" if Path.home().parts[-1].lower() == "shado terro" else None

    # Intentar obtener directorio de Claude
    import os
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        claude_dir = Path(appdata) / "Claude"

    # Desinstalar pip package
    pip_uninstalled = uninstall_pip()

    # Limpiar skills huérfanos
    if claude_dir and claude_dir.exists():
        skills_removed = remove_skills(claude_dir)
        if skills_removed:
            print(f"\n  Skills huérfanas eliminadas ({len(skills_removed)}):")
            for skill in skills_removed:
                print(f"    - {skill}")

    # Deshabilitar plugin
    plugin_disabled, _ = disable_plugin(user_claude_dir)
    if plugin_disabled:
        print("\n  Plugin deshabilitado (removido de enabledPlugins)")

    # Remover marketplace
    mp_removed = remove_marketplace(user_claude_dir)
    if mp_removed:
        print("  Marketplace de claude-retain removido de extraKnownMarketplaces")

    print()
    print("claude-retain desinstalado correctamente.")
    print("Reinicia Claude Code para que los cambios surtan efecto.")

if __name__ == "__main__":
    main()

