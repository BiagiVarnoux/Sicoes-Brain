# Entrega de fichas de adquisición v1 — 2026-11-09

Implementación local en `main`, sin commits. Esquema y reglas: [FICHAS_ADQUISICION_V1.md](FICHAS_ADQUISICION_V1.md).

Salida aceptada: `procesamiento/historico/data/adquisiciones_v1_20261109_04/`. Las corridas 01–03 son iteraciones de desarrollo conservadas, no datasets adicionales para sumar. La corrida 05 verifica repetibilidad de 04.

## Inventario local por entidad y gestión

Cada cifra de formulario cuenta documentos locales con versión válida, hash y tamaño verificados. DBC disponible no implica segmentable. No equivale a cobertura anual total de SICOES; 2026 es parcial.

| Entidad | Gestión | CUCE | FORM 500 | FORM 200 | FORM 220 | DBC | Observaciones 500 | Observaciones 200/220 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0660-10 | 2022 | 24 | 23 | 9 | 14 | 9 | 139 | 140 |
| 0660-10 | 2023 | 29 | 28 | 9 | 19 | 9 | 147 | 147 |
| 0660-10 | 2024 | 19 | 19 | 7 | 12 | 7 | 97 | 97 |
| 0660-11 | 2023 | 51 | 48 | 21 | 27 | 21 | 211 | 211 |
| 0660-11 | 2024 | 28 | 27 | 11 | 16 | 11 | 162 | 165 |
| 0660-11 | 2025 | 14 | 14 | 7 | 7 | 7 | 113 | 116 |
| 0660-11 | 2026 | 29 | 23 | 18 | 11 | 16 | 147 | 178 |

Total: 194 CUCE, 182 FORM 500, 82 FORM 200, 106 FORM 220 y 80 DBC. 1.016 observaciones de recepción y 1.054 de FORM 200/220 (incluyen 3 no contratadas, que no representan adquisiciones). Cero omisiones detectadas dentro de las tablas de bienes reconocidas.

## Cobertura de vinculación

Una ficha consolidada representa dos observaciones vinculadas; una ficha no vinculada representa una observación. Estos conteos miden cobertura de procesamiento, no número neto de adquisiciones ni demanda.

| Entidad | Gestión | Fichas | Contrato/recepción confirmada | Ambigua | Sin vínculo | Fichas con DBC confirmado |
|---|---|---:|---:|---:|---:|---:|
| 0660-10 | 2022 | 270 | 9 | 260 | 1 | 2 |
| 0660-10 | 2023 | 284 | 10 | 274 | 0 | 6 |
| 0660-10 | 2024 | 191 | 3 | 188 | 0 | 11 |
| 0660-11 | 2023 | 405 | 17 | 388 | 0 | 0 |
| 0660-11 | 2024 | 317 | 10 | 304 | 3 | 0 |
| 0660-11 | 2025 | 225 | 4 | 219 | 2 | 0 |
| 0660-11 | 2026 | 315 | 10 | 274 | 31 | 1 |

2.007 fichas: 63 pares confirmados, 1.907 fichas ambiguas y 37 sin vínculo entre recepción y contratación. Los 63 pares cubren 126/2.070 observaciones (6,1%); no es una tasa de precisión. Hay 8.998 aristas ambiguas de recepción/contratación, muchas por contrato compartido entre ítems. Son hipótesis documentales, no ventas ni equivalencias de producto.

DBC: 24 aristas confirmadas en 20 fichas; 289 fichas con candidatos ambiguos y 1.698 sin vínculo técnico. Se conservan 994 aristas DBC ambiguas sin trasladar sus atributos. De 194 CUCE, 114 no tienen DBC local, 54 tienen DBC sin bloques reconocibles y 26 tienen bloques segmentados. La cobertura técnica es insuficiente para afirmar enriquecimiento completo de las adquisiciones.

## Faltantes explícitos

| Entidad | Gestión | Sin FORM 500 | Sin FORM 200/220 | Sin DBC |
|---|---|---:|---:|---:|
| 0660-10 | 2022 | 1 | 1 | 15 |
| 0660-10 | 2023 | 1 | 1 | 20 |
| 0660-10 | 2024 | 0 | 0 | 12 |
| 0660-11 | 2023 | 3 | 3 | 30 |
| 0660-11 | 2024 | 1 | 1 | 17 |
| 0660-11 | 2025 | 0 | 0 | 7 |
| 0660-11 | 2026 | 6 | 0 | 13 |

El detalle exhaustivo por CUCE está en `cobertura_procesos.jsonl`; el inventario documental en `inventario_documental.jsonl`. Ausencia local no demuestra que el documento nunca fuera publicado. Los procesos sin formularios prioritarios siguen en el inventario aunque no generen ficha.

## Ejemplos concretos y estado de revisión

### Escritorios, recepción y contratación

CUCE `23-0660-11-1314047-1-1`; ficha `5055bfa3a26f9d263f3bf655e1a389ac7c41c6cc3c59fc6d088fee5072c576d4`. Asociación comercial: **CONFIRMADA**; DBC: **SIN_VINCULAR**.

- FORM 500, tabla 5, fila 3: EscritoriosESCRITORIOS SEMI EJECUTIVOS. Original: `scraper/historico_local/data/historico_http_paginas_0660-11_2023/23-0660-11-1314047-1-1/crudos/FORM_500__23ac39ab80718f428860dd456c2cc2a44aa68ca4e0ebe877a9740ff9dab7e822.html`; SHA256 `23ac39ab80718f428860dd456c2cc2a44aa68ca4e0ebe877a9740ff9dab7e822`.
- FORM 200, tabla 11, fila 3: EscritoriosESCRITORIOS SEMI EJECUTIVOS. Original: `scraper/historico_local/data/historico_http_paginas_0660-11_2023/23-0660-11-1314047-1-1/crudos/FORM_200__363ab2c54d78e00feeb3218509dc21b2bb72d34bbbe39063e762324c163667df.html`; SHA256 `363ab2c54d78e00feeb3218509dc21b2bb72d34bbbe39063e762324c163667df`.

### Equipo de computación con DBC

CUCE `23-0660-10-1301083-1-1`; ficha `77e73d2fd091a3bd0aef7fb9379889e8f24208b523c60b58838da03e947be755`. Asociación comercial: **CONFIRMADA**; DBC: **CONFIRMADA**.

- FORM 500, tabla 5, fila 3: Todo en una computadora de escritorioEQUIPOS DE COMPUTACIÓN DE ESCRITORIO. Original: `scraper/historico_local/data/historico_http_paginas_0660-10_2023/23-0660-10-1301083-1-1/crudos/FORM_500__b48861a8ba8a55f1033c5c4241a23a309c27a54b6aaf71ade912f3365c1a9143.html`; SHA256 `b48861a8ba8a55f1033c5c4241a23a309c27a54b6aaf71ade912f3365c1a9143`.
- FORM 200, tabla 11, fila 3: Todo en una computadora de escritorioEQUIPOS DE COMPUTACIÓN DE ESCRITORIO. Original: `scraper/historico_local/data/historico_http_paginas_0660-10_2023/23-0660-10-1301083-1-1/crudos/FORM_200__aad1b47cdda1f7c2b32f920e37fa36859506795af11c2080334822922b84f8fc.html`; SHA256 `aad1b47cdda1f7c2b32f920e37fa36859506795af11c2080334822922b84f8fc`.

### Varios proveedores e ítems

CUCE `25-0660-11-1517374-1-1`; ficha `0835255e423f857392a62e8b1dffbe75cb5d3a4c7d99ec399252ca3620564883`. Asociación comercial: **AMBIGUA**; DBC: **SIN_VINCULAR**.

- FORM 200, tabla 11, fila 18: Tóner para impresoras o faxTONER PARA IMPRESORA; MODELO DE IMPRESORA TONER HP LASERJET 1020; COLOR TINTA NEGRA; SERIE Q2612 A. Original: `scraper/historico_local/data/historico_http_paginas_0660-11_2025/25-0660-11-1517374-1-1/crudos/FORM_200__bcbe732c645f3c3c473de58e17ce9e82048e87e98302a637c3c59a5789439e9c.html`; SHA256 `bcbe732c645f3c3c473de58e17ce9e82048e87e98302a637c3c59a5789439e9c`.

### Conflicto de cantidades con DBC

CUCE `23-0660-10-1329122-1-1`; ficha `1086011d453a82783663e89b21f184cdd396d2ddca7bfda49100aaf4a4c2c5f1`. Asociación comercial: **AMBIGUA**; DBC: **AMBIGUA**.

- FORM 200, tabla 11, fila 15: Almohadilla para sellos de estampación de cauchoTAMPO DE SELLOS CON TINTA; MATERIAL METALICO; MEDIDAS 8.5X12.5 CM COLOR DE TINTA AZUL.. Original: `scraper/historico_local/data/historico_http_paginas_0660-10_2023/23-0660-10-1329122-1-1/crudos/FORM_200__7489a690a1014f9742ec33b5221c75a0221c8b0da0947361436b42a8430a9ee0.html`; SHA256 `7489a690a1014f9742ec33b5221c75a0221c8b0da0947361436b42a8430a9ee0`.

### Recepción ausente

CUCE `26-0660-11-1651293-1-1`; ficha `0776f5dcc5b6539401dbf11ab33cde1838de33a596dc98086417560e5ac7e1da`. Asociación comercial: **SIN_VINCULAR**; DBC: **SIN_VINCULAR**.

- FORM 200, tabla 11, fila 10: Antiséptico de aireAmbientador sólido embace cartón perfumado. Original: `scraper/historico_local/data/historico_http_paginas_0660-11_2026/26-0660-11-1651293-1-1/crudos/FORM_200__569b281444cdb94df1a389870d086f0cb5600324805ecff02af902d1f39ce5c0.html`; SHA256 `569b281444cdb94df1a389870d086f0cb5600324805ecff02af902d1f39ce5c0`.

El caso de escritorios es verificable: contrato 925, 20 piezas contratadas, 20 recibidas, Bs 3.090 unitario contratado y derivado de recepción, Bs 61.800 contratado y recibido. FORM 500 declara TOLA MAMANI PEDRO y recepción definitiva 20/04/2023; la moneda Bolivianos está documentada en FORM 200. La unidad PIEZA permanece en contratación. No se copia como dato literal de recepción.

Su DBC original DOCX, tabla 9 fila 2, pide madera roble, largo 1,20 m, fondo 0,65 m, alto 0,80 m y tablero de 19 mm. Se cotejó esa fila original; el segmentador no devuelve bloques. La sección se conserva y requiere revisión humana para una asociación técnica estructurada. No se presentan esas dimensiones como características comprobadas.

El equipo de computación incorpora requisitos respaldados por DBC; “Marca: especificar” permanece desconocido. Los casos de varios proveedores, cantidades discrepantes, unidades diferentes y descripciones genéricas requieren revisión. Se conserva contexto contractual sin atribuir proveedores a filas que no lo documentan. FORM 500 frecuentemente carece de unidad; no se crean conversiones. Los conflictos de unidad DBC se registran incluso para unidades no normalizadas.

Unidades diferentes verificadas en los candidatos del CUCE `22-0660-10-1232026-1-1`:
FORM 200 describe clips, presentación caja de 100 unidades, con unidad `Caja`,
mientras un bloque DBC candidato declara `Pieza`. La arista permanece ambigua;
no se convierte caja en pieza ni se traslada el atributo. También `PZAS.` frente
a `Unidades` puede abstenerse por alias no cubierto: no se declara incompatibilidad
comercial demostrada solo porque la normalización sea incompleta.

## Validación y reproducibilidad

- 49 pruebas automatizadas: todas satisfactorias, incluida regresión 2024 y casos reales nuevos; prueba de red bloqueada en los conjuntos que procesan el corpus histórico.
- Cotejo independiente HTML: 2.070 observaciones, 23.484 celdas, cero diferencias de contenido tras normalizar espacios de maquetación. No mide recall de tablas desconocidas.
- SHA256 y tamaño de originales verificados antes de parsear; fuentes y manifiestos seleccionados comprobados sin cambios al finalizar. Procedencia y hashes de código en `procedencia.json`.
- SQLite con integridad y claves foráneas verificadas. Cada observación pertenece exactamente a una ficha, sin eliminar las observaciones separadas.
- Regresión 0660-10/2024: 348 observaciones; 54 bloques DBC, 198 atributos y vínculos históricos 51 confirmados/3 ambiguos. Los tests anteriores de generación y repetibilidad siguen pasando.
- No existe todavía evaluación independiente de precisión comercial, exhaustividad técnica ni equivalencia de productos.

Se compararon las corridas 04 y 05: los 10 JSON/JSONL generados son idénticos byte por byte y las filas de las tres tablas SQLite son idénticas. Las 724 fuentes/manifiestos/Markdown seleccionados conservan sus hashes. Las 194 observaciones prioritarias de 2024 conservan IDs y descripciones frente a la SQLite de referencia. Evidencia local: `validacion_entrega.json`.

## Próxima tarea concreta

Preparar una referencia humana de asociación contratación/recepción con casos de contrato compartido: empezar por `25-0660-11-1517374-1-1`, registrar pares positivos/negativos/ambiguos y su evidencia de proveedor, descripción, cantidad, unidad y contrato. Después ajustar la resolución para recuperar pares inequívocos dentro de documentos con varios ítems sin usar solo el número de ítem. Aceptación: aumentar cobertura en esa referencia sin fusionar negativos ni repartir montos entre proveedores; conservar regresión y trazabilidad.

Luego ampliar y validar el layout DBC de escritorios de `23-0660-11-1314047-1-1`, y medir atributos/operadores contra filas originales. Las 17 filas FORM 170 permanecen como deuda no bloqueante; no se han usado para enriquecer ni para confirmar adquisiciones. No se implementaron las etapas 4–6, dashboard o Supabase.
