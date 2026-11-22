# CM (Compra Menor) — OCR → Estructuración → Auditoría

Runbook del pipeline que convierte las ofertas CM escaneadas (imágenes) en
registros estructurados reutilizables para la canonicalización y el dashboard de
demanda. Documenta **cómo se hizo** para poder repetirlo o extenderlo.

Fecha del cierre de esta pasada: **2026-11-22**. Estado: **560 / 560 estructurados**.

---

## 1. Qué es esto

Las CM (Compra Menor) del Órgano Judicial llegan como **PDF escaneado** (no texto).
Hay 571 procesos CM. Para analizarlos como demanda por producto hay que pasar de
"imagen de una proforma/DBC" a items estructurados con cantidad y unidad.

Flujo de tres etapas:

1. **OCR** (ya hecho previamente): `dbc_ocr.py` / Tesseract `spa` lee cada escaneo y
   deja el texto crudo en `scratchpad/ocr_cm/<cuce>.txt`.
2. **Estructuración** (esta pasada): convertir cada OCR en un registro JSON con sus
   items. Store reanudable en `scratchpad/cm_estructurado.jsonl`.
3. **Canonicalización** (pendiente): pasar el store por el pre-keyer híbrido y
   cablear a `hist_productos_canonicos` / dashboard, igual que los 725 DBC.

---

## 2. Archivos

| Archivo | Rol |
|---|---|
| `scratchpad/ocr_cm/<cuce>.txt` | Texto OCR crudo por CUCE (entrada). 571 archivos. |
| `scratchpad/cm_next.py` | Sirve los próximos N CUCE pendientes (no en el store, no en cuarentena). |
| `scratchpad/cm_append.py` | Valida un lote, deduplica por `cuce`, normaliza y agrega al store. |
| `scratchpad/cm_estructurado.jsonl` | **EL STORE** (salida). Un registro por línea. Es el puntero de reanudación. |
| `scratchpad/cm_batch.json` | Lote de trabajo (se reescribe cada vuelta). |
| `scratchpad/_lote.txt` | Volcado OCR que lee el estructurador (se reescribe cada vuelta). |
| `scratchpad/cm_malos.json` | Cuarentena: CUCE con OCR espejado/ilegible (11). `cm_next.py` los salta. |
| `scratchpad/cm_dudosos_sub.txt` | Lista de CUCE marcados dudosos en la auditoría, con nota del porqué. |

### Forma del registro en el store

```json
{"cuce":"25-0660-07-1567072-1-1","fuente":"cm_ocr","n_items":1,
 "items":[{"item":1,"descripcion":"Toner Lexmark 56F4000 negro",
           "especificaciones":"rendimiento 6000 pag; compatible MS421",
           "cantidad":22,"unidad":"pieza"}],
 "ts":"2026-11-22T..."}
```

`cm_append.py` normaliza claves faltantes: `cantidad→null`, `unidad→null`,
`especificaciones→""`. Deduplica por `cuce` (reejecutar es seguro, no duplica).

---

## 3. El loop (cómo se corre)

Tres pasos por vuelta, repetir hasta `PENDIENTES: 0`:

```bash
# 1. pedir los próximos 15 pendientes
python3 scratchpad/cm_next.py 15 > scratchpad/_lote.txt 2>&1
# 2. (modelo) leer _lote.txt COMPLETO y escribir scratchpad/cm_batch.json
#    con un array de {cuce, items:[...]} — uno por cada CUCE mostrado
# 3. agregar al store
python3 scratchpad/cm_append.py   # -> "agregados N | duplicados D | store total T"
```

El store ES el puntero: si se corta, `cm_next.py` vuelve a servir solo lo que falta.

---

## 4. Quién hace la estructuración (decisión de costo)

La estructuración es **transcripción/extracción**, no razonamiento profundo. Hacerla
toda con Opus es el método más caro posible (Opus leyendo miles de líneas de OCR
sucio). El reparto que funcionó bien:

- **Subagente Sonnet** hace el loop completo (lee OCR → escribe JSON → `cm_append`),
  de corrido. ~5x más barato que Opus para esta tarea.
- El subagente **marca los dudosos** en `cm_dudosos_sub.txt` (OCR ilegible,
  cantidad adivinada, tabla espejada) con una nota corta.
- **Opus audita** solo esa lista de dudosos + una muestra, y corrige.

Resultado medido: 164 CM nuevos estructurados por ~653K tokens de Sonnet. Los 3
únicos errores numéricos que aparecieron estaban **todos dentro de la lista de
dudosos** — el sistema de banderas los atrapó donde debía.

> **NO se usa ninguna API externa ni Groq para esto.** Lo hace el modelo en-chat
> (Sonnet para el bulto, Opus para la curaduría).

---

## 5. Convenciones de estructuración

### Cantidad
- Tomar de la tabla **"ESPECIFICACIONES/CARACTERÍSTICAS TÉCNICAS DEL BIEN"** del DBC
  (es el requerimiento autoritativo).
- Si solo hay cotización con precio unitario y total: **derivar**
  `cantidad = total / precio_unitario` (redondear al entero obvio).
- Si está ilegible/garabateada/no aparece: `cantidad = null`. **El null es seguro;
  es preferible a inventar un número.**
- El OCR suele mostrar columnas `[cantidad · precio · total]`; se valida la
  derivación comprobando `cantidad × precio = total`.

### Unidad
- Inferir: `pieza, caja, rollo, litro, metro, juego, servicio, lote, frasco, bidón...`
- Si no se sabe: `pieza` para bienes contables, `servicio` para servicios.

### Bundling (un solo item)
- Autopartes de vehículos ilegibles/garabateadas → un item `lote`, `cantidad null`.
- Contratos de "provisión" (repuestos de aires acondicionados, periódico, servicios
  recurrentes) → un item `servicio`, `cantidad null`, alcance en especificaciones.
- Si hay varios bienes claros y distintos (ej. fusor + disco duro), **sí** se separan.

### Texto
- Valores sin tildes/ASCII plano está bien (el OCR viene sucio).
- `especificaciones` en una línea, detalles separados por `; `.

---

## 6. Auditoría hecha (2026-11-22)

- Integridad: 560 registros, 2.535 items, 0 JSON malos, 0 descripciones vacías,
  21% de items con `cantidad null` (servicios/bundles/ilegibles).
- Sonnet marcó **39 dudosos**; de ellos **30 con número derivado** (el riesgo real;
  los otros 9 son solo-null, seguros).
- Opus auditó los 30 derivados contra el OCR crudo (aritmética cantidad×precio=total).
- **Correcciones aplicadas (3 en total):**
  - `25-0660-09-1521974` Fusor HP RM1-7547: 25 → **20** (`PIEZA 2500 50000`).
  - `25-0660-10-1602686` Ambientador aerosol: 600 → **500** (`500 20.00 10.000,00`).
  - (una tercera corregida durante la validación de muestra, mismo patrón.)
- **A vigilar** (quedó flagueado, no corregido por OCR demasiado fragmentario):
  `26-0660-09-1676860` (cámaras sala Gesell) asumió "1 por item" pero el OCR insinúa
  que la cámara bala podría ser 8. Revisar el DBC original si ese proceso importa.

---

## 7. Cómo repetir / extender

- **Reanudar si faltaran CUCE:** correr el loop de la §3; el store se encarga del
  resto. Para incluir los de cuarentena: `cm_next.py N --incluir-sosp`.
- **Re-estructurar un CUCE puntual:** borrar su línea del store y volver a correr.
- **Nuevos CM (nueva gestión):** correr el OCR (`dbc_ocr.py`) para generar
  `ocr_cm/<cuce>.txt`, y luego el loop de la §3.
- **Siguiente etapa:** pre-keyer híbrido + cableado a canónicos (ver
  `monitor/canonicalizacion/`), tratando el store como fuente `cm_ocr`.
