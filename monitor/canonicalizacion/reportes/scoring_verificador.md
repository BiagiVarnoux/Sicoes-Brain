# Scoring del verificador vs etiquetas asistidas (3 niveles) — validacion_verificador_etiquetada_chatgpt.csv

Pares evaluables: 53. **Concordancia (NO precisión demostrada):** FAMILIA_AMPLIA 53/53 · SUBFAMILIA 49/53 · PRODUCTO_ESPECIFICO 51/53.
> Las etiquetas son asistidas (ChatGPT), NO verdad certificada; la muestra trae las propuestas del algoritmo (no es ciega del todo). Concordancia ≠ precisión real.
> ⚠️ **ESTA muestra (53) INFORMÓ las correcciones de la capa correctiva v2** → su concordancia post-fix NO es validación independiente (ChatGPT lo advirtió). La validación real debe hacerse sobre `muestras/validacion_verificador2_ciega.csv` (nueva, no usada para ajustar), aún sin etiquetar.


## Matriz de confusión — FAMILIA_AMPLIA  (filas=humano, cols=propuesta)
| humano\propuesta | SI | NO | INSUF |
|---|---|---|---|
| **SI** | 53 | 0 | 0 |
| **NO** | 0 | 0 | 0 |
| **INSUF** | 0 | 0 | 0 |

## Matriz de confusión — SUBFAMILIA  (filas=humano, cols=propuesta)
| humano\propuesta | SI | NO | INSUF |
|---|---|---|---|
| **SI** | 24 | 0 | 4 |
| **NO** | 0 | 20 | 0 |
| **INSUF** | 0 | 0 | 5 |

## Matriz de confusión — PRODUCTO_ESPECIFICO  (filas=humano, cols=propuesta)
| humano\propuesta | SI | NO | INSUF |
|---|---|---|---|
| **SI** | 3 | 0 | 0 |
| **NO** | 0 | 31 | 1 |
| **INSUF** | 1 | 0 | 17 |

## Discrepancias (todas)
- **V011** [papel_continuo] (ChatGPT ERROR_DE=ninguno) — SUBFAMILIA: propuesta=INSUF humano=SI
    - A: «PAPEL CONTINUO 9 1/2X11X4»  · B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X11X4X5.5; GRAMAJE 56 GRS»
    - nota: Formato y número de partes iguales, pero faltan gramaje, tipo y empaque de A.
- **V023** [papel_continuo] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56»  · B: «Papel Continuo; Medidas 9 1/2 x 11 x 2 Plg.; Gramaje 56»
    - nota: B no declara gramaje; identidad exacta no demostrable bajo criterio conservador aunque los demás atributos coincidan.
- **V027** [papel_bond] (ChatGPT ERROR_DE=verificador) — SUBFAMILIA: propuesta=INSUF humano=SI
    - A: «PAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75G/M-20 LB .; COLOR»  · B: «PAPEL TAMAÑO OFICIO DE COLOR SURTIDO»
    - nota: Oficio blanco frente a oficio surtido: subfamilia comparable pero específico distinto.
- **V035** [papel_continuo] (ChatGPT ERROR_DE=verificador) — SUBFAMILIA: propuesta=INSUF humano=SI
    - A: «PAPEL CONTINUO TROQUELADO 9 1/2 x 11 x 4 x 5,5 750 JGS,»  · B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X11X4X5.5; GRAMAJE 56 GRS»
    - nota: Químico frente a carbónico puede indicar diferencia material, pero el término comercial es ambiguo; revisar antes de declarar distinto específico.
- **V045** [papel_continuo] (ChatGPT ERROR_DE=extractor) — PRODUCTO_ESPECIFICO: propuesta=INSUF humano=NO
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2X11X4X5.5, GRAMAJE 56 GRS,»  · B: «Papel Continuo; 9 1/2 x 5 1/2 4; Gramaje 56 Grs.; Caja »
    - nota: B 9,5 x 5,5 x 4 puede expresar tamaño o troquelado (falta 11); el formato no se puede confirmar; empaque explícito 750 juegos vs 1000 hojas difiere.
- **V051** [papel_continuo] (ChatGPT ERROR_DE=ninguno) — SUBFAMILIA: propuesta=INSUF humano=SI
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»  · B: «PAPEL CONTINUO TROQUELADO 9 1/2x 11x4x5,5 750 jgs, QUIM»
    - nota: A no indica gramaje, tipo químico, presentación ni troquelado; misma medida y partes.