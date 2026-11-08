# Mapa de cobertura — taxonomía one-pass (LLM)

_Corrida completada 2026-11-07. Validada (ver abajo)._

## Qué es esto
Un LLM (Groq `gpt-oss-120b`) etiqueta TODAS las descripciones únicas en un árbol
(categoría → subcategoría → producto). Sirve como **mapa de cobertura / triaje** para priorizar qué
familias modelar en el pipeline curado — **NO como fuente de fusiones** (las fusiones salen del pipeline
curado y verificable).

## Validación del mapeo (el bug que se arregló)
- La corrida del 5-nov quedó barajada (mapeo descripción→etiqueta por índice posicional + checkpoint
  reusado con corpus crecido): 94,2% de pares hoja↔descripción sin ninguna palabra en común.
- Corregido: cada etiqueta lleva atado el texto de su descripción en el momento de etiquetar.
- **Verificación de esta corrida:** 93,4% de coincidencia cruda hoja↔descripción, y las no-coincidencias
  revisadas a mano son TODAS correctas (p. ej. hoja `TN 316` ← "TONER BROTHER TN 316 NEGRO"; la heurística
  solo ignora tokens cortos como "TN"/"316"). Mapeo efectivamente correcto. **Bug cerrado.**

## Cifras
- **4.351 descripciones etiquetadas** (de ~4.966 leídas; ~615 quedaron sin etiqueta por lotes que
  fallaron — reintentables).
- **575 categorías crudas · 2.406 hojas.**

> ⚠️ **Salvedad importante:** la fase de CONSOLIDACIÓN (unificar nombres de categoría equivalentes y
> fusionar hojas que son el mismo producto) **falló a mitad porque se agotó el cupo DIARIO de Groq (TPD)**.
> Por eso hay 575 categorías crudas en vez de ~100: una misma familia aparece partida en varios nombres
> (`toner y cartuchos` / `toner` / `cartuchos de tinta`; `fusor` / `fusores`; `clips de papel` /
> `clips para papel`). El **mapeo descripción→hoja NO depende de esto y es correcto**; la consolidación es
> un refinamiento que se re-corre con `canonicalizar_taxonomia.py --solo-consolidar` cuando el cupo de
> Groq resetee (~20:00 Bolivia), reusando el checkpoint sin re-etiquetar. Las cifras por familia de abajo
> ya agrupan a mano los duplicados obvios.

## Familias por volumen (nº de descripciones) — las que hay que priorizar

Agrupando los nombres crudos equivalentes:

| familia (agrupada) | ~descripciones | ¿modelada hoy? |
|---|---:|---|
| **Impresión: tóner + cartuchos + tinta + tambores + fusores** | **~640** | ❌ NO |
| Útiles de escritura (marcadores, bolígrafos, resaltadores) | ~160 | ❌ NO |
| Papel (bond + continuo + impresión computadoras) | ~240 | ✅ parcial (bond/continuo sí) |
| Archivo (folders, carpetas, sujetadores, clips, grapas) | ~260 | ❌ NO |
| Mobiliario (sillas, escritorios, muebles de oficina) | ~150 | ❌ NO |
| Repuestos (automotrices, aire acondicionado, torres de enfriamiento) | ~115 | ❌ NO |
| Sellos y estampillas | ~40 | ❌ NO |
| Discos ópticos | ~39 | ✅ sí |
| Tijeras | ~33 | ❌ NO |

**Lectura:** el pipeline curado modela hoy 8 categorías y solo cubre ~340 de ~5.067 descripciones. La
**gran mayoría del volumen sin cubrir está en impresión (tóner/cartuchos/tinta)** — es, de lejos, la
familia #1 a modelar a continuación, seguida de útiles de oficina y archivo.

## Top 30 categorías crudas (sin consolidar, como las dejó el LLM)

```
 169  toner y cartuchos          62  papel bond ✅            40  sellos y estampillas
 160  toner                      61  boligrafos              39  discos opticos ✅
 135  cartuchos de tinta         59  folders                 36  escritorios
  98  accesorios de oficina      53  carpetas                36  papel impresion computadoras
  78  papel                      44  silla de oficina        35  fusores
  76  tambores                   41  sujetadores de pinza    35  resaltadores
  67  marcadores                 40  aire acondicionado rep. 34  accesorios torres enfriam.
  66  papel continuo ✅          40  clips de papel          34  fusor
  64  grapas                     40  clips para papel        34  tinta para impresora
  62  (papel bond)               40  repuestos automotrices  33  tijeras / 32 muebles oficina
```

(Las ✅ ya están modeladas en el pipeline curado; el resto no.)

## Recomendación de priorización
1. **Impresión (tóner/cartuchos/tinta/tambores/fusores)** — mayor volumen, y la identidad es clara
   (modelo del consumible: 78A, TN-316, GPR-63…). Alto valor, modelado tratable.
2. **Útiles de oficina y archivo** (marcadores, bolígrafos, folders, clips, grapas) — mucho volumen,
   identidad más difusa; evaluar granularidad con el humano.
3. Completar la consolidación del árbol (cuando resetee Groq) para un mapa más limpio.
