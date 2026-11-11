# FORM 220 — Etapa 1: asociación interna con el contexto contractual

Entrega local de 2026-11-09 en main. **Solo Etapa 1 implementada. Etapa 2 (FORM 220 ↔ FORM 500) no implementada ni conectada al nuevo resultado; pendiente de revisión y autorización posterior.**

## Resultado demostrable

Se asociaron los 386 bienes contratados de los 106 FORM 220 regulares con una fila contextual única del mismo documento. Los 20 formularios con varios proveedores están incluidas. Las 23 referencias compuestas conservan incertidumbre sobre la orden individual; no se desglosan. Las 389 observaciones originales de FORM 220 (386 contratadas y tres no contratadas), con sus IDs y campos, son exactamente iguales a las conservadas en v2. No se insertó un número contractual en sus campos originales.

| Medida | Resultado |
|---|---:|
| Documentos regulares procesados | 106 |
| Formularios con varios proveedores | 20 |
| Filas contextuales originales | 148 |
| Bienes contratados asociados a contexto único | 386 |
| Ambigüedad de contexto en el corpus actual | 0 |
| Referencia contextual literal simple | 363 |
| Orden individual indeterminada por referencia compuesta | 23 |
| Bienes no contratados preservados, sin asociación de adquisición | 3 |
| Documento publicado ERRÓNEO excluido | 1 |
| FORM 220 regular anunciado ausente | 2 CUCE |
| Sin FORM 220 de ninguna clase | 1 de esos 2 CUCE |

La cobertura contextual 386/386 describe este corpus aprobado; no certifica precisión global ni autoriza asociación con recepción. Un contexto confirmado es una fila documental, no una nueva compra ni una identidad canónica de producto. Las 148 filas contextuales tampoco son un conteo seguro de órdenes individuales porque existen referencias compuestas.

## Implementación y reutilización

Nuevo módulo independiente: `procesamiento/historico/form220_context.py`. Reutiliza `parser.parse_document`, sus observaciones y `contract_context`, normalización/IDs del parser, serialización y escritura atómica de `pipeline`, y cotejo de `review.SourceRows`/`source_fidelity`. No cambia `parser.py`, `linking.py`, `acquisitions.py`, comandos previos o algoritmos de canonicalización.

La firma B01 se localiza por conjunto de encabezados, cantidad de celdas y spans admisibles. No se exige que el contexto sea T11 ni que los bienes estén en T12: las pruebas desplazan tablas, mueven la tabla contractual y reordenan la columna de proveedor. Se admite la tabla comercial reconocida, sin depender del número global de tablas del documento. Si no hay una sola tabla identificable para cada rol o aparece una cabecera desconocida, se abstiene con `ESQUEMA_NO_ADMITIDO`.

Para un bien de etapa `contratacion`, se compara su proveedor explícito con el nombre/razón social del contexto en el mismo documento. Se normalizan solo espacios, caja y acentos, conservando el literal. Cero candidatos produce `SIN_CONTEXTO`; varios, `AMBIGUA`; uno, `CONFIRMADA`. No se elige proveedor por número de ítem, importe global, descripción similar o datos de otro CUCE/documento. Varios bienes pueden referir la misma fila contextual sin duplicar sus observaciones ni repartir el importe global.

Los metadatos y el título del HTML se comprueban para excluir documentos publicados ERRÓNEO. Se distinguen ausencia de entrada, versión sin validación, archivo faltante, HTML inconsistente y estructura no admitida. Las 107 versiones disponibles se verifican por tamaño y SHA256 antes de procesar o excluir. Ningún documento ausente se sustituye por el erróneo.

## Esquema de la asociación derivada

| Campo | Contenido y límite |
|---|---|
| `observation_id`, `document_id`, `cuce` | Identidad estable del original, sin mezclar documentos |
| `item_reference` | Documento/hash, raíz/ruta del original, tabla y fila del bien |
| `item_contract_number_original` | Siempre null en los bienes B01 actuales; no se agrega un campo contractual a la observación original |
| `supplier_evidence.item_cell` | Literal, encabezado, columna y referencia a la celda proveedora del bien |
| `context_status` | CONFIRMADA / AMBIGUA / SIN_CONTEXTO / NO_ELEGIBLE; describe la fila contextual |
| `context_candidates` | Todas las filas del proveedor candidatas, sus IDs y las nueve celdas originales con documento/tabla/fila/columna |
| `contextual_contract_reference` | Literal del número contextual, origen DERIVADA_DE_FILA_CONTEXTUAL y referencia exacta a su celda |
| `individual_order_status`, `individual_order_uncertain` | Distinguen referencia simple de orden indeterminada; nunca desglosan una referencia compuesta |

No se crea un identificador comercial global ni un array de órdenes desglosadas. Una referencia simple documentada tampoco certifica por sí sola firma o entrega física. Los precios, cantidades, unidades y montos originales siguen en `observaciones.jsonl`; la asociación no los cambia ni los suma.

## Métricas por entidad y gestión

| Entidad | Gestión | Documentos | Bienes asociados | Documentos multiproveedor | Bienes con referencia compuesta |
|---|---|---:|---:|---:|---:|
| 0660-10 | 2022 | 14 | 73 | 4 | 2 |
| 0660-10 | 2023 | 19 | 88 | 4 | 19 |
| 0660-10 | 2024 | 12 | 46 | 1 | 2 |
| 0660-11 | 2023 | 27 | 68 | 4 | 0 |
| 0660-11 | 2024 | 16 | 50 | 1 | 0 |
| 0660-11 | 2025 | 7 | 35 | 4 | 0 |
| 0660-11 | 2026 | 11 | 26 | 2 | 0 |

Las dos ausencias regulares son `23-0660-11-1333011-1-1` (solo existe un Formulario 220 publicado ERRÓNEO) y `23-0660-11-1333799-1-1` (no hay FORM 220 local). La primera queda también en el inventario de exclusión: son estados distintos dentro de un mismo proceso, no documentos adicionales utilizables. Los manifiestos locales no prueban ausencia en SICOES ni completitud anual.

## Referencias compuestas: contexto cierto, orden individual incierta

| CUCE | Literal contextual conservado | Bienes | Resultado |
|---|---|---:|---|
| 22-0660-10-1199776-1-1 | 009-0010 | 2 | Contexto confirmado; orden individual indeterminada |
| 23-0660-10-1334904-1-1 | 57 - 61 | 19 | Contexto confirmado; orden individual indeterminada |
| 24-0660-10-1415622-1-1 | 19-29 | 2 | Contexto confirmado; orden individual indeterminada |

Cada asociación conserva el texto completo original y su celda fuente. No se transforma un guion en rango ni se asigna una suborden por posición, cantidad o suma. No se cuentan dos compras a partir de una referencia compuesta.

## Ejemplos reales verificables

Las posiciones siguientes son físicas y desde 1; se publican para auditar el resultado, no como constantes de detección.

### 22-0660-10-1199746-1-1

[HTML original](</Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data/historico_http_paginas_0660-10_2022/22-0660-10-1199746-1-1/crudos/FORM_220__fdb6a1e909575266c852e7b8411ff9b8a9a31bc3c82d5a9c54681b65b6bf66f0.html>)

Bien: Memoria ram dinámica (dram) MEMORIA RAM 16 GB PC3. Proveedor literal: NEXTDATA LTDA. Celda del proveedor: T12 F4 C7.
Contexto: T11 F2; número en C5: `019`. Estado: CONFIRMADA; orden individual: REFERENCIA_SIMPLE_DOCUMENTADA.
Observación `1b6ca8c8244b53068e908044f8e0d3ec018281c06b6320f8220ace28b53856df`; SHA256 `fdb6a1e909575266c852e7b8411ff9b8a9a31bc3c82d5a9c54681b65b6bf66f0`.

### 23-0660-11-1388835-1-1

[HTML original](</Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data/historico_http_paginas_0660-11_2023/23-0660-11-1388835-1-1/crudos/FORM_220__006fef3a976bbee5dc67c4d93f8d56c69b400157270de4f56fc88da32305ed98.html>)

Bien: Sujetadores de pinza BROCHE PARA EXPEDIENTE; LONGITUD 8 CMS; TIPO NEPACO (ACOFASTER). Proveedor literal: RIOJA SANCHEZ HENRY FREDDY. Celda del proveedor: T12 F4 C7.
Contexto: T11 F7; número en C5: `3477`. Estado: CONFIRMADA; orden individual: REFERENCIA_SIMPLE_DOCUMENTADA.
Observación `6fca830cd6029781986061af18637858f197ab26c8a2d01240bad26795baa91f`; SHA256 `006fef3a976bbee5dc67c4d93f8d56c69b400157270de4f56fc88da32305ed98`.

### 22-0660-10-1199776-1-1

[HTML original](</Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data/historico_http_paginas_0660-10_2022/22-0660-10-1199776-1-1/crudos/FORM_220__6b664de70ee4d6f18c8c6134188f05da48b0eaedb61b4434e4fbf55b14570dde.html>)

Bien: Temporizadores de reloj RELOJ BIOMETRICO FACIAL. Proveedor literal: NEGRETTY PLAZA GUIDO. Celda del proveedor: T12 F4 C7.
Contexto: T11 F2; número en C5: `009-0010`. Estado: CONFIRMADA; orden individual: ORDEN_INDIVIDUAL_INDETERMINADA.
Observación `15f270cca1d0067a7e66a89acb17d7c4184031dfc05d85577e93fa221602668b`; SHA256 `6b664de70ee4d6f18c8c6134188f05da48b0eaedb61b4434e4fbf55b14570dde`.

### 23-0660-10-1334904-1-1

[HTML original](</Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data/historico_http_paginas_0660-10_2023/23-0660-10-1334904-1-1/crudos/FORM_220__2dcc06d19e438dd03d3049111c17378402fd1d530e5e87235b9dde646e49fb5b.html>)

Bien: Alcoholes o sus sustitutos ALCOHOL EN GEL; DESINFECTANTE PARA MANOS; TIPO LIQUIDO SANITIZADOR ANTIBACTERIANO; PRESENTACION 5 LT.. Proveedor literal: CONDORI AQUINO MIRIAM. Celda del proveedor: T12 F4 C7.
Contexto: T11 F2; número en C5: `57 - 61`. Estado: CONFIRMADA; orden individual: ORDEN_INDIVIDUAL_INDETERMINADA.
Observación `adacb94fa92ef8be74e3e76db439995c4448855363d512737c08561db3d92f36`; SHA256 `2dcc06d19e438dd03d3049111c17378402fd1d530e5e87235b9dde646e49fb5b`.

### 24-0660-10-1415622-1-1

[HTML original](</Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data/historico_http_paginas_0660-10_2024/24-0660-10-1415622-1-1/crudos/FORM_220__2251c225c41ca7bc73204c5ff656405ec9cdb1ba1042fc960e5ec7de70c373b5.html>)

Bien: Fusores FUSOR PARA IMPRESORA LEXMARK 421. Proveedor literal: JOSPRINTER S.R.L.. Celda del proveedor: T12 F4 C7.
Contexto: T11 F4; número en C5: `19-29`. Estado: CONFIRMADA; orden individual: ORDEN_INDIVIDUAL_INDETERMINADA.
Observación `9493c0af6567ad14444d1c11088bcd4b7da4da9caf06c02edea2f997378c03e0`; SHA256 `2251c225c41ca7bc73204c5ff656405ec9cdb1ba1042fc960e5ec7de70c373b5`.

## Pruebas y controles negativos

**21 tests nuevos satisfactorios en el entorno aislado; 75 tests satisfactorios en el conjunto completo (54 anteriores + 21 nuevos).** No se ampliaron las reglas para resolver casos de recepción. Los tests nuevos cubren:

- Los 386 bienes, 106 documentos y 20 formularios multiproveedor; ninguno se confirma por total o índice local del ítem.
- Los 23 bienes de las tres cadenas compuestas: literal preservado, null original y orden individual indeterminada.
- Observaciones exactamente iguales a las de v2: 389, incluidos tres no contratados sin enlaces de adquisición.
- Desplazamiento de tablas, movimiento de la tabla contractual y reordenación de la columna proveedora, con referencias actualizadas por posición física real.
- Dos filas contextuales del mismo proveedor, aun con órdenes diferentes: AMBIGUA, con ambas candidatas y sin número contextual elegido.
- Proveedor ausente, incompatible o duplicado en campos del ítem: abstención sin rescate por monto o número de ítem.
- Observación de otro documento/CUCE, otro formulario o etapa no contratada: NO_ELEGIBLE.
- Cabecera contractual no admitida: documento no admitido y ninguna confirmación forzada.
- Etiqueta ERRÓNEO y título HTML ERRÓNEO por separado: exclusión aun cuando el otro indicador parezca regular.
- Ausencia en manifiesto, versión no válida y archivo ausente: estados distintos; hash incorrecto y salida ya existente: rechazo sin sobrescritura.
- No mutación de los documentos/observaciones y referencias de cada número derivado a su celda original.
- El módulo de etapa 1 solo parsea FORM 220; no lee HTML de FORM 500 ni llama al vinculador v2.

Los negativos y los casos de contexto ambiguo se construyeron mediante copias en memoria o temporales de HTML reales, sin editar los originales. El corpus aprobado no contiene ambigüedad de contexto natural por proveedor: contiene los 23 casos reales de incertidumbre de orden individual. Los escenarios adversos demuestran abstención, pero no constituyen una medida independiente de precisión fuera del corpus.

Cotejo con lector HTML independiente: 389 observaciones y 3.884 celdas de bienes; 148 contextos y 1.332 celdas contractuales. Sin diferencias de contenido al normalizar solo espaciado de maquetación. La regresión anterior de 2024 sigue satisfactoria: 348 observaciones, 54 bloques DBC, 198 atributos y relaciones históricas 51 confirmadas / 3 ambiguas.

## Aislamiento, conservación y repetibilidad

Se copió el paquete de procesamiento, sin los datos, a `/private/tmp/sicoes_form220_etapa1_20261109_01/workspace/`. La ejecución nueva y sus 21 pruebas se realizaron desde esa copia, con fuentes locales explícitas en lectura y escritura únicamente en salidas nuevas. Los tests bloquean conexiones de red. Se usó el entorno Python local existente, sin instalar dependencias ni crear otra arquitectura.

Las dos corridas aisladas produjeron los ocho artefactos base idénticos byte por byte. Se cotejaron también los bytes de módulo/parser/pipeline/review entre la copia ejecutada y los archivos revisables del repositorio. Los originales y las salidas v1/v2 se comprobaron por hashes; se preservaron 617 archivos funcionales existentes, incluidos archivos rastreados de Graphify. La verificación excluye metadatos `.DS_Store` del sistema, sin significado de corpus.

Se agregan solo un módulo, sus tests y este documento. No se modifica ni despliega producción; no se cambia dashboard, Supabase, Graphify, scraper, parser, vinculadores previos o canonicalización. No se escribió ninguna SQLite. No hubo APIs, LLM, descargas, commits ni push.

## Salidas para revisión

Raíz de ejecución y controles: `/private/tmp/sicoes_form220_etapa1_20261109_01/`. Salida aceptada: `salida_01/`; repetición: `salida_repeticion_01/`.

- `revision_asociacion_interna.csv`: vista de los 386 bienes con descripción, proveedor, cantidad/unidad/precio/importe originales, null contractual original, literal contextual, incertidumbre y referencias físicas.
- `asociaciones_internas.jsonl` / `.csv`: asociación completa con celdas, candidatos y procedencia.
- `observaciones.jsonl` / `documentos.jsonl`: observaciones originales y filas/contextos retenidos.
- `inventario.jsonl` / `procesos.jsonl`: procesados, exclusiones y ausencias sin sustituir unas por otras.
- `ejemplos_verificables.json`: cinco ejemplos completos, incluidas las tres referencias compuestas.
- `resumen.json` / `procedencia.json`: métricas y hashes de los 301 manifiestos/HTML leídos por el módulo.
- `VALIDACION_ENTREGA.json`, `pruebas_aisladas.txt`, `pruebas_completas.txt`: conservación, repetibilidad y resultados de tests.

Al abrir el CSV, importar las referencias contractuales como texto para conservar ceros iniciales; el JSONL conserva siempre su literal y null original.

Para repetir sobre la copia aislada, con una salida nueva y desde su workspace:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/fabriziocuellar/Sicoes-Brain/scraper/venv/bin/python -m procesamiento.historico.form220_context --base /Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data --output /private/tmp/sicoes_form220_etapa1_NUEVA
```

La etapa 1 queda entregada para revisión. La siguiente decisión es aprobar o corregir esta asociación interna y sus estados de incertidumbre. **No se ha iniciado la etapa 2 ni se utilizará esta salida para confirmar vínculos FORM 220–FORM 500 antes de esa autorización.**
