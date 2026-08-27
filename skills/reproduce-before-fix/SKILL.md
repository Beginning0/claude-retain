---
name: reproduce-before-fix
description: Cuando encuentres un error en cualquier proyecto — reproduce el fallo con un caso límite, lee el traceback real e inspecciona la API instalada antes de tocar código. Nunca adivines.
allowed-tools: [Bash]
---

## Regla de oro: NO toques código hasta haber reproducido el error

La mayoría de los fixes son síntomas re-empujados a otro lado. Antes de editar nada, sigue este flujo de 3 pasos. La herramienta clave es **ejecutar el caso que hace fallar**, no adivinar leyendo archivos.

### Paso 1 — Reproduce con un caso límite (no el happy path)

Los bugs viven en los bordes: primera vez, estado vacío, input máximo, vacío, concurrencia. El happy path (datos reales que ya funcionan) nunca los muestra. Prueba el caso límite más relevante:

```bash
# Primera instalación / state vacío — el que escondió el bug de chroma
python -c "from mi_modulo import fn; fn(en_estado_vacio=True)"

# Bordes: vacío, nulo, máximo, lista vacía
python -c "from mi_modulo import fn; fn(vacio='', maximo=10**9, lista=[])"

# El comando real con datos reales del proyecto (no mocks)
./bin/tu-comando --auto     # o el entry point real del proyecto
```

Si no crashea pero el resultado es raro, compara contra lo esperado: un `diff` o un `assert`. Sin reproducción NO hay fix válido.

### Paso 2 — LeE el traceback REAL, no lo adivines

Copia el mensaje exacto. Casi siempre dice qué falló y dónde. Un `try/except` que imprime solo `str(e)` esconde el detalle — busca el `Traceback (most recent call last):` completo:

```
sqlite3.ProgrammingError: Incorrect number of bindings supplied.
    The current statement uses 2, and there are 3 supplied.
```
Eso ya te dice que hay un binding de más → el bug está en los params de la SQL, no en otra parte.

### Paso 3 — Inspecciona la API INSTALADA, no la que recuerdas

Asumir "esta librería así funciona" es la causa #1 de bugs falsos. Verifica versión + firma real en vez de confiar en memoria:

```bash
python -c "import x; print(x.__version__)"                                   # versión instalada
python -c "import inspect, x; print(inspect.signature(x.func))"              # firma real
python -c "import x; print([m for m in dir(x) if not m.startswith('_')])"   # qué expone
```

El bug de chroma 1.5.5: un `lambda` como `embedding_function` daba
`Expected EmbeddingFunction.__call__ ... got args, kwargs`. La API real exige
un objeto con `__call__(self, input)` — lo confirmé inspeccionando
`EmbeddingFunction`, no suponiendo. Sin esto te pasarías horas arreglando el lugar equivocado.

### Después de reproducir: causa raíz, no síntoma

- Encuentra DÓNDE se dispara (grep de todos los callers). Un guard en la función compartida es un diff más pequeño que parchear cada caller.
- Fija la raíz con el diff más pequeño que corrija EL caso reproducido.
- Deja UNA verificación que falle si la lógica se rompe: un `assert` en un `demo()`/`__main__` o un test pequeño. Sin check, el fix no está terminado.
- No arregles 5 síntomas y dejes el original vivo.

## Checklist rápida
- [ ] ¿Reproduje el error con un caso real/límite? (no solo happy path)
- [ ] ¿Leí el traceback completo?
- [ ] ¿Verifiqué la API/versión instalada vs. lo que asumía?
- [ ] ¿Fijé la causa raíz con el diff más pequeño?
- [ ] ¿Dejé una verificación que falle si se rompe?
