---
name: scope-checker
description: Detectar problemas de scope de variables — declaraciones dentro de bloques condicionales pero uso fuera, variables implícitas globales, y asignaciones sin declaración previa. Se activa ANTES de modificar código o cuando hay errores "is not defined".
allowed-tools: [Bash]
---

## Regla de oro: Antes de modificar código, verificar scope de todas las variables

Cuando se va a modificar una función que usa variables externas al bloque condicional, **siempre** ejecutar scope-checker. Cuando aparece un error `X is not defined`, usar scope-checker ANTES de intentar cualquier fix.

## Paso 1 — Detectar el problema de scope

Cuando un error dice `X is not defined`, verificar si la variable se declara dentro de un bloque condicional pero se usa fuera:

```bash
# Escanear el archivo para variables sin declarar en el contexto actual
!claude-retain scope-checker "bot.js" --function analyzeStrategyLoop
```

## Paso 2 — Analizar el bloque condicional

Si el error está relacionado con un bloque `if`, verificar si la variable se declara dentro del bloque:

```bash
# Verificar profundidad de llaves para identificar límites de bloques
node -e "
let depth = 0;
const fs = require('fs');
const lines = fs.readFileSync('bot.js', 'utf-8').split('\n');
for (let i = inicioLinea; i < finLinea; i++) {
    const line = lines[i];
    let before = depth;
    for (const ch of line) {
        if (ch === '{') depth++;
        else if (ch === '}') depth--;
    }
    if (before >= 1 && depth < before) {
        console.log('CERRADURA: LÍNEA ' + (i+1) + ' (d=' + before + '→' + depth + '): ' + line.trim());
    }
}
"
```

## Paso 3 — Identificar TODAS las variables con el mismo problema

**NO arreglar solo la variable del error.** Buscar TODAS las variables declaradas dentro del bloque pero usadas fuera:

```bash
# Encontrar todas las variables no declaradas asignadas en el bloque if
node -e "
const fs = require('fs');
const lines = fs.readFileSync('bot.js', 'utf-8').split('\n');

// Variables declaradas antes del bloque if
const declaredVars = new Set();
for (let i = 0; i < inicioLinea; i++) {
    const declMatches = lines[i].matchAll(/(?:let|var|const)\s+([a-zA-Z_]\w+)/g);
    for (const m of declMatches) declaredVars.add(m[1]);
}

// Variables asignadas dentro del bloque pero no declaradas
for (let i = inicioLinea; i < finLinea; i++) {
    const line = lines[i];
    // Solo variables con let/var/const — NO object.property = value
    if (!line.match(/^[^}].*?\.([a-zA-Z_]\w+)\s*=/) && line.includes('=')) {
        const assignmentMatches = line.matchAll(/(?:let|var|const)\s+([a-zA-Z_]\w+)/g);
        for (const m of assignmentMatches) {
            if (!declaredVars.has(m[1])) {
                console.log('NO DECLARADA: LÍNEA ' + (i+1) + ': ' + line.trim());
            }
        }
    }
}

// Variables asignadas pero SIN let/var/const (implicit global)
for (let i = inicioLinea; i < finLinea; i++) {
    const line = lines[i];
    // Ignorar SQL strings y object.property assignments
    if (!line.includes('UPDATE') && !line.includes('SELECT') && !line.includes('WHERE')
        && !line.match(/\.([a-zA-Z_]\w+)\s*=/)) {
        const simpleAssign = line.match(/(?<![.\w])([a-zA-Z_]\w+)\s*=\s*(?!\s*\w)/);
        if (simpleAssign && !declaredVars.has(simpleAssign[1])) {
            console.log('IMPLICIT GLOBAL: LÍNEA ' + (i+1) + ': ' + simpleAssign[1] + ' = ' + line.trim().split('=')[1]?.trim());
        }
    }
}
"
```

## Paso 4 — Aplicar el fix a TODAS las variables afectadas

Mover TODAS las declaraciones al mismo nivel de scope:

```javascript
// ANTES (dentro del bloque if):
if (condicion) {
    let signalSide = 'none';      // ← DENTRO del bloque
    let isReEntry = false;        // ← DENTRO del bloque
}
// Uso fuera del bloque — ReferenceError!

// DESPUES (declaradas FUERA con valores por defecto):
let signalSide = 'none';         // ← FUERA del bloque, antes de if
let isReEntry = false;           // ← FUERA del bloque, antes de if

if (condicion) {
    signalSide = 'none';         // ← solo asignación dentro del bloque
    isReEntry = false;           // ← solo asignación dentro del bloque
}
// Uso fuera del bloque — OK ✓
```

## Paso 5 — Verificar que no haya más variables con el mismo problema

Después de aplicar el fix, verificar que no queden variables sin declarar:

```bash
# Escanear nuevamente para confirmar
!claude-retain scope-checker "bot.js" --function analyzeStrategyLoop --verify
```

## Anti-patrones a evitar

| Anti-patrón | Patrón correcto |
|---|---|
| Fijar solo la variable del error | Fijar TODAS las variables con el mismo problema |
| Declarar dentro del bloque condicional | Declarar FUERA con default value |
| Asumir que `const` es siempre local | Verificar si el bloque condicional cierra antes del uso |
| Ignorar implicit globals (sin `let/var/const`) | Buscar asignaciones sin declaración (implicit global) |
| Solo verificar la variable del error | Escanear TODAS las variables del archivo |

## Flujo completo de scope-checker

```
ERROR: X is not defined
  ↓
1. ¿La variable se declara dentro de un bloque condicional?
   → Sí: mover declaración fuera + convertir a asignación
  ↓
2. ¿Hay más variables con el mismo problema?
   → Sí: fijar TODAS, no solo la del error
  ↓
3. ¿La variable era implicit global (sin let/var/const)?
   → Sí: añadir declaración con default value
  ↓
4. Verificar que no queden variables sin declarar
```

## Patrones comunes de errores de scope

### Patrón A — Variable declarada dentro de `if` pero usada fuera

```javascript
if (ohlcv && ohlcv.length > 0) {
    let currM = macdLine[macdLine.length - 1];  // DENTRO del if
}
// Uso de currM aquí — ReferenceError!
```

### Patrón B — Implicit global (asignación sin declaración)

```javascript
if (wArr.length > 0) {
    obCrossWallContra = contra / wArr.length;  // Sin let/var/const
}
// obCrossWallContra es implicit global — funciona en no-strict, bug en strict
```

### Patrón C — Variable declarada con `const` dentro de bloque que cierra antes del uso

```javascript
if (condicion) {
    const atrPct = currentATR / price * 100;  // DENTRO del if
}
// Uso de atrPct aquí — ReferenceError!
```

