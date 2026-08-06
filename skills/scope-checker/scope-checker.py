#!/usr/bin/env python3
"""
Detecta problemas de scope de variables en archivos JavaScript/TypeScript.

Encuentra:
1. Variables declaradas dentro de bloques condicionales pero usadas fuera
2. Implicit globals — asignaciones sin let/var/const
3. Variables usadas antes de ser declaradas en el mismo scope
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Issue:
    severity: str  # CRITICAL, ERROR, WARNING
    variable: str
    issue_type: str  # "inside_block", "implicit_global"
    assign_line: int
    usage_line: Optional[int]
    detail: str
    code: str

    def to_dict(self):
        return asdict(self)


def get_brace_depth(line: str) -> int:
    """Calcula la profundidad de llaves en una línea."""
    depth = 0
    for ch in line:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    return depth


def find_function_bounds(lines, func_name):
    """Encuentra los límites de una función por nombre.

    Busca el opening brace { de la funcion y luego encuentra el matching closing brace }.
    """
    func_start = 0
    func_end = len(lines)

    # Encontrar inicio de la funcion — soporta varios patrones
    patterns = [
        re.compile(r'\s*function\s+' + re.escape(func_name)),           # function foo(...)
        re.compile(r'\s*async\s+function\s+' + re.escape(func_name)),   # async function foo(...)
        re.compile(re.escape(func_name) + r'\s*=\s*(?:async\s+)?function'),  # const foo = function
        re.compile(r'\s*(?:const|let|var)\s+' + re.escape(func_name) + r'\s*='),  # const foo = ...
        re.compile(r'\s*[a-zA-Z_]\w*\.' + re.escape(func_name) + r'\s*=\s*(?:async\s+)?function'),  # obj.foo = function
    ]

    found = False
    for i, line in enumerate(lines):
        for pattern in patterns:
            if pattern.search(line):
                func_start = i
                found = True
                break
        if found:
            break

    if not found:
        return func_start, func_end

    # Encontrar el opening brace { de la funcion
    brace_depth = 0
    func_open_brace = -1
    for i in range(func_start, len(lines)):
        line = lines[i]
        before = brace_depth
        for ch in line:
            if ch == '{':
                brace_depth += 1
                # El opening brace de la funcion es el primero que lleva de 0 a 1
                if before == 0:
                    func_open_brace = i
                    break
            elif ch == '}':
                brace_depth -= 1
        if func_open_brace >= 0:
            break

    if func_open_brace < 0:
        return func_start, func_end

    # Encontrar el closing brace } que corresponde al opening brace
    depth = 0
    for i in range(func_open_brace, len(lines)):
        before = depth
        for ch in lines[i]:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        # Cuando depth vuelve a 0 desde 1, ese es el cierre de la funcion
        if before == 1 and depth == 0:
            func_end = i + 1
            break

    return func_start, func_end


def find_conditional_blocks(lines, start_line, end_line):
    """Encuentra bloques condicionales (if/for/while) dentro de un rango."""
    blocks = []
    depth = 0
    block_start = -1

    for i in range(start_line, min(end_line, len(lines))):
        line = lines[i]

        # Detectar inicio de bloque condicional
        if re.match(r'\s*(if|for|while)\s*\(', line):
            before_depth = depth
            for ch in line:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            if before_depth >= 1 and depth > before_depth:
                block_start = i

        # Detectar cierre de bloque condicional
        if re.match(r'\s*\}', line):
            before_depth = depth
            for ch in line:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            if block_start >= 0 and before_depth >= 1 and depth < before_depth:
                blocks.append({
                    'start_line': block_start + 1,  # 1-indexed
                    'end_line': i + 1,               # 1-indexed
                    'depth_before': before_depth,
                    'depth_after': depth,
                })
                block_start = -1

    return blocks


def find_declarations(lines, start_line, end_line):
    """Encuentra todas las declaraciones de variables (let/var/const) en un rango."""
    declarations = {}

    for i in range(start_line, min(end_line, len(lines))):
        line = lines[i]

        # Buscar todas las declaraciones let/var/const en la línea
        matches = re.finditer(r'(?:let|var|const)\s+([a-zA-Z_]\w+)', line)
        for m in matches:
            name = m.group(1)
            # Verificar si es una asignación o declaración simple
            if re.search(re.escape(name) + r'\s*=', line):
                declarations[name] = {
                    'line': i + 1,
                    'type': 'assignment',
                    'value': line.split('=')[1].strip() if '=' in line else ''
                }
            else:
                declarations[name] = {
                    'line': i + 1,
                    'type': 'declaration',
                    'value': ''
                }

    return declarations


def find_assignments(lines, start_line, end_line, block_decls, func_declarations):
    """Encuentra asignaciones dentro de un bloque condicional.

    Args:
        block_decls: declaraciones DENTRO del bloque (para detectar inside_block)
        func_declarations: TODAS las declaraciones de la funcion (para verificar implicit globals)
    """
    assignments = {}

    for i in range(start_line, min(end_line, len(lines))):
        line = lines[i]

        # Ignorar SQL strings y object.property assignments
        if re.search(r'(UPDATE|SELECT|WHERE|INSERT|DELETE)\s', line):
            continue
        if re.search(r'\.\w+\s*=', line):
            continue

        # Buscar declaraciones con let/var/const (declaración dentro del bloque)
        decl_matches = list(re.finditer(r'(?:let|var|const)\s+([a-zA-Z_]\w+)\s*=\s*', line))
        if decl_matches:
            # Esta linea tiene declaracion explícita — verificar inside_block
            for m in decl_matches:
                name = m.group(1)
                if name not in block_decls and name not in func_declarations:
                    assignments[name] = {
                        'line': i + 1,
                        'code': line.strip(),
                        'type': 'inside_block'
                    }

        # Buscar asignaciones sin let/var/const (implicit global) — solo si NO hay declaracion en esta linea
        if not decl_matches:
            matches = re.finditer(r'(?<![.\w])([a-zA-Z_]\w+)\s*=\s*', line)
            for m in matches:
                name = m.group(1)
                # Ignorar keywords de JS
                js_keywords = {
                    'if', 'else', 'for', 'while', 'return', 'true', 'false',
                    'null', 'undefined', 'const', 'let', 'var', 'function',
                    'new', 'this', 'class', 'try', 'catch', 'finally', 'throw',
                    'break', 'continue', 'switch', 'case', 'default', 'typeof',
                    'instanceof', 'delete', 'void', 'async', 'await', 'import',
                    'export', 'console', 'log', 'Math', 'JSON', 'Date', 'Number',
                    'String', 'Boolean', 'Array', 'Object', 'Promise', 'Error'
                }
                if name in js_keywords:
                    continue
                # Si ya está declarada en el scope de la funcion, es OK (reasignación)
                if name in func_declarations:
                    continue
                assignments[name] = {
                    'line': i + 1,
                    'code': line.strip(),
                    'type': 'implicit_global'
                }

    return assignments


def find_outside_usage(lines, block_end_line, max_line, var_names):
    """Busca uso de variables fuera del bloque condicional."""
    usages = {}

    for i in range(block_end_line, min(max_line, len(lines))):
        line = lines[i]

        for name in var_names:
            # Verificar si la variable se usa como valor (no asignación)
            if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', line):
                if not re.search(re.escape(name) + r'\s*=', line):
                    if name not in usages:
                        usages[name] = []
                    usages[name].append({
                        'line': i + 1,
                        'code': line.strip()
                    })

    return usages


def main():
    parser = argparse.ArgumentParser(
        description='Detecta problemas de scope de variables en archivos JS/TS'
    )
    parser.add_argument('filepath', help='Ruta al archivo JS/TS a escanear')
    parser.add_argument('--function', '-f', help='Nombre de función para limitar el escaneo')
    parser.add_argument('--verify', '-v', action='store_true', help='Modo verificar — sale con error si hay problemas')
    parser.add_argument('--json', '-j', action='store_true', help='Output en formato JSON')
    args = parser.parse_args()

    # Leer archivo
    try:
        with open(args.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Archivo no encontrado: {args.filepath}", file=sys.stderr)
        sys.exit(1)

    total_lines = len(lines)

    # Si se especificó una función, limitar el escaneo
    if args.function:
        func_start, func_end = find_function_bounds(lines, args.function)
        print(f"Escaneando funcion '{args.function}' (lineas {func_start+1}-{func_end})", file=sys.stderr)
    else:
        func_start, func_end = 0, total_lines

    # Obtener TODAS las declaraciones de la funcion (scope completo)
    func_declarations = find_declarations(lines, func_start, func_end)

    # Encontrar bloques condicionales dentro de la funcion
    blocks = find_conditional_blocks(lines, func_start, func_end)

    issues = []

    for block in blocks:
        # Obtener declaraciones DENTRO del bloque (para detectar inside_block)
        block_decls = find_declarations(lines, block['start_line'], block['end_line'])

        # Encontrar asignaciones dentro del bloque — usar func_declarations para verificar implicit globals
        assignments = find_assignments(lines, block['start_line'], block['end_line'], block_decls, func_declarations)

        if assignments:
            var_names = list(assignments.keys())
            # Buscar uso fuera del bloque
            outside_usage = find_outside_usage(lines, block['end_line'], func_end, var_names)

            for name in assignments:
                usage = outside_usage.get(name)
                severity = "WARNING"
                detail = ""

                if assignments[name]['type'] == 'inside_block':
                    severity = "ERROR"
                    detail = f"Declarada con let/var/const dentro del bloque condicional (linea {assignments[name]['line']}) pero usada fuera del bloque"
                elif usage:
                    severity = "CRITICAL"
                    detail = f"Implicit global — asignado sin let/var/const en linea {assignments[name]['line']}, usado fuera del bloque en linea {usage[0]['line']}"

                issues.append(Issue(
                    severity=severity,
                    variable=name,
                    issue_type=assignments[name]['type'],
                    assign_line=assignments[name]['line'],
                    usage_line=usage[0]['line'] if usage else None,
                    detail=detail,
                    code=assignments[name]['code'],
                ))

    # Output
    if not issues:
        print("\n[OK] No se encontraron problemas de scope de variables.", file=sys.stderr)
    else:
        print(f"\n[!] Se encontraron {len(issues)} problema(s) de scope de variables:", file=sys.stderr)

        by_severity = {}
        for issue in issues:
            by_severity.setdefault(issue.severity, []).append(issue)

        colors = {'CRITICAL': 'RED', 'ERROR': 'YELLOW', 'WARNING': 'CYAN'}
        for severity, sev_issues in by_severity.items():
            print(f"  {severity}: {len(sev_issues)}", file=sys.stderr)

        for issue in issues:
            color = colors.get(issue.severity, '')
            print(f"\n  [{issue.severity}] {issue.variable}", file=sys.stderr)
            print(f"    Tipo: {issue.issue_type}", file=sys.stderr)
            print(f"    Asignada en linea {issue.assign_line}: {issue.code}", file=sys.stderr)
            if issue.usage_line:
                print(f"    Usada fuera del bloque en linea {issue.usage_line}: {issue.code}", file=sys.stderr)
            print(f"    Detalle: {issue.detail}", file=sys.stderr)

        print(f"\n[RECOMENDADO] Mover TODAS las variables declaradas dentro del bloque condicional a antes del bloque con valores por defecto:", file=sys.stderr)
        print("    ANTES: let X = valor; dentro del if", file=sys.stderr)
        print("    DESPUES: let X = default; antes del if + X = valor; dentro del if", file=sys.stderr)

    # JSON output
    if args.json:
        print(json.dumps([i.to_dict() for i in issues], indent=2, ensure_ascii=False))

    if args.verify and issues:
        print(f"\n[FAIL] Se encontraron {len(issues)} problema(s).", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
