# Asociación de recepción y contratación por descripción

La v2 vincula observaciones de FORM 500 con observaciones de FORM 200 o 220
del mismo CUCE por igualdad de descripción normalizada. La normalización
aplica el criterio existente de espacios, acentos y caja. La confirmación
requiere una asociación 1:1 entre candidatas elegibles. El número de ítem,
el contrato, las cantidades y la unidad se registran como evidencia. El
número de ítem puede cambiar entre formularios.

FORM 200 conserva el contrato de la fila y deriva el proveedor si una única
fila del contexto coincide por número de documento. FORM 220 conserva el
proveedor de la fila y deriva el contrato si una única fila contextual
coincide por nombre normalizado. La evidencia derivada conserva el documento,
el hash, la tabla, la fila y las celdas de contexto. Si varias filas comparten
el mismo contrato, el proveedor queda sin asignar por ese contexto.

Un conflicto explícito de proveedor o fecha de firma descarta la arista.
Un contexto contractual ambiguo o varias candidatas elegibles que compiten
por una observación requieren revisión. Las alternativas históricas por
contrato literal con descripción distinta se conservan como descartadas
con su motivo.

## Resultados en el corpus local

| Aristas de recepción y contratación | v1 | v2 previa | v2 por descripción |
|---|---:|---:|---:|
| Confirmadas | 63 | 560 | 934 |
| Ambiguas | 8.998 | 55 | 55 |
| Descartadas | 0 | 8.446 | 8.072 |

Las 1.016 recepciones tienen una coincidencia de descripción 1:1 dentro del
CUCE. De esos pares, 934 se confirman, 55 quedan ambiguos por múltiples
filas de contexto contractual y 27 se descartan por conflicto de fecha de
firma. Las otras 8.045 aristas descartadas son alternativas históricas por
contrato con descripción distinta. La corrida intermedia por número de ítem
había confirmado 245 pares y dejado 771 en revisión. En el caso curado
`25-0660-11-1517374-1-1`, los 19 pares vuelven a confirmarse por descripción.

Las corridas de referencia son `adquisiciones_v1_20261109_04` y
`adquisiciones_v2_20261109_01`. La nueva salida se escribe en
`procesamiento/historico/data/adquisiciones_v2_desc_01/`. Su `resumen.json`
incluye la comparación con ambas corridas y la causa dominante de las
aristas ambiguas.

## Verificación

Pasaron los 75 tests del histórico, incluidos los tres casos curados de
asociación. Los hashes de `test_acquisitions.py` y
`acquisiciones_referencia_v2.json` son idénticos antes y después del cambio.
Las 9.061 aristas de recepción y contratación de v1 se reprodujeron
exactamente con sus reglas originales.

| Etapa | Observaciones en ambas corridas | Suma del importe documentado |
|---|---:|---:|
| Contratación | 1.051 | 18.271.327,16 de importe total contratado |
| Recepción | 1.016 | 15.750.444,48 de monto real ejecutado |
| No contratación | 3 | — |

Las 2.070 observaciones son idénticas byte por byte a v1 y cada una aparece
en una sola ficha. Las sumas por etapa coinciden tanto en las observaciones
como en las fichas. La agrupación pasa de 2.007 a 1.136 fichas. Las aristas
DBC son idénticas a v1. Los 11 archivos de salida, incluido SQLite,
tienen SHA-256 idénticos entre las dos ejecuciones.
