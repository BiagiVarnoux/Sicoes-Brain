# Diagnóstico de causas raíz de la auditoría de adquisiciones v2

Fecha: 2026-11-09. Repositorio principal, rama main. Diagnóstico documental asistido, sin modificación de reglas, observaciones, estados v1/v2 ni producción.

## Conclusión y alcance

Los 38 casos indeterminados de la revisión recibida tienen correspondencia documental única en los HTML locales cuando se incorpora el contexto adecuado: 16 casos de FORM 220 sin número contractual en la tabla de bienes, 20 de FORM 200 con número compartido entre proveedores y dos con orden modificatoria de plazo documentada en FORM 250. Esta conclusión identifica registros de un mismo ciclo de adquisición; no certifica prestaciones del producto, entrega física ni precisión global del algoritmo.

Se revisaron las ocho hipótesis descartadas indeterminadas y las diez observaciones sin vínculo (18 casos), los 20 ambiguos y los 12 descartes incompatibles como controles negativos. Son 50 parejas de 31 CUCE; las 38 inicialmente indeterminadas corresponden a 21 CUCE. Las otras 50 nuevas confirmadas no se sometieron aquí a una segunda auditoría de precisión. No se combinan las 100 etiquetas para calcular exactitud o recall global.

Las entradas recibidas desde Downloads se preservaron como copias exactas, con hashes. Las 100 filas conservan los datos exportados: se comprobó que solo difieren del CSV inicial las tres columnas de revisión. Las etiquetas siguen siendo revisión asistida, pendiente de aprobación humana, no ground truth certificado. El diagnóstico añade conclusiones separadas y no sustituye esas etiquetas.

| Grupo del CSV | Casos examinados | Resultado del cotejo original |
|---|---:|---|
| DESCARTADA / INDETERMINADA | 8 | 7 vinculables por contexto FORM 220; 1 por FORM 250 |
| SIN_VINCULO | 10 | 9 vinculables por contexto FORM 220; 1 por FORM 250 |
| AMBIGUA | 20 | Proveedor corroborado por ítem en FORM 170, contexto FORM 200 y FORM 500 |
| DESCARTADA / NO_RESPALDADA | 12 | Mantener descarte de las parejas incompatibles |

## 1. FORM 220: ausencia estructural, no número perdido

En los 16 casos examinados, la tabla 12 de FORM 220 contiene descripción, unidad, proveedor contratado, precio contratado, cantidad e importe, pero su encabezado no contiene una columna de contrato. El número sí existe en la tabla 11 de contratos/proveedores, junto con proveedor, fecha de firma, monto global y recepción estimada. No es un fallo de lectura de una celda contractual ni prueba de que el proceso carezca de contrato. La causa del descarte v2 es exigir igualdad de número en cada fila: `match_receipt` obtiene null en FORM 220 y `supplier_context` no encuentra contexto porque comienza buscando ese mismo número ausente.

Para cada caso se contrastó descripción literal, cantidad solicitada/contratada/recepcionada e importe; se comprobó que no hay otra fila con esa combinación en ninguna de las dos tablas completas. El proveedor explícito de FORM 220 coincide con FORM 500 y selecciona una sola fila de contexto en FORM 220. En esa fila coinciden número de contrato, firma y fecha estimada con FORM 500. El precio contratado por cantidad concilia exactamente con el importe. La unidad que no figura en FORM 500 permanece desconocida allí: no se crea una igualdad de unidades ni una conversión de presentación.

No hay que rellenar el número como si estuviera documentado en la fila del bien. La eventual referencia derivada debe conservar el origen contextual y el motivo `NO_PREVISTO_EN_ESQUEMA_DE_TABLA`. Tampoco debe usarse el precio del proveedor preseleccionado en lugar del precio contratado.

Los casos de RAM muestran por qué importa usar proveedor y fecha además de CUCE: `24-0660-10-1415622-1-1` tiene dos órdenes, `20` de 14/03/2024 (ROJAS PATTY ANDRES) y `28` de 04/04/2024 (ADRIAN MAYORGA ALFREDO). DDR3, 40 piezas, Bs 9.080, corresponde a la primera; DDR4, 31 piezas, Bs 8.370, a la segunda. No se hereda una orden única a todos los ítems del CUCE.

### Los 16 casos y sus referencias

Las referencias T/F/C son índices físicos de tabla/fila/columna, desde 1. Los paths y hashes completos se conservan en el anexo de evidencia.

| Caso | CUCE | FORM 220 T/F | FORM 500 T/F | Contexto T/F | Orden y firma | Proveedor | Cantidad / importe |
|---|---|---|---|---|---|---|---|
| AUD-V2-071 | 22-0660-10-1248345-1-1 | 12/10 | 5/14 | 11/2 | 90 · 31/08/2022 | CHALCO AGUILAR DE VELASCO ROSA | 180 / 4032 |
| AUD-V2-074 | 23-0660-10-1322493-1-1 | 12/5 | 5/4 | 11/2 | 35/2023 · 18/04/2023 | NEGRETTY PLAZA GUIDO | 1 / 6654 |
| AUD-V2-077 | 24-0660-10-1415622-1-1 | 12/5 | 5/5 | 11/3 | 28 · 04/04/2024 | ADRIAN MAYORGA ALFREDO | 31 / 8370 |
| AUD-V2-080 | 23-0660-11-1383883-1-1 | 12/4 | 5/3 | 11/2 | 3298 · 24/11/2023 | RIOJA SANCHEZ HENRY FREDDY | 930 / 28365 |
| AUD-V2-083 | 24-0660-11-1488863-1-1 | 12/4 | 5/3 | 11/2 | 2867 · 01/11/2024 | TECNODIGITAL SRL | 100 / 26000 |
| AUD-V2-086 | 25-0660-11-1610985-1-1 | 12/4 | 5/3 | 11/2 | 2680 · 20/11/2025 | CUELLAR SALAZAR CARLOS FABRIZIO | 149 / 26671 |
| AUD-V2-089 | 26-0660-11-1661273-1-1 | 12/4 | 5/3 | 11/2 | 1227/2026 · 26/05/2026 | ARIAS FERNANDEZ OSCAR MAURICIO | 28 / 29680 |
| AUD-V2-091 | 22-0660-10-1249848-1-1 | 12/4 | 5/3 | 11/2 | 94 · 23/08/2022 | QUINTANILLA FAJARDO MARISEL | 17 / 34850 |
| AUD-V2-092 | 23-0660-10-1309109-1-1 | 12/10 | 5/9 | 11/3 | 013/2023 · 09/03/2023 | PARRA CARVAJAL NARDA | 350 / 5250 |
| AUD-V2-093 | 24-0660-10-1415622-1-1 | 12/6 | 5/4 | 11/2 | 20 · 14/03/2024 | ROJAS PATTY ANDRES | 40 / 9080 |
| AUD-V2-094 | 24-0660-10-1464208-1-1 | 12/4 | 5/4 | 11/2 | 73 · 15/08/2024 | FERNANDEZ CALLE IRMA | 13 / 17550 |
| AUD-V2-095 | 23-0660-11-1366638-1-1 | 12/4 | 5/3 | 11/2 | 2503 · 14/09/2023 | FLORES CABEZAS ROBERTO CARLOS | 14 / 32200 |
| AUD-V2-096 | 24-0660-11-1422563-1-1 | 12/4 | 5/3 | 11/2 | 906 · 05/04/2024 | AKAMINE DE DICK ROSIO ELIZABETH | 200 / 34800 |
| AUD-V2-097 | 25-0660-11-1599911-1-1 | 12/4 | 5/3 | 11/2 | 2343 · 16/10/2025 | VERA GUMUCIO JOSE CARLOS | 25 / 42500 |
| AUD-V2-098 | 25-0660-11-1576770-1-1 | 12/4 | 5/3 | 11/2 | 1840 · 31/07/2025 | BLACUTT VILLEGAS EMILIO FREDDY | 143 / 44330 |
| AUD-V2-099 | 26-0660-11-1645249-1-1 | 12/5 | 5/4 | 11/2 | 777/2026 · 06/04/2026 | FERNANDEZ ESPINOZA JOSE ANDRES | 10 / 12380 |

Los datos anteriores caracterizan los 16 casos de 15 CUCE revisados; no acreditan que cualquier versión histórica de FORM 220 tenga exactamente el mismo diseño ni que todos los contextos sean únicos.

## 2. FORM 200: número compartido no significa proveedor indeterminable

En los cinco CUCE de los 20 casos ambiguos, distintas filas de contratos/proveedores contienen el mismo número. La política v2 considera ambiguo el contexto al buscar solo por ese número, antes de contrastar el proveedor. Sin embargo, FORM 500 documenta el proveedor por recepción; la tabla contractual de FORM 200 contiene una sola fila para ese proveedor, con número, firma y recepción estimada coincidentes. Se cotejó además el FORM 170 original: en los 20 casos hay una sola fila con la misma descripción, cantidad, precio unitario e importe adjudicados, y su proveedor coincide con la recepción y el contexto contractual.

FORM 170 aporta corroboración separada del propio FORM 500; no se infiere el proveedor contratado únicamente desde la recepción. Adjudicación no equivale a contratación o recepción: se comprueba coherencia entre las tres etapas y se preservan sus roles. No fue necesario perfeccionar el parser de FORM 170 ni recuperar sus 17 filas omitidas; las filas utilizadas aquí ya están presentes y legibles en los originales. Este hallazgo demuestra utilidad complementaria en estos casos, no vuelve bloqueante aquella deuda técnica.

### Proveedor resuelto y referencia complementaria por caso

| Caso | CUCE | FORM 200 T/F | FORM 500 T/F | Contexto FORM 200 T/F | FORM 170 T/F | Proveedor corroborado |
|---|---|---|---|---|---|---|
| AUD-V2-051 | 22-0660-10-1211325-1-1 | 11/7 | 5/13 | 10/2 | 13/8 | CUEVAS QUISPE NANCY ABIGAIL |
| AUD-V2-052 | 22-0660-10-1211325-1-1 | 11/11 | 5/7 | 10/2 | 13/9 | CUEVAS QUISPE NANCY ABIGAIL |
| AUD-V2-053 | 22-0660-10-1211325-1-1 | 11/13 | 5/14 | 10/4 | 13/12 | TECNODIGITAL SRL |
| AUD-V2-054 | 22-0660-10-1211325-1-1 | 11/9 | 5/11 | 10/4 | 13/14 | TECNODIGITAL SRL |
| AUD-V2-055 | 22-0660-10-1211325-1-1 | 11/8 | 5/3 | 10/2 | 13/6 | CUEVAS QUISPE NANCY ABIGAIL |
| AUD-V2-056 | 22-0660-10-1211325-1-1 | 11/10 | 5/5 | 10/2 | 13/4 | CUEVAS QUISPE NANCY ABIGAIL |
| AUD-V2-057 | 22-0660-10-1211325-1-1 | 11/14 | 5/8 | 10/4 | 13/13 | TECNODIGITAL SRL |
| AUD-V2-058 | 22-0660-10-1211325-1-1 | 11/6 | 5/4 | 10/2 | 13/10 | CUEVAS QUISPE NANCY ABIGAIL |
| AUD-V2-059 | 23-0660-10-1327723-1-1 | 11/4 | 5/6 | 10/3 | 13/4 | BETANCOURT NAVAS MAURICIO EDMUNDO |
| AUD-V2-060 | 23-0660-10-1329122-1-1 | 11/27 | 5/24 | 10/3 | 13/4 | RILUMAR PVS LTDA. |
| AUD-V2-061 | 23-0660-10-1329122-1-1 | 11/10 | 5/5 | 10/3 | 13/17 | RILUMAR PVS LTDA. |
| AUD-V2-062 | 23-0660-10-1329122-1-1 | 11/25 | 5/15 | 10/4 | 13/36 | INSUVIRTUAL S.R.L. |
| AUD-V2-063 | 23-0660-10-1327723-1-1 | 11/5 | 5/4 | 10/2 | 13/7 | NEGRETTY PLAZA GUIDO |
| AUD-V2-064 | 23-0660-10-1329122-1-1 | 11/16 | 5/11 | 10/2 | 13/35 | JORGE GONZALES EDWIN AMILCAR |
| AUD-V2-065 | 23-0660-10-1329122-1-1 | 11/26 | 5/23 | 10/3 | 13/22 | RILUMAR PVS LTDA. |
| AUD-V2-066 | 24-0660-10-1411332-1-1 | 11/3 | 5/4 | 10/3 | 13/4 | PAZ SEVERICHE RICHARD |
| AUD-V2-067 | 24-0660-10-1411332-1-1 | 11/4 | 5/3 | 10/2 | 13/5 | JOSPRINTER S.R.L. |
| AUD-V2-068 | 24-0660-10-1412564-2-2 | 11/5 | 5/5 | 10/2 | 13/5 | AKAMINE DE DICK ROSIO ELIZABETH |
| AUD-V2-069 | 24-0660-10-1412564-2-2 | 11/4 | 5/4 | 10/3 | 13/4 | PAZ SEVERICHE RICHARD |
| AUD-V2-070 | 24-0660-10-1412564-2-2 | 11/3 | 5/3 | 10/2 | 13/6 | AKAMINE DE DICK ROSIO ELIZABETH |

### Conciliación de las tablas completas por proveedor

Se sumaron exclusivamente importes de recepción por proveedor dentro de cada documento para cotejarlos con el monto contractual global; no se añadieron montos de contratación a recepción ni se generó demanda nueva. En los 21 CUCE con casos indeterminados los totales por proveedor coinciden con el contexto contractual. La conciliación es un control adicional, no una regla suficiente para asignar ítems por coincidencia de sumas.

| CUCE ambiguo | Proveedor | Contexto contratado = recepción completa |
|---|---|---:|
| 22-0660-10-1211325-1-1 | CUEVAS QUISPE NANCY ABIGAIL | 88915 |
| 22-0660-10-1211325-1-1 | PAZ SEVERICHE RICHARD | 107955 |
| 22-0660-10-1211325-1-1 | TECNODIGITAL SRL | 63820 |
| 23-0660-10-1327723-1-1 | NEGRETTY PLAZA GUIDO | 102773.4 |
| 23-0660-10-1327723-1-1 | BETANCOURT NAVAS MAURICIO EDMUNDO | 186754.2 |
| 23-0660-10-1329122-1-1 | JORGE GONZALES EDWIN AMILCAR | 24081 |
| 23-0660-10-1329122-1-1 | RILUMAR PVS LTDA. | 42850 |
| 23-0660-10-1329122-1-1 | INSUVIRTUAL S.R.L. | 26997 |
| 24-0660-10-1411332-1-1 | JOSPRINTER S.R.L. | 67500 |
| 24-0660-10-1411332-1-1 | PAZ SEVERICHE RICHARD | 107550 |
| 24-0660-10-1412564-2-2 | AKAMINE DE DICK ROSIO ELIZABETH | 53300 |
| 24-0660-10-1412564-2-2 | PAZ SEVERICHE RICHARD | 292800 |

## 3. Las llantas: un modificatorio explica los dos números y fechas

Los casos AUD-V2-090 (185/70 R13) y AUD-V2-100 (205/70 R15), CUCE `26-0660-11-1658002-1-1`, no son un simple contrato faltante. FORM 200 tabla 10 fila 2 y tabla 11 documentan la orden principal `1210`, firmada el 25/05/2026, proveedor BARRANCOS QUIROZ FARITH, total Bs 39.400 y recepción estimada 08/06/2026. FORM 500 tabla 8 remite a `1353/2026`, firma 08/06/2026 y recepción estimada/definitiva 23/06/2026.

El FORM 250 HTML local conecta explícitamente ambas referencias:

| Referencia FORM 250 | Evidencia literal relevante |
|---|---|
| T5 F4 C4 | BARRANCOS QUIROZ FARITH |
| T7 F2 C1/C3/C4/C6 | Principal 1210; firma 25/05/2026; monto 39400; recepción 08/06/2026 |
| T9 F2 C2/C4 | Contrato/Orden de compra modificatorio; alcance Plazo |
| T10 F2 C1/C3/C4/C5 | Modificatorio 1353/2026; firma 08/06/2026; monto registrado 0; recepción 23/06/2026 |
| T11 F3 | No existen registros en detalle de bienes objeto de modificación |
| T12 F1 C3/C5 | Monto consolidado 39400; recepción vigente 23/06/2026 |

Es una cadena principal–modificatorio de plazo, sin cambio de monto documentado. El cero es monto registrado del modificatorio, no precio de las llantas ni recepción gratuita. El monto consolidado no es una adquisición adicional. Para ambos ítems coinciden descripción, cantidad, precio unitario e importe en contratación y recepción; la prueba decisiva para el número y fecha es FORM 250. Las diez líneas de recepción suman Bs 39.400, igual que la orden principal y el monto vigente.

| Caso | FORM 200 T11 fila | FORM 500 T8 fila | Cantidad | Precio unitario | Importe | Conclusión |
|---|---:|---:|---:|---:|---:|---|
| AUD-V2-090 | 7 | 12 | 4 | 800 | 3200 | Vinculable por cadena 1210 → 1353/2026 |
| AUD-V2-100 | 11 | 7 | 8 | 700 | 5600 | Vinculable por cadena 1210 → 1353/2026 |

Por tanto, no corresponde levantar cualquier conflicto contractual/temporal por coincidencia comercial. En estos dos casos se dispone de un enlace explícito que justifica la diferencia. Sin documento modificatorio o cuando cambien bienes, montos o cantidades, el caso debe seguir pendiente y no beneficiarse de esta conclusión.

### Limitación de extracción adicional detectada, sin corregir

Este FORM 500 usa un diseño de 13 columnas y el encabezado `Monto ejecutado` (T8 F2 C10), frente a `Monto real ejecutado` en el diseño anterior. El parser actual reconoce el segundo, pero deja el primero como `column_10`; no se pierde la celda original, pero falta su semántica normalizada. Además, C8 `Cantidad recepcionada` y C13 `Cantidad no recepcionada` reciben ambas el nombre `cantidad_reportada_recepcion` en el parser actual. Al consultar un campo único, esa duplicación deja el valor sin resolver; no corresponde interpretar el cero de C13 como cantidad recibida. Para las dos llantas, C8 declara 4 y 8, respectivamente, mientras C13 declara cero no recibido. Es otra limitación semántica del diseño nuevo, conservada sin corregir. El formulario tampoco tiene una columna explícita de estado de recepción: sí declara cantidad recepcionada y no recepcionada. Por eso este diagnóstico coteja 3200 y 5600 directamente con los HTML y no supone que un campo exportado vacío significa ausencia en el original. No se inventa un estado para habilitar precios derivados. El precio unitario recepcionado está explícito en C9.

## 4. Los doce pares incompatibles mantienen el descarte

No se cambió su estado. Compartir contrato, categoría, proveedor o un monto no elimina incompatibilidades de referencia, formato o función. Se cotejaron las descripciones originales de ambos formularios, con estos controles negativos:

| Caso | CUCE | Recepción | Contratación |
|---|---|---|---|
| AUD-V2-072 | 22-0660-10-1232026-1-1 | Sujetadores auto adhesivosBanderillas Post-it; Medida 76 x 76 Mms.; Color Amarillo; Presentación Paquete de un Taco x 100 Hojas | Sujetadores auto adhesivosBanderillas Post-it; Medida Estándar; Color Surtido; Presentación Paquete de 5 Colores; Tipo Flecha |
| AUD-V2-073 | 22-0660-10-1199037-2-2 | Gavetas organizadoras para el escritorioGABETERO DE CUATRO CAJONES O GABETAS | Gavetas organizadoras para el escritorioANAQUEL METALICO REFORSADO |
| AUD-V2-075 | 23-0660-10-1329122-1-1 | Accesorios para estampación de cauchoTINTA PARA TAMPO; COLOR AZUL; ENVASE FRASCO; CONTENIDO 30ML. | Cinta de impresoraCINTA PARA IMPRESORA: EPSON LQ-590 TIPO CARRO CORTO. |
| AUD-V2-076 | 23-0660-10-1323309-1-1 | Organizadores de soporte para computadoresMUEBLE PARA COMPUTADORA | EscritoriosESCRITORIO EJECUTIVO |
| AUD-V2-078 | 24-0660-10-1432538-1-1 | EstilógrafosMICRO PUNTA; PUNTA FINO 0.7; COLOR AZUL | Tintas acrílicas a base de aguaTINTA PARA TAMPO COLOR NEGRO 30 MLTR |
| AUD-V2-079 | 24-0660-10-1412564-2-2 | Impresoras de múltiples funcionesimpresoras de escritorio | Impresoras de múltiples funcionesescaner |
| AUD-V2-081 | 23-0660-11-1318250-1-1 | Impresoras láserIMPRESORAS LASER (DE ACUERDO A ESPECIFICACIONES TECNICAS) | Computadores de escritorioCOMPUTADORAS DE ESCRITORIO (DE ACUERDO A ESPECIFICACIONES TECNICAS) |
| AUD-V2-082 | 23-0660-11-1310548-1-1 | Papel para impresora o fotocopiadoraPAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJAS (ARTWORK O SU EQUIVALENTE) | Papel para impresora o fotocopiadoraPAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS (ARTWORK O SU EQUIVALENTE) |
| AUD-V2-084 | 24-0660-11-1413532-1-1 | Clips para papelCLIPS PARA PAPELES; MATERIAL: METAL; NUMERO: 4; DE 33 MM; PRESENTACION: CAJA DE 100 UNIDAD | FoldersFOLDERS; MATERIAL PLASTICO; TAMAÑO OFICIO; COLOR SURTIDO |
| AUD-V2-085 | 24-0660-11-1459564-1-1 | Papel para impresión de computadoresPAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS; 216 MM X 279 MM | Papel para impresión de computadoresPAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJAS; 216 MM X 330 MM |
| AUD-V2-087 | 25-0660-11-1610359-1-1 | Tóner para impresoras o faxTóner para Impresora; Modelo de Impresora Laser Jet M201; color de tinta Negro; Serie CF 283X | Tóner para impresoras o faxTóner para Impresora; Modelo de Impresora Hp Laser Jet Pro M402/MFP M426; Color negro; Serie CF 226X |
| AUD-V2-088 | 25-0660-11-1518371-1-1 | Papel satinadoPAPEL LUSTRE; TAMAÑO 50 X 70; COLOR SURTIDO | Papel para impresión de computadoresPAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR SURTIDO; PRESENTACION POR HOJA; 7000=AMARILLO; 7000=CELESTE; 7000=ANARANJADO; 5000=ROJO; 4000=VERDE CLARO; 3500=ROSADO |

En particular, AUD-V2-087 compara tóner CF283X con CF226X: son referencias distintas y el par sigue descartado. Tampoco se une papel carta con oficio ni una impresora de escritorio con un escáner. Estas conclusiones rechazan esas parejas concretas; no afirman que las observaciones carezcan de cualquier otra contraparte correcta.

## 5. Propuesta acotada, todavía no implementada

La mejora debe extender las relaciones documentales de las etapas 2–3 existentes, sin cambiar canonicalización ni crear un sistema paralelo. Se propone este orden:

1. **Contexto FORM 220.** Reconocer explícitamente que el número no está previsto en su tabla de bienes. Cuando haya descripción exacta, cantidad e importe coherentes, proveedor explícito en ambas filas, relación única en ambos sentidos y una sola fila contextual con proveedor/número/firma/recepción coincidentes, permitir una asociación derivada con referencia a esa fila contextual. Mantener null en el dato contractual original del ítem. Si un proveedor tiene varias órdenes posibles, abstenerse. Conservar el precio contratado separado del preseleccionado y comprobar la unidad comercial sin inventar la que falta en FORM 500.
2. **Número compartido en FORM 200.** Resolver el contexto con proveedor y fechas documentados; no solo con número. Para los casos aquí revisados, incorporar como evidencia complementaria el proveedor por ítem de FORM 170, usando los módulos existentes y sin perfeccionar toda su extracción. Si no existe corroboración suficiente, hay varios candidatos o las etapas discrepan, conservar ambigüedad. Una adjudicación no se convierte automáticamente en recepción ni se copia como proveedor literal de una fila de contratación que no lo declara.
3. **Cadena modificatoria explícita.** Representar principal y modificatorio como eventos del mismo ciclo, con sus documentos y alcance. Empezar únicamente por modificaciones de plazo comprobadas, sin cambios de bienes, cantidades o monto, y con vinculación explícita de números/proveedor/fechas. No ignorar conflictos sin ese puente; no sumar principal, modificatorio y recepción como adquisiciones separadas. FORM 250 debe entrar primero como evidencia de relación, sin tratar su monto global o su cero como ítems.
4. **Variante de FORM 500.** En una tarea separada de fidelidad, mapear de forma comprobada `Monto ejecutado` en el diseño observado; distinguir `Cantidad recepcionada` de `Cantidad no recepcionada` para evitar encabezados semánticos duplicados; conservar las 13 columnas, el precio explícito y la ausencia de estado. Validar otros originales antes de generalizar y no derivar estado o precios sin condiciones documentales suficientes.

No se propone similitud semántica, LLM ni equivalencia técnica para rescatar estos pares. Tampoco una regla de “mismo proveedor + mismo importe” ni una tolerancia general a contratos distintos. Cada vía debe exponer evidencia, cardinalidad y motivo de abstención.

### Criterios para una futura implementación

- Convertir estos 38 diagnósticos en referencia documental de desarrollo, con aprobación humana pendiente; ya no usarlos como evaluación independiente de una regla diseñada con ellos.
- Mantener sin confirmar los 12 controles incompatibles; agregar controles con mismo proveedor y varias órdenes, descripciones duplicadas, importes repetidos, recepción parcial y modificatorios que alteren bienes/cantidades/montos.
- Medir cobertura por vía y revisar una muestra independiente de nuevos rescates fuera de estos CUCE; no extrapolar los 38 casos al resto del corpus ni declarar 100% de precisión.
- Exigir trazabilidad a cada celda y a toda arista contractual, unicidad en ambos sentidos y abstención en asociaciones uno a varios no resueltas. No repartir montos globales entre ítems por suma coincidente.
- Preservar IDs y observaciones originales, cantidades e importes separados por etapa y unidad; una asociación es una vista derivada, no otra compra.
- Reproducir v1/v2 y la regresión de 2024 en salidas nuevas; no sustituir las referencias anteriores. Comparar altas, bajas y motivos de cada asociación modificada antes de cualquier publicación.

## 6. Entregables y verificación

Los anexos locales están en `procesamiento/historico/data/diagnostico_auditoria_v2_20261109_01/`:

- `diagnostico_casos.csv`: 50 conclusiones nuevas separadas de las etiquetas recibidas, con referencias y evidencia complementaria.
- `evidencia_por_caso.json`: literales de las filas de ambos formularios, contexto contractual, unicidad en tablas completas, referencias FORM 170 y puente FORM 250.
- `conciliacion_por_proveedor.json`: controles por proveedor en las tablas completas de los 21 CUCE indeterminados.
- `revision_asistida_recibida.csv` e `informe_asistido_recibido.md`: copias exactas de las entradas recibidas, sin alterar sus etiquetas.
- `verificacion_y_procedencia.json`: hashes y verificaciones de conservación de entradas, originales, módulos y salidas congeladas.

El cotejo utiliza un lector HTML independiente del parser comercial. Se abrieron 68 HTML originales, incluidos cinco FORM 170 y el FORM 250, y se verificaron sus hashes. Se comprobaron las 38 correspondencias por descripción/cantidad/importe en ambas tablas completas, la aritmética por ítem, la selección contextual del proveedor y las fechas; se verificaron los 12 controles negativos y la conciliación por proveedor de los 21 procesos. La conservación de reglas y referencias se comprobó por SHA256, sin ejecutar el algoritmo de vinculación ni una nueva extracción del corpus.

El script de reproducción es `procesamiento/historico/auditorias/diagnostico_originales_v2.py`: solo genera el acta de los casos revisados y comprueba sus evidencias; no es una implementación de las mejoras propuestas. Exige salida nueva y conserva v1/v2 y las muestras. No hubo cambios en parser, linking, acquisitions, scraper, SQLite de referencia, Supabase, dashboard o canonicalización. Sin descargas, APIs, LLM, commits ni push.

La siguiente tarea concreta recomendada es preparar y revisar el contrato de prueba de la vía contextual FORM 220 (16 casos documentados y sus negativos), antes de autorizar cambios de reglas. Las demás vías deben validarse por separado.
