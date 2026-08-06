#!/usr/bin/env python3
"""Pruebas básicas del instalador de claude-retain."""

import json
import os
import pathlib
import sys

# Agregar directorio del plugin al path para importar el instalador
PLUGIN_DIR = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))


def test_skill_bundle_exists():
    """Verificar que el .skill-bundle tiene los archivos esperados."""
    bundle_dir = PLUGIN_DIR / ".skill-bundle"
    assert bundle_dir.exists(), f".skill-bundle no existe en {bundle_dir}"

    expected_skills = [
        "claude-retain-stats.skill",
        "claude-retain-search.skill",
        "claude-retain-layers.skill",
        "claude-retain-graph.skill",
        "claude-retain-llm-cache-stats.skill",
        "claude-retain-llm-cache-clear.skill",
    ]
    for skill in expected_skills:
        skill_file = bundle_dir / skill
        assert skill_file.exists(), f"Falta {skill} en .skill-bundle"


def test_skills_have_skill_md():
    """Verificar que cada skill tenga SKILL.md."""
    skills_dir = PLUGIN_DIR / "skills"
    assert skills_dir.exists(), f"Directorio de skills no existe en {skills_dir}"

    for skill in skills_dir.iterdir():
        if skill.is_dir():
            skill_md = skill / "SKILL.md"
            assert skill_md.exists(), f"{skill.name} no tiene SKILL.md"


def test_hooks_exist():
    """Verificar que los hooks existan (version PowerShell en Windows)."""
    import platform
    hook_ext = ".ps1" if platform.system() == "Windows" else ""

    expected_hooks = [
        "claude-retain-post-tool-use",
        "claude-retain-session-start",
        "claude-retain-stop",
    ]
    for hook in expected_hooks:
        hook_file = PLUGIN_DIR / "bin" / f"{hook}{hook_ext}"
        assert hook_file.exists(), f"Falta hook {hook}{hook_ext}"


def test_mcp_server_exists():
    """Verificar que el MCP server wrapper exista."""
    import platform
    mcp_ext = ".ps1" if platform.system() == "Windows" else ""

    mcp_file = PLUGIN_DIR / "bin" / f"claude-retain-mcp-server{mcp_ext}"
    assert mcp_file.exists(), f"Falta MCP server {mcp_file}"


def test_plugin_manifest():
    """Verificar que el manifest del plugin tenga la estructura correcta."""
    manifest = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
    assert manifest.exists(), f"Manifest no existe en {manifest}"

    with open(manifest, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "name" in data, "Manifest sin 'name'"
    assert "skills" in data, "Manifest sin 'skills'"
    assert isinstance(data["skills"], list), "Skills no es una lista"
    assert len(data["skills"]) > 0, "Manifest sin skills"


def test_pyproject_has_entry_point():
    """Verificar que pyproject.toml tenga el entry point."""
    pyproject = PLUGIN_DIR / "pyproject.toml"
    assert pyproject.exists(), "pyproject.toml no existe"

    content = pyproject.read_text(encoding="utf-8")
    assert "claude_retain.cli:main" in content, "Entry point no encontrado en pyproject.toml"


def test_no_root_init_conflict():
    """Verificar que no haya __init__.py conflictivo en la raíz."""
    root_init = PLUGIN_DIR / "__init__.py"
    assert not root_init.exists(), (
        "__init__.py en la raíz puede causar conflictos de import - "
        "se recomienda eliminarlo ya que los subpackages son independientes."
    )


def test_project_graph_has_main():
    """Verificar que project_graph.py tenga un main() para CLI."""
    pg_file = PLUGIN_DIR / "claude_retain" / "project_graph.py"
    content = pg_file.read_text(encoding="utf-8")
    assert "def main()" in content, "project_graph.py necesita una función main() para el CLI"


def test_install_hooks_has_matcher():
    """Verificar que install.py tenga el matcher en PostToolUse."""
    install_file = PLUGIN_DIR / "scripts" / "install.py"
    content = install_file.read_text(encoding="utf-8")
    assert '"matcher": "Write|Edit"' in content, (
        "install.py debe tener un matcher 'Write|Edit' para PostToolUse"
    )


def test_pyproject_has_packages_find():
    """Verificar que pyproject.toml tenga tool.setuptools.packages.find."""
    pyproject = PLUGIN_DIR / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    assert "tool.setuptools.packages.find" in content, (
        "pyproject.toml necesita [tool.setuptools.packages.find] para incluir subpackages"
    )


if __name__ == "__main__":
    tests = [
        ("Skill bundle existe", test_skill_bundle_exists),
        ("Skills tienen SKILL.md", test_skills_have_skill_md),
        ("Hooks existen", test_hooks_exist),
        ("MCP server existe", test_mcp_server_exists),
        ("Manifest de plugin válido", test_plugin_manifest),
        ("Entry point en pyproject.toml", test_pyproject_has_entry_point),
        ("Sin __init__.py conflictivo", test_no_root_init_conflict),
        ("project_graph.py tiene main()", test_project_graph_has_main),
        ("install.py tiene matcher PostToolUse", test_install_hooks_has_matcher),
        ("pyproject.toml tiene packages.find", test_pyproject_has_packages_find),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  OK: {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {name} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {name} — {e}")
            failed += 1

    print()
    print(f"Resultados: {passed} OK, {failed} FAIL")
    sys.exit(0 if failed == 0 else 1)


