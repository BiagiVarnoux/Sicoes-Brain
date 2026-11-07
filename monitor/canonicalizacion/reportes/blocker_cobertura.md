# Etapa 2 — Blocker de candidatos por atributos (cobertura y descartes, solo lectura)

Universo: **5067 descripciones ÚNICAS** (NO los ~7.441 registros hist_items).

## Estado de los ítems (cobertura global, sobre descripciones únicas)
- fuera_alcance (None): 3390
- delegado_motor (consumible): 1337
- en_alcance (atributos): 340

**En alcance del blocker por atributos: 340** (categorías: almacenamiento, llanta, optico, papel_bond, papel_continuo, papel_impreso, ram, sobre_manila)

> Suma de estados = 5067 descripciones únicas.

## Por familia amplia (= categoría = tipo)
| categoría | ítems | subfamilias distintas | solo familia_amplia | pares candidatos | comparten subfamilia |
|---|---|---|---|---|---|
| almacenamiento | 27 | 9 | 11 | 351 | 9 |
| llanta | 33 | 16 | 5 | 528 | 19 |
| optico | 34 | 2 | 15 | 561 | 137 |
| papel_bond | 105 | 4 | 13 | 5460 | 2009 |
| papel_continuo | 63 | 4 | 6 | 1953 | 549 |
| papel_impreso | 26 | 2 | 1 | 325 | 150 |
| ram | 26 | 6 | 4 | 325 | 71 |
| sobre_manila | 26 | 6 | 0 | 325 | 66 |

## Descartes AGREGADOS y auditables
- Pares cross-categoría NO generados (restricción dura de tipo): **47,802** de 57,630 posibles entre ítems en alcance.
- Ítems delegados al motor v2 por código (consumible_impresion): 1337.
- Ítems fuera de alcance (equipos/accesorios/otros): 3390.
- Ítems en alcance SIN segmento completo (candidatos solo a familia_amplia): 55 (no se pierden; el verificador decide).

## Nota de diseño
El blocker NO fusiona ni asigna familia: solo propone pares candidatos dentro del mismo tipo. `comparten_subfamilia` es una ETIQUETA del par, no un filtro. Los pares cross-tipo se descartan por regla dura de tipo (agregado). La ausencia de pérdidas dentro del tipo modelado es de DISEÑO, pendiente de validación independiente.

## (validación) Blocker-recall sobre la muestra v2 CONGELADA (no se ajustó nada con ella)
- Relaciones reales (específico+familia): 28
- Capturadas (misma familia amplia=tipo): **19/28 (67%)** — generador anterior por firmas: 36% (10/28).
- MISMO_ESPECIFICO: 5/9.
- 9 no capturados (categorías aún no modeladas por la Etapa 1 → None):
  - [None vs None] «PERFORADORA; ALTO 40 HOJAS; NRO. DE PERF» ↔ «Perforadora; Alto 40 Hojas; Nro. de Perf»
  - [None vs None] «LUSTRA MUEBLE PRESENTACION FRASCO ATOMIZ» ↔ «LUSTRA MUEBLE DE 850 ML ENVASE CON ATOMI»
  - [None vs None] «PERFORADORA; ALTO 40 HOJAS; NRO. DE PERF» ↔ «Perforadora; alto 40 hojas; nro. de perf»
  - [None vs None] «PERFORADORA ALTO 40 HOJAS; NRO. DE PERFO» ↔ «PERFORADORA; ALTO 20/25 HOJAS; NRO. DE P»
  - [None vs None] «ARCHIVADOR DE PALANCA; MATERIAL: CARTON » ↔ «ARCHIVADOR DE PALANCA; MATERIAL CARTON; »
  - [None vs None] «ARCHIVADOR DE PALANCA LOMO MEDIO PLASTIF» ↔ «ARCHIVADOR DE PALANCA LOMO ANCHO PLASTIF»
  - [None vs None] «CLIP METALICO DE 50MM PRESENTACION CAJIT» ↔ «Clip metalico medida 78mm presentacion c»
  - [None vs None] «PERFORADORA; ALTO 40 HOJAS; NRO. DE PERF» ↔ «PERFORADORA; ALTO 40 HOJAS»
  - [None vs None] «PERFORADORA ALTO 40 HOJAS; NRO. DE PERFO» ↔ «PERFORADORA; ALTO 40 HOJAS; NRO. DE PERF»
