# Canonicalización de productos — pipeline automático

Cómo `hist_items` se agrupa en productos canónicos (`hist_productos_canonicos`) para el
dashboard de demanda. **Automático y determinístico** (sin IA, sin Groq, sin toqueteo
manual por ítem). Fecha de esta versión (v5): **2026-11-26**.

## El problema que resuelve

El dashboard agrupa ítems por `producto_canonico_id`. Un ítem sin canónico cae en el
fallback (UNSPSC o descripción) y se marca **provisional** en la UI
([app/src/lib/historico.ts](../app/src/lib/historico.ts) `isProvisional`).

Antes había **3.238 provisionales (34%)** por dos causas distintas:
1. **Fragmentación de duplicados** — el mismo producto partido por texto ruidoso:
   prefijo de etiqueta UNSPSC variable ("Papel en formas continuas" vs "Papel offset"…),
   medidas en mil formatos ("9 ½ x 11", "9 1/2 X 11 PLG", "9.5*11"), mayúsculas, acentos.
   Ej.: papel continuo = 108 ítems rotos en 64 piezas cuando son ~4 productos.
2. **Singletons genuinos** marcados provisionales — productos que aparecen una sola vez;
   el agrupador viejo solo creaba canónico para grupos ≥2, así que todo producto único
   quedaba "provisional" **por diseño**, no por estar mal estructurado (long-tail: 446
   familias distintas).

## La solución (v5)

`scratchpad/recablear_v5.py` reconstruye los canónicos desde cero (idempotente) con:

1. **Firma estructurada (SKU)** — consumibles con identificador fuerte (toner/cinta por
   marca + part-number) agrupan por su firma. `scratchpad/fase3_firma.py`.
2. **Normalizador genérico** — todo lo demás agrupa por una clave que **normaliza
   medidas, unidades y ruido** en vez del texto crudo: colapsa `A x B x C` a un token
   único, unifica números+unidad, quita prefijo UNSPSC/acentos/mayúsculas/palabras-ruido.
   `scratchpad/normalizador.py`.
3. **Singletons confiables reciben canónico** — un ítem con clave confiable (familia +
   ≥1 atributo fuerte: una medida, un número+unidad, o ≥2 atributos) se canoniza aunque
   aparezca una sola vez. Así **"provisional" deja de significar "soy único"** y pasa a
   significar **"revísame: descripción vaga"** (familia sola, sin atributos).

### Resultado en producción (2026-11-26)

| | Antes | v5 |
|---|---|---|
| Canónicos | 1.292 | **4.257** (1.303 grupos ≥2 + 2.954 únicos confiables) |
| **Provisionales** | 3.238 (34%) | **50 (0,5%)** — solo los genuinamente vagos |
| CM canonicalizados | ~44% | **99%** |

Sin cambios de frontend: como cada ítem confiable recibe `producto_canonico_id`, el
`isProvisional` existente refleja el nuevo significado solo.

## Automatización (fin del toqueteo manual)

`procesamiento/historico/cargar_dashboard.py` llama a `recanonizar()` al final de cada
carga `--write`. Es decir: **cada vez que entran datos nuevos, se re-canonizan solos** con
el normalizador actual. No hay paso manual.

```bash
# carga normal: al terminar, re-canoniza automáticamente
scraper/venv/bin/python -m procesamiento.historico.cargar_dashboard --run <salida> --write

# re-canonizar sin recargar datos (p.ej. tras mejorar el normalizador):
scraper/venv/bin/python scratchpad/recablear_v5.py --write      # (dry-run sin --write)
```

## Reversible

`recablear_v5` hace NULL de todas las asignaciones + DELETE de los canónicos + recrea.
Para volver al agrupado anterior: `scratchpad/recablear_v4.py --write`.

## Reglas finas por familia

Cuando el normalizador genérico separa de más (keyea por atributo secundario), se agrega
una **regla por familia** en `normalizador.py` (`firma_familia` → dispatch). Se escribe
UNA vez por familia-commodity, nunca por ítem.

- **Papel continuo** (`_firma_papel_continuo`): identidad = `ancho x alto x nº de copias`.
  Ignora gramaje (55/56/70), nº de caja (750/1000/1500), "químico/blanco/troquelado/
  desglose" y el troquelado 5½. Resultado: papel continuo **42 → 8 canónicos** (los 3
  productos reales 9½×11 en ×2/×3/×4 concentran 95 de 108 ítems). Solo aplica si la
  familia es papel (evita falsos positivos como una impresora que menciona "papel continuo").

Próximas candidatas (si se ven feas en el dashboard): limpieza, cable/eléctrico, muebles.

## Robustez de red

`recablear_v3._urlopen_retry` reintenta (5×, backoff) ante resets transitorios
(Errno 54 / timeouts). Sin esto, un reset a mitad del PATCH dejaba la DB en estado
**parcial** (canónicos creados pero ítems a medio asignar). El rebuild es idempotente:
ante cualquier estado parcial, re-correr `recablear_v5.py --write` lo deja consistente.

## Límites conocidos

- 50 ítems quedan provisionales por descripción vaga ("PERFORADORA", "ESPONJA"): correcto
  que pidan revisión; no se fuerzan.
