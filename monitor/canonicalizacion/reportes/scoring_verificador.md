# Scoring del verificador vs etiquetas asistidas (3 niveles) — validacion_verificador_etiquetada_chatgpt.csv

Pares evaluables: 53. **Concordancia (NO precisión demostrada):** FAMILIA_AMPLIA 53/53 · SUBFAMILIA 52/53 · PRODUCTO_ESPECIFICO 45/53.
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
| **SI** | 28 | 0 | 0 |
| **NO** | 0 | 20 | 0 |
| **INSUF** | 1 | 0 | 4 |

## Matriz de confusión — PRODUCTO_ESPECIFICO  (filas=humano, cols=propuesta)
| humano\propuesta | SI | NO | INSUF |
|---|---|---|---|
| **SI** | 3 | 0 | 0 |
| **NO** | 0 | 31 | 1 |
| **INSUF** | 7 | 0 | 11 |

## Discrepancias (todas)
- **V004** [papel_continuo] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56»  · B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56»
    - nota: Químico y calca con desglose pueden describir misma función; B está truncada y no prueba diferencia de composición.
- **V005** [papel_continuo] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL CONTINUO; MEDIDAS 9 1/2 X11X4X5.5; GRAMAJE 56 GRS»  · B: «Papel Continuo; Medidas 91/2 X11x4 Troquelado a 5.5; Gr»
    - nota: Carbónico frente a químico podría indicar materiales distintos o uso comercial impreciso; falta evidencia suficiente para identidad exacta.
- **V018** [papel_bond] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75 Grs.; COLOR BLANC»  · B: «Papel Bond; Tamaño Oficio; Gramaje 75 Grs.; Color Blanc»
    - nota: Coincide papel oficio 75 blanco 500; B exige/nombra normas ISO que A no acredita: no probar identidad exacta.
- **V023** [papel_continuo] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56»  · B: «Papel Continuo; Medidas 9 1/2 x 11 x 2 Plg.; Gramaje 56»
    - nota: B no declara gramaje; identidad exacta no demostrable bajo criterio conservador aunque los demás atributos coincidan.
- **V026** [papel_bond] (ChatGPT ERROR_DE=ninguno) — SUBFAMILIA: propuesta=SI humano=INSUF
    - A: «PAPEL BOND TAMAÑO CARTA»  · B: «PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 GRS; COLOR BLANCO;»
    - nota: Solo tamaño carta en A; faltan gramaje, color y presentación.
- **V030** [papel_continuo] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL CONTINUO; MEDIDAS 9 1/2*11*4*5.5; GRAMAJE 56 GRS.»  · B: «Papel Continuo; Medidas 9 1/2 x11x4 Troquelado a 5.5; G»
    - nota: Formato, 4 partes y gramaje coinciden; caja 750 hojas frente a 750 juegos: unidades distintas/ambiguas.
- **V040** [papel_bond] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL BOND TAMAÑO CARTA: GRAMAJE 75G/M2 COLOR BLANCO AL»  · B: «PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO»
    - nota: A precisa alcalino, B no. Evitar afirmar identidad exacta sin establecer equivalencia del requisito.
- **V045** [papel_continuo] (ChatGPT ERROR_DE=extractor) — PRODUCTO_ESPECIFICO: propuesta=INSUF humano=NO
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2X11X4X5.5, GRAMAJE 56 GRS,»  · B: «Papel Continuo; 9 1/2 x 5 1/2 4; Gramaje 56 Grs.; Caja »
    - nota: B 9,5 x 5,5 x 4 puede expresar tamaño o troquelado (falta 11); el formato no se puede confirmar; empaque explícito 750 juegos vs 1000 hojas difiere.
- **V047** [papel_bond] (ChatGPT ERROR_DE=verificador) — PRODUCTO_ESPECIFICO: propuesta=SI humano=INSUF
    - A: «PAPEL BOND TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO;»  · B: «PAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75G/M-20 LB .; COLOR»
    - nota: Ambos oficio 75 blanco 500; ISO 9706 en B no consta en A, impide probar identidad estricta.