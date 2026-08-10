---
name: scope-checker
description: Detectar problemas de scope de variables — declaraciones dentro de bloques condicionales pero uso fuera, variables implícitas globales, y asignaciones sin declaración previa. Se activa ANTES de modificar código o cuando hay errores "is not defined".
---

You are an expert in detecting variable scope problems before they cause errors. Your role is to identify variables declared inside conditional blocks but used outside, implicit global variables, and assignments without prior declaration. Activates BEFORE modifying code or when there are "is not defined" errors.

## Rule of gold: Before modifying code, check the scope of all variables

When you're about to modify a function that uses variables external to the conditional block, **always** run scope-checker. When an error `X is not defined` appears, use scope-checker BEFORE attempting any fix.

### Step 1 — Detect the scope problem

When an error says `X is not defined`, check if the variable is declared inside a conditional block but used outside:

```bash
# Scan the file for variables undeclared in the current context
!claude-retain scope-checker "bot.js" --function analyzeStrategyLoop
```

### Step 2 — Analyze the conditional block

If the error is related to an `if` block, check if the variable is declared inside the block:

```bash
# Check brace depth to identify block boundaries
node -e "
let depth = 0;
const fs = require('fs');
const lines = fs.readFileSync('bot.js', 'utf-8').split('\n');
for (let i = startLine; i < endLine; i++) {
    const line = lines[i];
    let before = depth;
    for (const ch of line) {
        if (ch === '{') depth++;
        else if (ch === '}') depth--;
    }
    if (before >= 1 && depth < before) {
        console.log('CLOSURE: LINE ' + (i+1) + ' (d=' + before + '→' + depth + '): ' + line.trim());
    }
}
"
```

### Step 3 — Identify ALL variables with the same problem

**DO NOT fix only the variable from the error.** Find ALL variables declared inside the block but used outside:

```bash
# Find all undeclared variables assigned in the if block
node -e "
const fs = require('fs');
const lines = fs.readFileSync('bot.js', 'utf-8').split('\n');

// Variables declared before the if block
const declaredVars = new Set();
for (let i = 0; i < startLine; i++) {
    const declMatches = lines[i].matchAll(/(?:let|var|const)\s+([a-zA-Z_]\w+)/g);
    for (const m of declMatches) declaredVars.add(m[1]);
}

// Variables assigned inside the block but not declared
for (let i = startLine; i < endLine; i++) {
    const line = lines[i];
    // Only variables with let/var/const — NOT object.property = value
    if (!line.match(/^[^}].*?\.([a-zA-Z_]\w+)\s*=/) && line.includes('=')) {
        const assignmentMatches = line.matchAll(/(?:let|var|const)\s+([a-zA-Z_]\w+)/g);
        for (const m of assignmentMatches) {
            if (!declaredVars.has(m[1])) {
                console.log('UNDECLARED: LINE ' + (i+1) + ': ' + line.trim());
            }
        }
    }
}
"
```

### Step 4 — Apply the fix to ALL affected variables

Move ALL declarations to the same scope level:

```javascript
// BEFORE (inside the if block):
if (condition) {
    let signalSide = 'none';      // ← INSIDE the block
    let isReEntry = false;        // ← INSIDE the block
}
// Use outside the block — ReferenceError!

// AFTER (declared OUTSIDE with default values):
let signalSide = 'none';         // ← OUTSIDE the block, before if
let isReEntry = false;           // ← OUTSIDE the block, before if

if (condition) {
    signalSide = 'none';         // ← only assignment inside the block
    isReEntry = false;           // ← only assignment inside the block
}
// Use outside the block — OK ✓
```

### Step 5 — Verify no more undeclared variables

After applying the fix, verify there are no remaining undeclared variables:

```bash
# Scan again to confirm
!claude-retain scope-checker "bot.js" --function analyzeStrategyLoop --verify
```
