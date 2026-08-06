#!/usr/bin/env python3
"""Empaqueta todas las skills de claude-retain como archivos .skill."""

import sys
import zipfile
import fnmatch
from pathlib import Path

EXCLUDE_DIRS = {"__pycache__", "node_modules"}
EXCLUDE_GLOBS = {"*.pyc"}
EXCLUDE_FILES = {".DS_Store"}

def should_exclude(rel_path):
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    name = rel_path.name
    if name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_GLOBS)

def package_skill(skill_path, output_dir):
    skill_path = Path(skill_path).resolve()
    if not skill_path.exists():
        print(f"  ERROR: Skill no encontrado: {skill_path}")
        return None

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        print(f"  ERROR: SKILL.md no encontrado en {skill_path}")
        return None

    skill_name = skill_path.name
    output_path = Path(output_dir).resolve() / f"{skill_name}.skill"

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in skill_path.rglob('*'):
            if not file_path.is_file():
                continue
            arcname = file_path.relative_to(skill_path.parent)
            if should_exclude(arcname):
                continue
            zipf.write(file_path, arcname)

    print(f"  OK: {skill_name}.skill -> {output_path}")
    return output_path

def main():
    plugin_dir = Path(__file__).parent.parent
    skills_dir = plugin_dir / "skills"
    output_dir = plugin_dir / ".skill-bundle"
    output_dir.mkdir(exist_ok=True)

    skill_dirs = sorted(skills_dir.iterdir()) if skills_dir.exists() else []
    if not skill_dirs:
        print(f"ERROR: No se encontraron skills en {skills_dir}")
        sys.exit(1)

    print(f"Empaquetando {len(skill_dirs)} skills...")
    for skill_dir in skill_dirs:
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            package_skill(skill_dir, output_dir)

if __name__ == "__main__":
    main()

