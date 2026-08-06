#!/usr/bin/env python3
"""Instalador de claude-retain para Claude Code.

Instala el plugin usando el sistema de marketplaces de Claude Code.
No toca settings.json — eso lo hace Claude Code automaticamente cuando
el plugin esta registrado como marketplace y habilitado.

Uso:
    python scripts/install.py

Requisitos:
    - Claude Code con soporte para marketplaces locales
    - El plugin debe estar registrado en extraKnownMarketplaces
      de settings.json como marketplace local antes de instalar.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def get_claude_dir():
    """Obtener el directorio de datos de Claude Code."""
    import platform
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return Path.home() / "AppData" / "Roaming" / "Claude"
        return Path(appdata) / "Claude"
    else:
        return Path.home() / ".claude"


def check_python():
    """Verificar que python o python3 este disponible."""
    import shutil
    if shutil.which("python3") or shutil.which("python"):
        return True
    print("  ERROR: No se encontro 'python' o 'python3' en PATH.")
    print("  Instala Python y asegurate de que este en el PATH.")
    sys.exit(1)


def check_python_version():
    """Verificar version minima de Python (3.9+)."""
    import platform as _platform
    ver = _platform.python_version_tuple()
    major, minor = int(ver[0]), int(ver[1])
    if major < 3 or (major == 3 and minor < 9):
        print(f"  ERROR: Se requiere Python 3.9+ (tiene {major}.{minor}).")
        sys.exit(1)
    return True


def ensure_skill_bundle(plugin_dir):
    """Correr package_skills.py si .skill-bundle esta vacio o no existe."""
    skill_bundle_dir = plugin_dir / ".skill-bundle"

    if skill_bundle_dir.exists():
        skill_files = list(skill_bundle_dir.glob("*.skill"))
        if skill_files:
            return True  # Ya tiene skills

    package_script = plugin_dir / "scripts" / "package_skills.py"
    if not package_script.exists():
        print("  ERROR: package_skills.py no encontrado. No se pueden empaquetar las skills.")
        return False

    print("  Empaquetando skills...")
    result = subprocess.run(
        [sys.executable, str(package_script)],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ERROR al empaquetar skills: {result.stderr}")
        return False
    print("  Skills empaquetadas correctamente.")
    return True


def check_marketplace_registered(user_claude_dir):
    """Verificar que el marketplace de claude-retain este registrado en extraKnownMarketplaces."""
    settings_path = user_claude_dir / "settings.json"

    if not settings_path.exists():
        print("  ERROR: No se encontro settings.json.")
        print("\n  Registra el marketplace antes de instalar:")
        print('  1. Abre %USERPROFILE%\\.claude\\settings.json')
        print('  2. Agrega en extraKnownMarketplaces:')
        print()
        print('    "claude-retain": {')
        print('      "source": {')
        print('        "source": "directory",')
        print('        "path": "G:\\\\Agentes\\\\Plugin_agente"')
        print('      }')
        print('    }')
        print()
        print("  3. Habilita el plugin con: \"claude-retain@claude-retain-local\": true")
        sys.exit(1)

    with open(settings_path, 'r', encoding='utf-8') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            print("  ERROR: settings.json corrupto.")
            sys.exit(1)

    # Verificar marketplace
    marketplaces = config.get("extraKnownMarketplaces", {})
    has_claude-retain_mp = "claude-retain" in marketplaces

    # Verificar plugin habilitado
    enabled = config.get("enabledPlugins", {})
    has_claude-retain_enabled = any(
        k.startswith("claude-retain@") for k in enabled
    )

    if not has_claude-retain_mp:
        print("  ERROR: Marketplace de claude-retain no registrado.")
        print("\n  Agrega esto en extraKnownMarketplaces de settings.json:")
        print()
        print('    "claude-retain": {')
        print('      "source": {')
        print('        "source": "directory",')
        print('        "path": "G:\\\\Agentes\\\\Plugin_agente"')
        print('      }')
        print('    }')
        sys.exit(1)

    if not has_claude-retain_enabled:
        print("  ERROR: Plugin de claude-retain no habilitado.")
        print("\n  Agrega esto en enabledPlugins de settings.json:")
        print()
        print('    "claude-retain@claude-retain-local": true')
        sys.exit(1)

    return True


def install_pip(plugin_dir):
    """Instalar el paquete Python con pip."""
    pyproject = plugin_dir / "pyproject.toml"
    if not pyproject.exists():
        print("  ERROR: pyproject.toml no encontrado. No se puede instalar via pip.")
        return False

    print("  Instalando paquete Python con pip...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(plugin_dir)],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ERROR al instalar con pip: {result.stderr}")
        return False
    print("  Paquete instalado correctamente.")
    return True


def main():
    plugin_dir = Path(__file__).parent.parent
    claude_dir = get_claude_dir()

    # Verificar Python disponible y version
    check_python()
    check_python_version()

    # Verificar que el marketplace este registrado
    user_claude_dir = Path.home() / ".claude"
    check_marketplace_registered(user_claude_dir)

    # Empaquetar skills si no existen
    if not ensure_skill_bundle(plugin_dir):
        sys.exit(1)

    # Crear directorio Claude si no existe
    if not claude_dir.exists():
        print(f"  Creando directorio: {claude_dir}")
        claude_dir.mkdir(parents=True, exist_ok=True)

    # Instalar con pip (editable)
    install_pip(plugin_dir)

    print()
    print("claude-retain instalado correctamente.")
    print()
    print("El plugin se cargara automaticamente desde el marketplace local")
    print("cuando reinicies Claude Code. No es necesario configurar nada mas.")
    print()
    print("Para verificar que esta instalado:")
    print("  - Ejecuta: /plugin list")
    print("  - Deberia aparecer claude-retain en la lista de plugins habilitados")
    print()
    print("Si el plugin no aparece, reinicia Claude Code.")

if __name__ == "__main__":
    main()

