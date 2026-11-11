# Plan rector de inteligencia de mercado SICOES-BRAIN

Fecha de revisión: 2026-11-09. Base de código consultada: `main`, commit
`c2f0337` (`feat(historico): integrar scraper local y procesamiento documental`).
Este documento fija la dirección de desarrollo; las tareas propuestas no se
consideran implementadas por estar descritas aquí.

## Prioridad de desarrollo vigente: fichas de adquisición

La primera entrega desarrolla las etapas 1–3 para bienes adquiridos: **FORM 500**
es la fuente principal de recepción; **FORM 200/220**, de contratación; **DBC**,
de requisitos técnicos. FORM 100/110 y FORM 170 siguen disponibles como fuentes
complementarias. No se perfecciona ahora su extracción. Las 17 filas de FORM 170
son deuda técnica **no bloqueante**, salvo evidencia concreta de impacto sobre
la cobertura de adquisiciones. No habilitamos aún etapas 4, 5 ni 6 ni uso de LLM.

El objetivo comercial es conocer bienes, compradores, proveedores, cantidades,
precios unitarios/totales, fechas y recurrencia; después, oportunidades de
abastecimiento y predicción de necesidades. Una ficha es una vista derivada de
observaciones separadas y auditables, nunca un reemplazo del original ni una
nueva compra que deba sumarse a cada etapa. Los requisitos DBC no prueban las
características efectivamente recibidas.

El esquema, reglas previas, implementación y evaluación de esta entrega se
mantienen en [Fichas de adquisición v1](desarrollo/FICHAS_ADQUISICION_V1.md).
La [continuación de asociación v2](desarrollo/ASOCIACION_ADQUISICIONES_V2.md)
resuelve contratos con varios ítems entre hipótesis elegibles, conservando
descartes y contextos ambiguos; su referencia documental requiere validación
humana independiente. El [informe de la primera entrega](desarrollo/ENTREGA_FICHAS_ADQUISICION_V1.md)
detalla cobertura, ejemplos, pruebas y límites medidos. Se reutilizan `parser.py`, `review.py`, `dbc.py`, `technical.py` y las comprobaciones
de `linking.py`; `acquisitions.py` agrega una entrada local independiente sin
cambiar los comandos ni el comportamiento de los módulos históricos existentes.
Esta prioridad actualiza la secuencia del mismo plan de seis etapas.

## Propósito y decisiones rectoras

Transformar los datos históricos de contratación pública de SICOES en inteligencia
de mercado útil para identificar demanda real, frecuencia de compras, precios,
cantidades, especificaciones, entidades compradoras, proveedores y oportunidades
de importación o abastecimiento. El resultado debe permitir decidir qué ofrecer,
a quién, en qué presentación, con qué requisitos y con qué recurrencia observada.
El valor del sistema se mide por la confiabilidad de esas respuestas y su evidencia.
La clasificación y la búsqueda de descripciones similares son componentes de apoyo.

La demanda real se reconstruye distinguiendo lo solicitado, adjudicado, contratado
y recibido, las modificaciones y las anulaciones. El requerimiento original puede
medirse antes de resolver todo ese ciclo, pero debe llamarse así; no representa
por sí solo demanda neta ni compras efectivamente realizadas. Un proceso publicado
no demuestra una venta y un precio referencial no demuestra un precio pagado.

Se reutiliza el recorrido existente: captura local con manifiestos → observaciones
por formulario → atributos y relaciones documentales → candidatos → evaluación
contextual → agrupaciones versionadas → indicadores y oportunidades. La publicación
puede avanzar con información validada de las primeras etapas sin esperar a que
toda la canonicalización esté resuelta.

Principios obligatorios:

- Mantener separados originales inmutables, observaciones extraídas, normalizaciones,
  cálculos e inferencias. Conservar fuente, hash, posición y versión de regla/modelo.
- Tratar cada etapa administrativa como evidencia del ciclo de una compra. No sumar
  sus cantidades como compras adicionales ni deduplicar por similitud de descripción.
- Conservar ausencias, ambigüedades y contradicciones. Desconocido no equivale a cero.
- Separar categoría, relación documental, equivalencia técnica e identidad comercial.
- Validar por categoría y por tipo de decisión; priorizar evitar fusiones indebidas.
- Mantener asignaciones reversibles y explicar desde cada indicador hasta el documento.
- Usar 2022 para validar estructuración y compatibilidad documental; conservar la
  restricción de no usarlo para ajustar algoritmos de canonicalización. Registrar
  cualquier exposición al corpus antes de definir una evaluación independiente.

## Evidencia local, cobertura y migración

### Inventario observado por entidad y gestión

Fuentes consultadas en modo lectura: `*/manifest.json` bajo
`scraper/historico_local/data/historico_http_paginas_<entidad>_<gestión>/`,
los `RESUMEN_HTTP.json` disponibles y el cierre de migración. No se hicieron nuevas
capturas, conversiones, extracciones de contenido ni llamadas a LLM en esta revisión.

| Entidad | Gestión | CUCE con manifiesto | COMPLETA | PARCIAL | FALTA_OCR | Versiones válidas declaradas | Referencias Markdown existentes |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0660-10 | 2022 | 24 | 11 | 2 | 11 | 102 | 91 |
| 0660-10 | 2023 | 29 | 9 | 1 | 19 | 122 | 103 |
| 0660-10 | 2024 | 19 | 7 | 0 | 12 | 84 | 72 |
| 0660-11 | 2023 | 51 | 21 | 3 | 27 | 219 | 192 |
| 0660-11 | 2024 | 28 | 11 | 1 | 16 | 123 | 107 |
| 0660-11 | 2025 | 14 | 7 | 0 | 7 | 65 | 58 |
| 0660-11 | 2026 | 29 | 21 | 4 | 4 | 127 | 123 |

Los estados son los registrados por el scraper, no certificaciones de cobertura
anual ni de fidelidad del parser. Las versiones cuentan entradas de manifiesto;
no son productos ni necesariamente documentos únicos por hash. En esta revisión
se comprobó la existencia de los Markdown referenciados; la legibilidad e integridad
de 0660-10 constan además en la verificación previa de migración. No se extiende esa
verificación de hashes a 0660-11 por analogía.

La tabla describe 194 CUCE locales en el alcance solicitado. No conocemos aquí el
denominador total de procesos publicados por entidad/gestión ni certificamos el
cierre de todas las páginas de cada corrida. En particular, 2026 es un período
parcial al corte; no debe compararse como año completo. La carpeta adicional
0660-11/2022 tiene cero manifiestos y no integra el corpus solicitado; no demuestra
ausencia de compras. Existen otros inventarios locales fuera de este alcance.

Documentos registrados sin versión válida, distintos de los pendientes de OCR:

| Entidad / gestión | Documentos sin versión válida | Etiquetas registradas |
|---|---:|---|
| 0660-10 / 2022 | 2 | FORM 170; Oferta del Proveedor Identificado |
| 0660-10 / 2023 | 1 | FORM 170 |
| 0660-10 / 2024 | 0 | — |
| 0660-11 / 2023 | 3 | FORM 180; Formulario 180 (Erroneo); FORM 170 |
| 0660-11 / 2024 | 1 | FORM 170 |
| 0660-11 / 2025 | 0 | — |
| 0660-11 / 2026 | 4 | FORM 250 |

Un original válido pendiente de OCR existe, pero su texto puede no estar disponible.
Un documento sin versión válida no debe convertirse en observaciones vacías exitosas.
Los documentos anunciados, los registrados y los efectivamente descargados requieren
conciliación antes de afirmar completitud. El OCR de ofertas queda fuera del alcance
actual del procesamiento histórico local.

### Migración ya verificada en main

La incorporación de código y la migración local ya ocurrieron. La frase anterior
que dejaba los datos para una futura segunda fase queda sustituida por este estado.
El [cierre de migración](CIERRE_MIGRACION_HISTORICA.md) conserva la evidencia histórica
y el HEAD de aquel momento; el commit actual de integración es `c2f0337`.

- Los corpus 0660-10 de 2022–2024 están en su ubicación definitiva: 1.451 archivos
  cotejados con SHA256 previo al traslado, sin faltantes ni diferencias. Son 72 CUCE,
  308 versiones y 266 Markdown legibles en aquella comprobación.
- Se preservaron 49 archivos derivados y cinco SQLite de referencia bajo
  `procesamiento/historico/data/referencias/experimental_20261109T152013Z/`, con
  verificaciones de integridad y claves foráneas correctas según el cierre.
- La regresión ya ejecutada desde main está en
  `procesamiento/historico/data/regresiones/20261109T152013Z/`: 19 CUCE de 2024,
  64 formularios procesados, uno excluido, 348 observaciones y 3.523 celdas cotejadas;
  siete CUCE con DBC, 54 bloques, 198 atributos y relaciones 51 CONFIRMADA / 3 AMBIGUA.
  Coincidió con la referencia, sin diferencias inesperadas y sin conexiones de red.
- Las referencias de compatibilidad de 2022 y 2023 contienen respectivamente 487 y
  517 observaciones. Son resultados históricos preservados con omisiones conocidas,
  no nuevas corridas integrales aprobadas ni datasets listos para canonicalización.
- 0660-11 está disponible localmente según los manifiestos anteriores, pero no forma
  parte de esa regresión ni tiene acreditada aquí una validación integral equivalente.

La migración no publica datos en Supabase ni en el dashboard. La operación real de
Brave/sesión sigue pendiente de validación autorizada; un perfil local existente no
acredita su funcionamiento. Las rutas antiguas de las referencias se conservan como
procedencia, no como dependencias del worktree experimental. Consultar también
[Integración histórica](INTEGRACION_HISTORICA.md) y
[Procesamiento histórico](../procesamiento/historico/README.md); sus descripciones de
fases anteriores deben leerse con la fecha del cierre y esta actualización.

## 1. Extracción documental

**Objetivo.** Disponer de evidencia documental íntegra y de una medida explícita de
lo capturado y lo pendiente por entidad, gestión, CUCE y tipo de documento.

**Datos de entrada.** Selección de entidad/gestión, páginas de resultados, detalle
del proceso, formularios y archivos anunciados, sesión autorizada y manifiestos
anteriores para reanudar sin perder versiones.

**Procesamiento esperado.** Recorrer y conciliar páginas/procesos; capturar formularios
por HTTP y documentos adjuntos; validar cuerpos, formatos y tamaños; calcular hashes;
conservar intentos, versiones, metadatos y conversión a Markdown. Diferenciar ausencia
local, no publicación comprobada, captura fallida, vacío explícito y falta de OCR.
Preservar recuperación de sesión y descarga sin ventana ya desarrolladas.

**Resultados de salida.** Originales, manifiestos por CUCE, Markdown cuando exista
texto extraíble, reportes de disponibilidad, pendientes y cobertura de navegación.

**Módulos existentes reutilizables.** `scraper/historico_local/historico_http_paginas.py`,
`historico_http_directo.py`, `http_forms.py`, `storage.py`, `parsing.py`,
`brave_bootstrap.py`, su `schema.sql` y `Correr Sicoes Local.command`.
Ver el [manual del scraper](../scraper/historico_local/README.md).

**Estado actual.** Código integrado y corpus locales inventariados; migración 0660-10
verificada. Las pruebas previas acreditan componentes y mocks, no una nueva sesión
real del portal ni cobertura exhaustiva de los siete conjuntos.

**Limitaciones conocidas.** Corridas parciales y OCR pendiente según tabla; documentos
sin versión válida; formatos y publicaciones heterogéneos. No hay OCR de ofertas en
este flujo. `pypdf` es opcional del convertidor auxiliar, no del convertidor operativo.

**Criterios antes de avanzar.** Inventario conciliado con archivos y anuncios;
procedencia y hash por versión usada; pendientes clasificados sin ocultarlos; selección
explícita de versión por documento. Para procesar un subconjunto no hace falta esperar
a todo el OCR, pero sí declarar exclusiones y cobertura. No afirmar completitud anual
sin evidencia del recorrido y del universo publicado.

## 2. Estructuración de observaciones

**Objetivo.** Reconstruir fielmente las filas económicas de los formularios y su etapa
administrativa antes de interpretar identidad de productos o sumar demanda.

**Datos de entrada.** HTML originales válidos, manifiestos y versiones seleccionadas,
metadatos del CUCE y variantes de encabezados/tablas.

**Procesamiento esperado.** Leer secciones, tablas y filas conservando coordenadas;
resolver encabezados compuestos sin desplazar celdas; extraer descripción, ítem/lote,
unidad, cantidad, precio, importe, moneda, fechas y proveedor cuando consten. Mantener
valores literales, normalizados y derivados separados. Auditar filas omitidas,
columnas desconocidas, duplicados y advertencias aritméticas. Identificar requerimiento,
adjudicación, contratación y recepción por evidencia del formulario/sección.

**Resultados de salida.** Observaciones con identificador y procedencia estable,
CSV/SQLite derivados, auditoría por documento/CUCE y conciliación de filas/celdas.
Una observación representa una fila en una etapa, no una compra adicional automática.

**Módulos existentes reutilizables.** `procesamiento/historico/parser.py`, `pipeline.py`,
`review.py`, `schema.sql`, CLI `__main__.py` y pruebas de `tests/test_processing.py`.
Reutilizar sus contratos; no sustituirlos por el parser antiguo de producción.

**Estado actual.** Regresión 2024 verificada con 348 observaciones. Compatibilidad de
2022–2023 preservada con fallos pendientes; 0660-11 con cotejo de celdas de los formularios prioritarios en la entrega v1; no equivale a validación comercial independiente.
FORM 600 solo inventariado; FORM 100-E excluido hasta definir su alcance.

**Limitaciones conocidas y deuda técnica complementaria.** `column_count_mismatch` deja 17 filas
de bienes de FORM 170 sin extraer por encabezados compuestos:

| Gestión | CUCE | Filas pendientes |
|---|---|---:|
| 2022 | 22-0660-10-1199037-2-2 | 4 |
| 2022 | 22-0660-10-1250273-1-1 | 4 |
| 2023 | 23-0660-10-1323309-1-1 | 3 |
| 2023 | 23-0660-10-1337681-1-1 | 1 |
| 2023 | 23-0660-10-1356740-1-1 | 5 |

Además, FORM 170 de `22-0660-10-1199042-1-2` y
`23-0660-10-1309108-1-1` carecen de versión válida; el cargador general todavía no
los tolera. Recuperar las 17 filas no resuelve esos dos documentos. Los pendientes
de 0660-11 requieren evaluación propia, sin asumir compatibilidad por nombre de FORM.

**Criterios antes de avanzar.** Conciliar FORM 500 y FORM 200/220 por entidad y
gestión, conservar faltantes explícitos y cotejar sus celdas contra originales.
Mantener la regresión 2024. La recuperación de las 17 filas no bloquea estas fichas:
no se ha demostrado que sean necesarias para interpretar los bienes contratados
o recibidos. Su eventual impacto se evalúa por CUCE sin prometer equivalencia
entre fases. El cargador de fichas no intenta parsear FORM 170 ni oculta su deuda.
Antes de evaluar canonicalización se congela un subconjunto de adquisiciones con
calidad y cobertura acreditadas; no se exige perfeccionar todo formulario
complementario para aprobar ese subconjunto.

## 3. Extracción de atributos y enriquecimiento documental

**Objetivo.** Convertir las características técnicas y comerciales en evidencia
estructurada comparable, conservando el contexto que explica cada valor.

**Datos de entrada.** Observaciones validadas, descripción original, DBC DOCX y Markdown
referenciados, secciones/tablas técnicas y patrones existentes por categoría.

**Procesamiento esperado.** Segmentar DBC y vincular bloques a observaciones con reglas
auditables. Extraer tipo, marca/modelo/código, dimensiones, material, capacidad,
compatibilidad, presentación y otros discriminantes por familia. Registrar valor,
unidad, evidencia literal, posición, fuente, versión y operador: exacto, mínimo,
máximo, rango, alternativa, prohibido o desconocido. No reducir “mínimo 75 g/m²” a
“exactamente 75 g/m²”. Conservar conflictos entre fuentes y requisitos frente a
características comprobadas de lo adjudicado/recibido.

**Resultados de salida.** Inventario DBC, bloques técnicos, atributos con evidencia,
relaciones CONFIRMADA/AMBIGUA y representaciones A (formulario) / B (enriquecida).
El vínculo documental confirmado no acredita equivalencia entre productos.

**Módulos existentes reutilizables.** `procesamiento/historico/dbc.py`, `technical.py`,
`linking.py`, `enrich.py` y `tests/test_enrichment.py`;
`monitor/canonicalizacion/extractor_atributos.py` y
`impresion/extractor_impresion.py` como base de patrones. `technical.py` reutiliza
patrones literales de impresión por AST sin ejecutar su configuración externa.

**Estado actual.** Enriquecimiento local reproducible en 2024: 198 atributos y 54
bloques; las tres relaciones ambiguas no inyectan atributos como hechos confirmados.
El extractor experimental por categorías ya existe, pero su cierre provisional no
valida su cobertura en los nuevos corpus ni integra automáticamente ambos flujos.

**Limitaciones conocidas.** Cobertura desigual por categoría; evidencia no extraíble
por OCR pendiente; soporte DBC local condicionado a DOCX y Markdown. No está validado
un enriquecimiento universal para todos los formatos. Un requisito DBC no demuestra
que el proveedor haya entregado un producto con esa prestación.

**Criterios antes de avanzar.** Medir precisión y cobertura por atributo/categoría,
operador y tipo de documento con revisión de evidencia; probar unidades, negaciones,
rangos, presentaciones y contradicciones. Cero incorporación de vínculos ambiguos
como hechos confirmados. Poder reconstruir A/B y separar atributos publicados de
inferidos. Definir discriminantes de identidad y de incompatibilidad antes de evaluar
pares. Añadir atributos no debe alterar el número ni las cantidades de observaciones.

## 4. Generación de candidatos

**Objetivo.** Reducir el espacio de comparación conservando posibles equivalencias
que merecen evaluación, con razones comprensibles para cada propuesta.

**Datos de entrada.** Descripciones originales, atributos validados, códigos, familia,
unidades/presentaciones y evidencias documentales disponibles.

**Procesamiento esperado.** Reutilizar bloqueo por familia y señales de códigos,
atributos y texto; preservar los descartes y su motivo. La similitud textual es una
señal de recuperación. Compartir UNSPSC o ser compatible con la misma impresora no
prueba identidad. Incorporar candidatos difíciles y revisión de omisiones fuera del
bloqueo para medir qué equivalencias se pierden.

**Resultados de salida.** Pares de identificadores con motivo, señales utilizadas,
versión del generador y trazabilidad. Ninguna asignación canónica nace de esta etapa.

**Módulos existentes reutilizables.** `monitor/canonicalizacion/blocker_candidatos.py`,
reportes de cobertura y muestras; taxonomía de `monitor/canonicalizacion/taxonomia/`
y `monitor/canonicalizar_taxonomia.py` como antecedentes de categorización y triaje,
no como prueba de identidad. Reutilizar artefactos locales, sin ejecutar sus accesos
externos durante esta tarea.

**Estado actual.** Generador experimental construido sobre descripciones únicas del
universo anterior. No está validado sobre las observaciones enriquecidas nuevas.
Las “etapas 1–4” de ese paquete son internas y no equivalen a las seis de este plan.

**Limitaciones conocidas.** Cobertura restringida de categorías; errores de extracción
pueden excluir positivos; las estadísticas antiguas no son métricas de los corpus
locales actuales. El generador no puede medir sus propias omisiones solo con sus pares.

**Criterios antes de avanzar.** Medir recuperación en positivos etiquetados obtenidos
también fuera del generador, reducción de pares y costo por categoría. Registrar
exclusiones por atributos o unidades y revisar falsos descartes. Fijar objetivos de
recuperación antes de medir y congelar la versión para comparar verificadores.

## 5. Evaluación de equivalencia mediante reglas y LLM

**Objetivo.** Resolver qué relación sostiene la evidencia entre dos productos, con
abstención explícita y decisiones separadas por nivel y contexto de compra.

**Datos de entrada.** Pares candidatos, ambas descripciones originales, atributos con
operadores, evidencia documental, faltantes, conflictos y política por categoría.

**Procesamiento esperado.** Aplicar reglas y, cuando se autorice su evaluación, LLM
con contrato de salida. Separar familia, subfamilia y producto específico; emitir
SI/NO/INSUFICIENTE con evidencia y motivos. Distinguir identidad comercial de aptitud
para satisfacer un requisito técnico. Una contradicción documentada debe resolverse
explícitamente; la interpretación del modelo no puede borrarla sin justificación.

**Resultados de salida.** Veredictos por relación/nivel, atributos decisivos,
evidencias, faltantes, conflictos y estado de revisión. Para LLM: prompt, modelo,
parámetros, respuesta original, versión, consumo y costo reales. Una recomendación
no constituye autorización de fusión ni etiqueta de verdad para evaluarse a sí misma.

**Módulos existentes reutilizables.** `monitor/canonicalizacion/verificador_niveles.py`,
`scoring_verificador.py`, `muestra_verificador.py`, baselines congeladas y reportes de
aceptación. Las experiencias LLM de taxonomía sirven para contratos y trazabilidad,
pero no constituyen un verificador híbrido validado de equivalencia contextual.

**Estado actual.** Verificador de reglas cerrado como experimento reproducible;
precisión suficiente para fusiones automáticas no demostrada. La comparación
controlada reglas/LLM/híbridos sobre el corpus enriquecido está pendiente.

**Limitaciones conocidas.** Familia amplia se apoya en el bloqueo y tiene SI fijo en
el verificador experimental; requiere negativos entre familias. Las muestras usadas
para ajustar son regresión, no prueba independiente. Los pares comparten descripciones
y no son ensayos independientes. Los casos de atributos solo de contradicción,
como huella/pliegues en llantas, requieren política explícita: su ausencia no acredita
igualdad ni necesariamente invalida un SI obtenido con otros discriminantes.

**Criterios antes de avanzar.** Ejecutar el protocolo comparativo descrito abajo solo
tras validar la estructuración; medir falsos positivos, abstención y cobertura por
categoría. Mantener modo asistido donde falte evidencia. El objetivo heredado de
precisión de fusión ≥98% exige diseño e intervalo que consideren dependencia;
no se acredita contando muchos pares de pocas variantes. Cumplir además los
[criterios experimentales existentes](../monitor/canonicalizacion/reportes/criterios_aceptacion_etapa3.md)
y validar clústeres separadamente antes de persistir asignaciones automáticas.

## 6. Agrupación canónica

**Objetivo.** Representar productos comparables mediante grupos estables y auditables
que permitan agregar demanda sin mezclar identidades o presentaciones incompatibles.

**Datos de entrada.** Observaciones validadas, veredictos confirmados, política por
categoría, evidencia de identidad, restricciones de unidad/presentación y revisión.

**Procesamiento esperado.** Reutilizar el diseño de agrupación con comprobación de
pares internos; A≈B y B≈C no permite agrupar A con C sin evaluarlos. Mantener categoría
y equivalencia técnica como relaciones distintas de la identidad comercial canónica.
Registrar altas, bajas, división de grupos, conflictos, autor, versión y causa.
Las asignaciones se revierten sin sustituir ni borrar observaciones originales.

**Resultados de salida.** Catálogo y miembros versionados, estados provisional,
confirmado y pendiente; registro de decisiones y agregado compatible con el ciclo
de compra. Los grupos amplios permiten explorar categorías, no sumar unidades como
si todos sus miembros fueran el mismo producto vendible.

**Módulos existentes reutilizables.** `monitor/canonicalizacion/simulacion_agrupacion.py`,
`reportes/diseno_etapa4.md`, `migracion_etapa4.sql` (borrador),
`provisional/generar_provisionales.py`, `demanda/agregador_demanda.py` y
`monitor/asignar_canonicos.py` como antecedente declarativo. Reutilizar también la
lectura del dashboard en `app/src/lib/historico.ts`, previa validación de su contrato.

**Estado actual.** Hay simulación, provisionales y agregador local; su existencia no
acredita una agrupación definitiva del corpus nuevo. La migración de esquema es un
borrador y no se aplica en esta tarea. El asignador declarativo y el overlay del
dashboard son caminos distintos del pipeline experimental.

**Limitaciones conocidas.** Precisión por pares no garantiza grupos homogéneos;
faltan validación independiente, integración de nuevas observaciones y prueba de
reversibilidad operativa. Un nombre parecido de grupo no autoriza fusionarlo con otro.

**Criterios antes de avanzar.** Verificar todos los pares exigidos por la política,
cero conflictos técnicos conocidos sin resolver, homogeneidad comercial y unidades
compatibles; auditar muestras de clústeres completos y de observaciones sin agrupar.
Demostrar reversión y comparar cantidades/importes antes y después. La agrupación
no debe crear ni perder demanda: cambia su clasificación, no los hechos económicos.

## Arquitectura híbrida y significado de las decisiones

La extracción de atributos es un componente fundamental: permite filtrar, explicar,
comparar precios y cantidades, detectar incompatibilidades y construir fichas incluso
cuando no hay una identidad canónica resuelta. No es una fase prescindible por usar
un modelo de lenguaje. La comparación debe recibir conjuntamente descripción original,
atributos estructurados y evidencia documental; conservar el texto evita perder
matices que un extractor todavía no reconoce.

Las reglas resuelven normalizaciones y restricciones explícitas; el LLM puede
interpretar abreviaturas, referencias y contexto, proponer una lectura o abstenerse.
La política híbrida decide qué casos resuelve cada componente y cómo tratar desacuerdos.
No debe aceptar automáticamente el último resultado ni una mayoría de respuestas.
Un nuevo atributo interpretado por LLM se conserva como inferencia hasta su validación.

| Relación | Qué afirma | Qué permite |
|---|---|---|
| Identidad comercial | Mismo producto vendible, con discriminantes y presentación compatibles; marca/modelo cuando sean relevantes | Proponer una identidad canónica específica; conversión de presentación solo con factor probado |
| Equivalencia técnica | Puede satisfacer un requisito concreto con prestaciones suficientes | Comparación de alternativas para ese requisito, sin afirmar mismo SKU o intercambiabilidad universal |
| Misma categoría | Comparten familia o segmento | Navegación y análisis por categoría, con cantidades separadas por unidad/producto |
| Información insuficiente | Faltan discriminantes o no puede resolverse evidencia incompatible | Revisión o enriquecimiento; ninguna fusión confirmada |

La equivalencia técnica puede ser contextual y direccional: un producto de mayor
capacidad puede cumplir un mínimo, pero el de menor capacidad no cumple el requisito
inverso. El verificador actual de tres niveles no demuestra por sí solo esa relación.
El contrato futuro debe representarla explícitamente sin reinterpretar sus SI como
identidad comercial. La pertenencia a familia/subfamilia tampoco equivale a identidad.

### Protocolo de evaluación comparativa pendiente

1. Cerrar primero la etapa 2 y congelar versiones de observaciones, fuentes y atributos.
   Separar conjuntos de desarrollo, regresión y prueba independiente por procesos,
   descripciones/variantes y evidencia compartida, evitando filtraciones. Respetar la
   reserva de 2022 y documentar qué corpus ya fue observado al ajustar.
2. Construir referencia humana ciega por categoría y relación con evidencia citada;
   resolver desacuerdos por revisión y conservar los irresolubles como insuficientes.
   Incluir positivos, negativos difíciles, ambiguos, contradicciones y casos fuera del
   generador. No usar etiquetas del modelo como verdad de evaluación.
3. Comparar sobre los mismos pares: reglas; LLM con descripción original; LLM con
   descripción, atributos y evidencia; híbrido con reglas y derivación contextual al
   LLM. Comparar además A/B para aislar el efecto del DBC. Mantener fija la información
   disponible en comparaciones directas y declarar las diferencias en las ablaciones.
4. Fijar antes de ejecutar versiones, prompts, contrato, presupuesto, política de
   desacuerdo y umbrales por categoría. Conservar resultados sin sobrescribirlos.
   No se realizan llamadas a LLM ni generación de muestras en esta tarea documental.
5. Reportar precisión/recuperación por relación, matriz SI/NO/INSUFICIENTE, fusiones
   indebidas, abstención y exactitud sobre casos decididos, cobertura total, costo,
   latencia y estabilidad. Medir extracción y recuperación de candidatos por separado
   para no atribuir todos los errores al verificador.
6. Reportar denominadores en pares, descripciones, variantes, procesos y clústeres;
   estimar incertidumbre considerando dependencia. Evaluar homogeneidad de grupos y
   efecto sobre cantidades/precios además del resultado por par. Seleccionar una
   política solo con evidencia; el modo asistido sigue siendo una salida válida.

Ejemplos de diseño de prueba, ilustrativos y no etiquetas de registros reales:

| Caso | Evidencia a comparar | Resultado esperado |
|---|---|---|
| Positivo | “Resma bond A4 blanco 75 g/m² 500 hojas” frente a la misma especificación con otro orden textual, sin otros discriminantes exigidos por la política | Identidad bajo esa política y presentación; citar coincidencias |
| Negativo difícil | RAM DDR3 8 GB frente a DDR4 8 GB | Misma categoría, sin identidad ni equivalencia para un equipo que requiere DDR3 |
| Equivalencia contextual | Requisito de capacidad mínima 16 GB frente a producto de 32 GB con las demás condiciones confirmadas | Puede cumplir ese requisito; no es identidad comercial con el de 16 GB |
| Ambiguo | “Tóner para impresora X” frente a cartucho de código conocido compatible con X | Categoría/compatibilidad pueden coincidir; identidad insuficiente sin código, rendimiento y presentación pertinentes |
| Contradictorio | Formulario dice A4 y DBC asociado dice carta | Conflicto visible; revisar versión/asociación, no elegir el dato que facilite fusionar |
| Presentación distinta | Una caja de diez unidades frente a una unidad suelta | No comparar precios directamente; convertir solo si contenido y factor están acreditados |
| Operador distinto | Requisito “gramaje mínimo 75” frente a descripción “75 g/m²” | Cumplimiento posible bajo el resto de requisitos; el mínimo no demuestra valor exacto del producto |

## Dashboard: publicación progresiva de información

El dashboard actual consulta `hist_*` y usa un overlay de canónicos provisionales.
No tiene un importador validado para las nuevas observaciones locales. Su colapso por
`(CUCE, nro_item, lote)` no prueba correspondencia entre fases del corpus nuevo.
Los módulos de `app/src/app/historico/` y `app/src/lib/historico.ts` son la base a
reutilizar; este plan no ordena sustituirlos ni publicar datos ahora.

Cada entrega debe identificar dataset/versión, entidad/gestión, fecha de corte,
cobertura, etapa administrativa, cantidad de observaciones elegibles/excluidas,
calidad y estado de confirmación. Las siguientes vistas pueden madurar por separado:

| Vista | Información publicable y dependencia | Condición de publicación |
|---|---|---|
| Resumen general del mercado | Procesos, entidades, períodos, disponibilidad documental; después importes por etapa | Desde etapa 1 para cobertura; etapa 2 validada para métricas económicas; sin extrapolar a todo SICOES |
| Exploración de procesos e ítems | Cronología, formularios, filas y documentos por CUCE | Etapa 2; mostrar faltantes y separar etapas, versiones y lotes |
| Buscador de productos | Texto original, categoría y filtros técnicos progresivos | Búsqueda textual con etapa 2; atributos con etapa 3; marcar coincidencias aproximadas y canónicos provisionales |
| Demanda y recurrencia | Cantidades por producto/unidad, procesos compradores e intervalos entre eventos | Observaciones validadas y correspondencia entre fases; recurrencia por evento de compra, no número de formularios |
| Análisis de precios | Referenciales, adjudicados, contratados y recibidos por separado; distribución, mediana y dispersión | Producto/presentación comparables, moneda y base de precio conocidas; mostrar tamaño de muestra y fechas |
| Entidades y proveedores | Quién requiere, adjudica, contrata o recibe; proveedor identificado por evidencia de etapa | Identidad y rol documentados; normalización de nombre no debe fusionar personas/empresas sin respaldo |
| Fichas técnicas y trazabilidad | Descripción, atributos, requisitos, conflictos y acceso a evidencia | Etapa 3 validada; distinguir requisito publicado de característica entregada comprobada |
| Agrupaciones canónicas y oportunidades comerciales | Demanda comparable, compradores recurrentes, alternativas y ventanas de abastecimiento | Etapas 5–6 validadas para identidad; oportunidades etiquetadas como inferencias con cobertura y supuestos |

### Contrato de métricas y prevención de doble conteo

La publicación debe preparar un dataset separado, conciliarlo con la versión vigente
y cambiar de versión consultada de forma reversible. No insertar cuatro etapas en
`hist_items` esperando que las vistas actuales resuelvan el ciclo automáticamente.

- Definir para cada indicador unidad de análisis, etapa, fecha, denominador y política
  de versiones/anulaciones. Requerimiento original, adjudicación, contratación y
  recepción son series distintas; sus importes no se suman como tamaño de mercado.
- Relacionar fases con evidencia de proceso, ítem/lote, producto y cambios. El número
  de ítem puede cambiar; la igualdad de claves no basta y la ausencia de relación
  obliga a abstenerse. Reconvocatorias y compras repetidas requieren revisión propia.
- Separar cantidades de productos, unidades de medida y unidades comerciales: pieza,
  caja, paquete, resma, litro o kilogramo. Conservar factor de empaque y conversión
  documentados. Sin factor probado, mantener series distintas; no sumar cajas y piezas.
- Comparar precios por base homogénea, moneda y fecha; distinguir unitario/total,
  impuestos y condiciones cuando estén documentados. No imputar moneda, factor de
  empaque o precio pagado desde el texto. Un valor atípico se revisa, no se borra.
- Calcular frecuencia con eventos únicos de compra y ventanas de cobertura comparables.
  No interpretar períodos sin captura como cero demanda ni usar 2026 parcial como año
  completo. Diferenciar ausencia observada de falta de documentación.
- Las agrupaciones de categoría pueden mostrar gasto comparable por moneda/etapa y
  conteo de procesos, pero no una cantidad física total de productos heterogéneos.
- Toda cifra debe poder desagregarse a observaciones y fuentes. Comprobar que nuevas
  relaciones DBC o miembros canónicos no multiplican filas ni montos en las uniones.

### Oportunidades de importación y abastecimiento

Priorizar productos con recurrencia documentada, cantidades comparables, compradores
repetidos, especificaciones estables y dispersión de precios interpretable. Presentar
qué entidades compran, cuándo, en qué presentación y con qué proveedores observados;
separar concentración de adjudicaciones de una supuesta exclusividad del mercado.

La compra histórica permite formular hipótesis de reposición, consolidación de demanda
y abastecimiento. La viabilidad de importar necesita además costos, logística, plazos,
requisitos y márgenes que este corpus no acredita por sí solo. Las fichas de oportunidad
deben distinguir hechos, inferencias, supuestos y datos pendientes; una proyección no
se presenta como convocatoria vigente ni demanda garantizada. El radar existente puede
aportar convocatorias en una integración posterior, con fecha y fuente propias.

## Hoja de ruta técnica y criterios de aceptación

La secuencia reutiliza módulos existentes y separa calidad documental, calidad de
equivalencia y publicación. Los entregables siguientes son trabajo pendiente.

| Orden | Tarea y módulos de base | Entregable y aceptación |
|---|---|---|
| 1 — entrega local v1 | Inventariar FORM 500, FORM 200/220 y DBC; generar fichas con `acquisitions.py` reutilizando módulos históricos | Fuentes y hashes auditados, observaciones intactas, SQLite/JSONL nuevos, estados confirmada/ambigua/sin vínculo, cero suma entre fases y regresión 2024 conservada; resultados en informe v1 |
| 2 — en desarrollo, asociación v2 | Revisar casos reales ambiguos de contratación/recepción y layouts DBC no soportados | Referencia humana por tabla/fila, incluyendo múltiples ítems/proveedores/unidades; mejorar cobertura sin confirmar incompatibles; no usar número de ítem como identidad |
| 3 | Validar extracción de atributos y enriquecimiento sobre fichas, con `technical.py`, `dbc.py` y reglas de vinculación | Medición por atributo y operador sobre muestra revisada; requisitos frente a características comprobadas separados; ambigüedades sin inyección automática; repetir salida y cotejar hashes |
| 4 | Congelar corpus elegible y preparar referencia humana independiente y recuperación de candidatos con `blocker_candidatos.py` | Separación documentada de desarrollo/regresión/prueba; reserva de 2022 respetada; positivos fuera del bloqueo y negativos difíciles incluidos; objetivos de recuperación fijados |
| 5 | Comparar reglas, LLM e híbridos con verificador y scoring existentes | Protocolo previo, evaluación por relación/categoría, incertidumbre y dependencia explicitadas, costo y abstención medidos; sin declarar validado el 98% sin evidencia suficiente |
| 6 | Validar agrupación y agregación con simulador, diseño de etapa 4 y agregador de demanda | Grupos sin contradicciones internas conocidas; auditoría de clústeres, control de transitividad, registro reversible y conservación de cantidades/importes por etapa/unidad |
| 7 | Preparar publicación progresiva usando el contrato del dashboard existente | Dataset separado conciliado, vistas con cobertura y trazabilidad, cero doble conteo en casos de ciclo completo y fases ambiguas, comparación con versión vigente y reversión demostrada antes de publicar |
| 8 | Incorporar análisis comercial y oportunidades | Indicadores reproducibles de recurrencia y precios; oportunidades con evidencia, ventana temporal, cobertura, supuestos y validación de utilidad para abastecimiento |

No es necesario esperar al orden 6 para diseñar una entrega de exploración de procesos
con datos aprobados del orden 2. Sí es obligatorio superar los criterios del nivel de
información publicado: no presentar candidatos o categorías como productos idénticos.
Una nueva extracción para resolver faltantes o una futura evaluación LLM se programa
como trabajo separado; no se ejecuta por la sola existencia de esta hoja de ruta.

Las siguientes tareas concretas se precisan con las métricas de la entrega v1.
La deuda FORM 170 permanece registrada, sin bloquear el desarrollo prioritario.

## Alcance y evidencia de la entrega local

Se implementan únicamente fichas locales de etapas 1–3 y pruebas, con salidas nuevas
y versionadas. El inventario no demuestra completitud anual ni publicación total
de SICOES; 2026 es una ventana parcial. No se cambia scraper, originales,
manifiestos, referencias, Supabase, dashboard, canonicalización ni Graphify.
No hay descargas, APIs, LLM, commits ni push. La migración verificada en main
continúa vigente; los resultados previos se preservan como evidencia fechada.

Las fichas podrán alimentar exploración de adquisiciones, precios por etapa,
cantidades por entidad, búsqueda de descripciones y comparación de requisitos,
proveedores y posteriormente canonicalización/recurrencia. Para publicar se debe
seleccionar explícitamente recepción o contratación y controlar duplicados,
unidades, moneda, estado y cobertura. Las fichas ambiguas no son filas aditivas:
no se suman cantidades contratadas y recibidas ni se distribuyen importes entre
varios proveedores o ítems sin evidencia.
