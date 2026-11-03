# Graph Report - Sicoes-Brain  (2026-11-03)

## Corpus Check
- 69 files · ~157,056 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 4, .example 2, .graphify-bak 1)

## Summary
- 855 nodes · 1422 edges · 74 communities (58 shown, 16 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8c03b156`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- radar.py
- SICOES Items Scraper (CDP)
- RadarTable.tsx
- Dashboard Queries & Charts
- App Dependencies & Config
- Procesos Table & Search UI
- DBC Storage & PDF Conversion
- Groq AI Classifier
- Product Detail Charts
- TypeScript Config
- Project Docs & How-To
- os
- sicoes_nav.py
- SiteHeader
- Database Schema
- json
- Presentación electrónica de propuesta
- Presentación electrónica de propuesta
- App Layout & Fonts
- Presentación electrónica de propuesta
- Public SVG Icons
- PostCSS Config
- Next.js/Vercel Logos
- Graphify Knowledge Graph
- Project Root
- 24-0660-10-1477921-1-1/combinado.md
- DBC_completo.md
- DBC_recortado.md
- types.ts
- radar/page.tsx
- dbc_ocr.py
- schema_historico.sql
- c1_parse.py
- dbc_specs.py
- restaurar_procesos.py
- FORMALIZACIÓN DE LA CONTRATACIÓN
- FORMALIZACIÓN DE LA CONTRATACIÓN
- FORMALIZACIÓN DE LA CONTRATACIÓN
- ADJUDICACIÓN O DECLARATORIA DESIERTA
- DOCUMENTOS de la propuesta
- ADJUDICACIÓN O DECLARATORIA DESIERTA
- DOCUMENTOS de la propuesta
- ADJUDICACIÓN O DECLARATORIA DESIERTA
- DOCUMENTOS de la propuesta
- APERTURA DE PROPUESTAS
- Evaluación de la Propuesta Económica
- GARANTÍAS
- APERTURA DE PROPUESTAS
- Evaluación de la Propuesta Económica
- GARANTÍAS
- APERTURA DE PROPUESTAS
- Evaluación de la Propuesta Económica
- GARANTÍAS
- ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS
- SUBASTA ELECTRÓNICA
- ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS
- SUBASTA ELECTRÓNICA
- ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS
- SUBASTA ELECTRÓNICA
- CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES
- CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES
- CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES
- 24-0660-10-1499648-1-1
- 24-0660-10-1449810-1-1/combinado.md
- 24-0660-10-1464208-1-1/combinado.md
- 24-0660-10-1477921-1-1
- SUBCONTRATACIÓN
- DESCALIFICACIÓN DE PROPUESTAS
- SUBCONTRATACIÓN
- DESCALIFICACIÓN DE PROPUESTAS
- SUBCONTRATACIÓN
- DESCALIFICACIÓN DE PROPUESTAS
- 24-0660-10-1479204-1-1/combinado.md

## God Nodes (most connected - your core abstractions)
1. `SiteHeader()` - 19 edges
2. `next` - 18 edges
3. `RadarTable()` - 18 edges
4. `compilerOptions` - 16 edges
5. `correr()` - 15 edges
6. `scraping()` - 15 edges
7. `DashboardPage()` - 13 edges
8. `main()` - 12 edges
9. `abrir_formulario()` - 12 edges
10. `limpiar()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `radar.py (módulo monitor)` --references--> `radar.py (buscar/filtrar/bajar/clasificar)`  [INFERRED]
  monitor/README.md → COMO_CORRER.md
- `monitor requirements (playwright/pymupdf/OCR)` --shares_data_with--> `scraper requirements (playwright/bs4/lxml)`  [INFERRED]
  monitor/requirements.txt → scraper/requirements.txt
- `Radar de Convocatorias SICOES` --references--> `scraper requirements (playwright/bs4/lxml)`  [INFERRED]
  monitor/README.md → scraper/requirements.txt
- `Next.js app (dashboard Vercel)` --shares_data_with--> `Tabla convocatorias_radar (Supabase)`  [INFERRED]
  app/README.md → monitor/README.md
- `Radar run workflow (sesión típica)` --references--> `Next.js app (dashboard Vercel)`  [EXTRACTED]
  COMO_CORRER.md → app/README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Clasificación por rubro doble filtro** — monitor_doble_filtro_or, monitor_rubros_py, monitor_clasificador_ia_py [EXTRACTED 0.85]
- **Radar session pipeline (buscar→specs→dashboard)** — como_correr_radar_py, como_correr_dbc_specs_py, app_nextjs_project [EXTRACTED 0.90]

## Communities (74 total, 16 thin omitted)

### Community 0 - "radar.py"
Cohesion: 0.08
Nodes (24): catalogo_erp(), cuces_existentes(), ejemplos_entrenamiento(), _objetos(), _headers(), limpiar_documentos_vencidos(), limpiar_storage_descartados(), marcar_dbc() (+16 more)

### Community 1 - "SICOES Items Scraper (CDP)"
Cohesion: 0.07
Nodes (40): _abrir_form_intento(), abrir_formulario(), activar_sesion_con_formulario(), armar_descripcion(), buscar(), _buscar_y_verificar(), _cerrar_modales(), codigo_unspsc_valido() (+32 more)

### Community 2 - "RadarTable.tsx"
Cohesion: 0.12
Nodes (15): cuce4(), diasRestantes(), fmtBs(), HistorialBadge(), labelFechaPub(), labelMotivo(), norm(), RadarTable() (+7 more)

### Community 3 - "Dashboard Queries & Charts"
Cohesion: 0.07
Nodes (37): DashboardPage(), dynamic, formatMonto(), Props, StatCard(), dynamic, EstadoBadge(), formatMonto() (+29 more)

### Community 4 - "App Dependencies & Config"
Cohesion: 0.08
Nodes (33): eslintConfig, dependencies, next@16.2.9, react@19.2.4, react-dom@19.2.4, @supabase/supabase-js@^2.108.1, devDependencies, eslint@^9 (+25 more)

### Community 5 - "Procesos Table & Search UI"
Cohesion: 0.18
Nodes (15): Campo(), dynamic, formatFecha(), formatMonto(), ProcesoPage(), Props, colorMap, EstadoBadge() (+7 more)

### Community 6 - "DBC Storage & PDF Conversion"
Cohesion: 0.09
Nodes (19): _buscar(), _comprimir_pdf(), _content_type(), _conv_libreoffice(), _conv_textutil_chromium(), convertir_a_pdf(), cuce4(), limpiar_storage() (+11 more)

### Community 7 - "Groq AI Classifier"
Cohesion: 0.11
Nodes (12): _bloque_catalogo(), _bloque_ejemplos(), _cargar_keys(), clasificar_lote(), _pedir(), _dedup_items(), _es_tpd(), estructurar_c1() (+4 more)

### Community 8 - "Product Detail Charts"
Cohesion: 0.13
Nodes (17): recharts@^3.8.1, fmt(), fmtMonto(), ProductoPage(), Props, StatCard(), MESES, Point (+9 more)

### Community 9 - "TypeScript Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 10 - "Project Docs & How-To"
Cohesion: 0.13
Nodes (15): Next.js app (dashboard Vercel), c1_parse.py (Formularios C-1), dbc_specs.py (extraer specs del DBC), erp_sync.py (refrescar historial ERP), radar.py (buscar/filtrar/bajar/clasificar), Radar run workflow (sesión típica), clasificador_ia.py (Groq semántico), Tabla convocatorias_radar (Supabase) (+7 more)

### Community 11 - "os"
Cohesion: 0.15
Nodes (13): _a_markdown(), _abrir_form_intento(), abrir_formulario_html(), buscar(), _cerrar_modales(), descargar_token(), _ext_desde_headers(), extraer_filas() (+5 more)

### Community 12 - "sicoes_nav.py"
Cohesion: 0.08
Nodes (21): recolectar(), cuce4(), main(), reconectar(), relevantes(), _asegurar_portal(), buscar_por_cuce4(), buscar_por_fechas() (+13 more)

### Community 13 - "SiteHeader"
Cohesion: 0.14
Nodes (18): Barra(), diasRestantes(), dynamic, ErpRow, MetricasPage(), RadarRow, Tile(), dias() (+10 more)

### Community 14 - "Database Schema"
Cohesion: 0.31
Nodes (10): idx_erp_c1_sicoes, idx_erp_prod_sicoes, idx_radar_fecha_pres, idx_radar_fecha_pub, idx_radar_relevante, public.convocatoria_specs, public.convocatorias_radar, public.erp_c1 (+2 more)

### Community 15 - "json"
Cohesion: 0.18
Nodes (8): main(), _rpc_export(), _send(), _get(), main(), _patch(), main(), relevantes()

### Community 16 - "Presentación electrónica de propuesta"
Cohesion: 0.10
Nodes (20): Cuando en la presentación de propuestas electrónicas se haya considerado utilizar el depósito por concepto de Garantía de Seriedad de Propuesta, éste deberá ser efectuado al menos dos (2) horas antes de la conclusión del plazo para la presentación de propuestas, cuando sea realizado en días hábiles, o prever la anticipación de un (1) día hábil en caso de ser realizado en días sábados, domingos o feriados, para una asociación adecuada a la presentación de la misma., Cuando en la presentación de propuestas electrónicas se haya considerado utilizar la Garantía de Seriedad de Propuesta, ésta deberá ser presentada en sobre cerrado y con cinta adhesiva transparente sobre las firmas y sellos, dirigido a la entidad convocante, citando el Número de Proceso, el Código Único de Contrataciones Estatales (CUCE) y el objeto de la Convocatoria., Cuando la entidad haya solicitado la presentación de muestras, se deberá realizar la presentación de las mismas en sobre cerrado y con cinta adhesiva transparente sobre las firmas y sellos, dirigido a la entidad convocante, citando el Número de Proceso, el Código Único de Contrataciones Estatales (CUCE) y el objeto de la Convocatoria., El Proponente debe autentificarse mediante sus credenciales de acceso al RUPE y seleccionar el proceso de contratación en el que desea participar según el CUCE., El proponente deberá aceptar las condiciones del sistema para la presentación de propuestas electrónicas y enviar su propuesta., El proponente que haya retirado su propuesta podrá realizar la presentación de una nueva propuesta, hasta antes del plazo límite para el cierre de presentación, establecido en el cronograma de plazos del DBC., La devolución de la Garantía de Seriedad de Propuesta será solicitada por el proponente por escrito. La entidad procederá con la devolución bajo constancia escrita y liberándose de cualquier responsabilidad. En caso del depósito, su devolución se realizará de conformidad con lo previsto en el Reglamento de Contrataciones con el Apoyo de Medios Electrónicos., La presentación de propuestas electrónicas se realizará a través del RUPE. (+12 more)

### Community 17 - "Presentación electrónica de propuesta"
Cohesion: 0.10
Nodes (20): Cuando en la presentación de propuestas electrónicas se haya considerado utilizar el depósito por concepto de Garantía de Seriedad de Propuesta, éste deberá ser efectuado al menos dos (2) horas antes de la conclusión del plazo para la presentación de propuestas, cuando sea realizado en días hábiles, o prever la anticipación de un (1) día hábil en caso de ser realizado en días sábados, domingos o feriados, para una asociación adecuada a la presentación de la misma., Cuando en la presentación de propuestas electrónicas se haya considerado utilizar la Garantía de Seriedad de Propuesta, ésta deberá ser presentada en sobre cerrado y con cinta adhesiva transparente sobre las firmas y sellos, dirigido a la entidad convocante, citando el Número de Proceso, el Código Único de Contrataciones Estatales (CUCE) y el objeto de la Convocatoria., Cuando la entidad haya solicitado la presentación de muestras, se deberá realizar la presentación de las mismas en sobre cerrado y con cinta adhesiva transparente sobre las firmas y sellos, dirigido a la entidad convocante, citando el Número de Proceso, el Código Único de Contrataciones Estatales (CUCE) y el objeto de la Convocatoria., El Proponente debe autentificarse mediante sus credenciales de acceso al RUPE y seleccionar el proceso de contratación en el que desea participar según el CUCE., El proponente deberá aceptar las condiciones del sistema para la presentación de propuestas electrónicas y enviar su propuesta., El proponente que haya retirado su propuesta podrá realizar la presentación de una nueva propuesta, hasta antes del plazo límite para el cierre de presentación, establecido en el cronograma de plazos del DBC., La devolución de la Garantía de Seriedad de Propuesta será solicitada por el proponente por escrito. La entidad procederá con la devolución bajo constancia escrita y liberándose de cualquier responsabilidad. En caso del depósito, su devolución se realizará de conformidad con lo previsto en el Reglamento de Contrataciones con el Apoyo de Medios Electrónicos., La presentación de propuestas electrónicas se realizará a través del RUPE. (+12 more)

### Community 18 - "App Layout & Fonts"
Cohesion: 0.18
Nodes (5): nextConfig, geistMono, geistSans, metadata, next

### Community 19 - "Presentación electrónica de propuesta"
Cohesion: 0.10
Nodes (20): Cuando en la presentación de propuestas electrónicas se haya considerado utilizar el depósito por concepto de Garantía de Seriedad de Propuesta, éste deberá ser efectuado al menos dos (2) horas antes de la conclusión del plazo para la presentación de propuestas, cuando sea realizado en días hábiles, o prever la anticipación de un (1) día hábil en caso de ser realizado en días sábados, domingos o feriados, para una asociación adecuada a la presentación de la misma., Cuando en la presentación de propuestas electrónicas se haya considerado utilizar la Garantía de Seriedad de Propuesta, ésta deberá ser presentada en sobre cerrado y con cinta adhesiva transparente sobre las firmas y sellos, dirigido a la entidad convocante, citando el Número de Proceso, el Código Único de Contrataciones Estatales (CUCE) y el objeto de la Convocatoria., Cuando la entidad haya solicitado la presentación de muestras, se deberá realizar la presentación de las mismas en sobre cerrado y con cinta adhesiva transparente sobre las firmas y sellos, dirigido a la entidad convocante, citando el Número de Proceso, el Código Único de Contrataciones Estatales (CUCE) y el objeto de la Convocatoria., El Proponente debe autentificarse mediante sus credenciales de acceso al RUPE y seleccionar el proceso de contratación en el que desea participar según el CUCE., El proponente deberá aceptar las condiciones del sistema para la presentación de propuestas electrónicas y enviar su propuesta., El proponente que haya retirado su propuesta podrá realizar la presentación de una nueva propuesta, hasta antes del plazo límite para el cierre de presentación, establecido en el cronograma de plazos del DBC., La devolución de la Garantía de Seriedad de Propuesta será solicitada por el proponente por escrito. La entidad procederá con la devolución bajo constancia escrita y liberándose de cualquier responsabilidad. En caso del depósito, su devolución se realizará de conformidad con lo previsto en el Reglamento de Contrataciones con el Apoyo de Medios Electrónicos., La presentación de propuestas electrónicas se realizará a través del RUPE. (+12 more)

### Community 20 - "Public SVG Icons"
Cohesion: 0.67
Nodes (3): File Document Icon, Globe Icon, Window UI Icon

### Community 25 - "24-0660-10-1477921-1-1/combinado.md"
Cohesion: 0.11
Nodes (18): CANCELACIÓN, SUSPENSIÓN Y ANULACIÓN DEL PROCESO DE CONTRATACIÓN, CIERRE DEL CONTRATO Y PAGO, CONTENIDO DEL INFORME DE EVALUACIÓN Y RECOMENDACIÓN, CONVOCATORIA Y DATOS GENERALES DE LA CONTRATACIÓN, CRONOGRAMA DE PLAZOS, DECLARATORIA DESIERTA, ENTREGA DE BIENES, ESPECIFICACIONES TÉCNICAS Y CONDICIONES TÉCNICAS REQUERIDAS DEL BIEN (+10 more)

### Community 26 - "DBC_completo.md"
Cohesion: 0.11
Nodes (18): CANCELACIÓN, SUSPENSIÓN Y ANULACIÓN DEL PROCESO DE CONTRATACIÓN, CIERRE DEL CONTRATO Y PAGO, CONTENIDO DEL INFORME DE EVALUACIÓN Y RECOMENDACIÓN, CONVOCATORIA Y DATOS GENERALES DE LA CONTRATACIÓN, CRONOGRAMA DE PLAZOS, DECLARATORIA DESIERTA, ENTREGA DE BIENES, ESPECIFICACIONES TÉCNICAS Y CONDICIONES TÉCNICAS REQUERIDAS DEL BIEN (+10 more)

### Community 27 - "DBC_recortado.md"
Cohesion: 0.11
Nodes (18): CANCELACIÓN, SUSPENSIÓN Y ANULACIÓN DEL PROCESO DE CONTRATACIÓN, CIERRE DEL CONTRATO Y PAGO, CONTENIDO DEL INFORME DE EVALUACIÓN Y RECOMENDACIÓN, CONVOCATORIA Y DATOS GENERALES DE LA CONTRATACIÓN, CRONOGRAMA DE PLAZOS, DECLARATORIA DESIERTA, ENTREGA DE BIENES, ESPECIFICACIONES TÉCNICAS Y CONDICIONES TÉCNICAS REQUERIDAS DEL BIEN (+10 more)

### Community 28 - "types.ts"
Cohesion: 0.21
Nodes (13): ProcesosPage(), Props, Pagination(), Props, Props, SearchFilters(), getProcesos(), Entidad (+5 more)

### Community 29 - "radar/page.tsx"
Cohesion: 0.19
Nodes (15): dias(), diasDesde(), dynamic, getErpMap(), getErpProductos(), getRadar(), getSpecsMap(), hoyBolivia() (+7 more)

### Community 30 - "dbc_ocr.py"
Cohesion: 0.25
Nodes (7): _descargar(), _get(), main(), _ocr_pdf(), _pdf_url(), _tesseract_ok(), _upsert()

### Community 31 - "schema_historico.sql"
Cohesion: 0.32
Nodes (11): idx_hist_canon_cat, idx_hist_item_canonico, idx_hist_item_cuce, idx_hist_item_entidad, idx_hist_item_unspsc, idx_hist_proc_anio, idx_hist_proc_entidad, idx_hist_proc_fecha (+3 more)

### Community 32 - "c1_parse.py"
Cohesion: 0.31
Nodes (6): _dest(), _erp_download(), listar_c1(), main(), _texto_pdf(), _ya_parseados()

### Community 33 - "dbc_specs.py"
Cohesion: 0.39
Nodes (6): _descargar(), _get(), main(), _pdf_url(), _texto_pdf(), _upsert()

### Community 34 - "restaurar_procesos.py"
Cohesion: 0.48
Nodes (3): clean(), main(), post_batch()

### Community 35 - "FORMALIZACIÓN DE LA CONTRATACIÓN"
Cohesion: 0.29
Nodes (7): Cuando el proponente adjudicado desista de forma expresa o tácita de formalizar la contratación, mediante contrato u orden de compra, su propuesta será descalificada, procediéndose a la revisión de la siguiente propuesta mejor evaluada. En caso de que la justificación del desistimiento expreso no sea por causas de fuerza mayor, caso fortuito u otras causas debidamente justificadas y aceptadas por la entidad, además, se consolidará el depósito o se ejecutará la Garantía de Seriedad de Propuesta, si esta hubiese sido solicitada y se informará al SICOES, en cumplimiento al inciso c) del Parágrafo I del Artículo 49 de las NB-SABS., El proponente adjudicado deberá presentar, para la formalización de la contratación, mediante contrato u orden de compra, los originales o fotocopias legalizadas de los documentos señalados en el Formulario de Presentación de Propuesta (Formulario A-1), excepto aquella documentación cuya información se encuentre consignada en el Certificado del RUPE., En caso de convenirse anticipo, el proponente adjudicado deberá presentar la Garantía de Correcta Inversión de Anticipo, equivalente al cien por ciento (100%) del anticipo solicitado, dentro de los plazos previstos en el contrato., En los casos que se necesite ampliar plazos, el RPA deberá autorizar la modificación del cronograma de plazos a partir de la fecha de emisión del documento de adjudicación., FORMALIZACIÓN DE LA CONTRATACIÓN, La entidad convocante deberá establecer el plazo de entrega de documentos, que no deberá ser menor a cuatro (4) días hábiles, para contrataciones hasta Bs200.000.- (DOSCIENTOS MIL 00/100 BOLIVIANOS), computables a partir del día siguiente hábil de su notificación y para contrataciones mayores a Bs200.000.- (DOSCIENTOS MIL 00/100 BOLIVIANOS), el plazo de entrega de documentos será computable a partir del día siguiente hábil al vencimiento del plazo para la interposición de Recursos Administrativos de Impugnación., Si el proponente adjudicado presentase los documentos antes del plazo otorgado, el proceso deberá continuar.

### Community 36 - "FORMALIZACIÓN DE LA CONTRATACIÓN"
Cohesion: 0.29
Nodes (7): Cuando el proponente adjudicado desista de forma expresa o tácita de formalizar la contratación, mediante contrato u orden de compra, su propuesta será descalificada, procediéndose a la revisión de la siguiente propuesta mejor evaluada. En caso de que la justificación del desistimiento expreso no sea por causas de fuerza mayor, caso fortuito u otras causas debidamente justificadas y aceptadas por la entidad, además, se consolidará el depósito o se ejecutará la Garantía de Seriedad de Propuesta, si esta hubiese sido solicitada y se informará al SICOES, en cumplimiento al inciso c) del Parágrafo I del Artículo 49 de las NB-SABS., El proponente adjudicado deberá presentar, para la formalización de la contratación, mediante contrato u orden de compra, los originales o fotocopias legalizadas de los documentos señalados en el Formulario de Presentación de Propuesta (Formulario A-1), excepto aquella documentación cuya información se encuentre consignada en el Certificado del RUPE., En caso de convenirse anticipo, el proponente adjudicado deberá presentar la Garantía de Correcta Inversión de Anticipo, equivalente al cien por ciento (100%) del anticipo solicitado, dentro de los plazos previstos en el contrato., En los casos que se necesite ampliar plazos, el RPA deberá autorizar la modificación del cronograma de plazos a partir de la fecha de emisión del documento de adjudicación., FORMALIZACIÓN DE LA CONTRATACIÓN, La entidad convocante deberá establecer el plazo de entrega de documentos, que no deberá ser menor a cuatro (4) días hábiles, para contrataciones hasta Bs200.000.- (DOSCIENTOS MIL 00/100 BOLIVIANOS), computables a partir del día siguiente hábil de su notificación y para contrataciones mayores a Bs200.000.- (DOSCIENTOS MIL 00/100 BOLIVIANOS), el plazo de entrega de documentos será computable a partir del día siguiente hábil al vencimiento del plazo para la interposición de Recursos Administrativos de Impugnación., Si el proponente adjudicado presentase los documentos antes del plazo otorgado, el proceso deberá continuar.

### Community 37 - "FORMALIZACIÓN DE LA CONTRATACIÓN"
Cohesion: 0.29
Nodes (7): Cuando el proponente adjudicado desista de forma expresa o tácita de formalizar la contratación, mediante contrato u orden de compra, su propuesta será descalificada, procediéndose a la revisión de la siguiente propuesta mejor evaluada. En caso de que la justificación del desistimiento expreso no sea por causas de fuerza mayor, caso fortuito u otras causas debidamente justificadas y aceptadas por la entidad, además, se consolidará el depósito o se ejecutará la Garantía de Seriedad de Propuesta, si esta hubiese sido solicitada y se informará al SICOES, en cumplimiento al inciso c) del Parágrafo I del Artículo 49 de las NB-SABS., El proponente adjudicado deberá presentar, para la formalización de la contratación, mediante contrato u orden de compra, los originales o fotocopias legalizadas de los documentos señalados en el Formulario de Presentación de Propuesta (Formulario A-1), excepto aquella documentación cuya información se encuentre consignada en el Certificado del RUPE., En caso de convenirse anticipo, el proponente adjudicado deberá presentar la Garantía de Correcta Inversión de Anticipo, equivalente al cien por ciento (100%) del anticipo solicitado, dentro de los plazos previstos en el contrato., En los casos que se necesite ampliar plazos, el RPA deberá autorizar la modificación del cronograma de plazos a partir de la fecha de emisión del documento de adjudicación., FORMALIZACIÓN DE LA CONTRATACIÓN, La entidad convocante deberá establecer el plazo de entrega de documentos, que no deberá ser menor a cuatro (4) días hábiles, para contrataciones hasta Bs200.000.- (DOSCIENTOS MIL 00/100 BOLIVIANOS), computables a partir del día siguiente hábil de su notificación y para contrataciones mayores a Bs200.000.- (DOSCIENTOS MIL 00/100 BOLIVIANOS), el plazo de entrega de documentos será computable a partir del día siguiente hábil al vencimiento del plazo para la interposición de Recursos Administrativos de Impugnación., Si el proponente adjudicado presentase los documentos antes del plazo otorgado, el proceso deberá continuar.

### Community 38 - "ADJUDICACIÓN O DECLARATORIA DESIERTA"
Cohesion: 0.33
Nodes (6): ADJUDICACIÓN O DECLARATORIA DESIERTA, El Documento o Resolución de Adjudicación o Declaratoria Desierta será motivada y contendrá mínimamente la siguiente información:, El Documento o Resolución de Adjudicación o Declaratoria Desierta será notificada a los proponentes de acuerdo con lo establecido en el Artículo 51 de las NB-SABS. La notificación, deberá incluir copia de la Resolución y del Informe de Evaluación y Recomendación de Adjudicación o Declaratoria Desierta. En contrataciones hasta Bs200.000 (DOSCIENTOS MIL 00/100 BOLIVIANOS), el documento de adjudicación o declaratoria desierta deberá ser publicado en el SICOES, para efectos de comunicación., El RPA, recibido el Informe de Evaluación y Recomendación de Adjudicación o Declaratoria Desierta y dentro del plazo fijado en el cronograma de plazos, emitirá la Adjudicación o Declaratoria Desierta., En caso de que el RPA solicite al Responsable de Evaluación o la Comisión de Calificación la complementación o sustentación del informe, podrá autorizar la modificación del cronograma de plazos a partir de la fecha establecida para la emisión de la Adjudicación o Declaratoria Desierta. El nuevo cronograma de plazos deberá ser publicado en el SICOES., Para contrataciones mayores a Bs200.000 (DOSCIENTOS MIL 00/100 BOLIVIANOS), el RPA deberá adjudicar o declarar desierta la contratación, mediante Resolución expresa, para contrataciones menores o iguales a dicho monto la entidad determinará el documento de adjudicación o declaratoria desierta.

### Community 39 - "DOCUMENTOS de la propuesta"
Cohesion: 0.33
Nodes (6): Cada asociado, en forma independiente, deberá presentar el Formulario de Identificación de Integrantes de la Asociación Accidental (Formulario A-2d)., DOCUMENTOS de la propuesta, En el caso de Asociaciones Accidentales, los documentos deberán presentarse diferenciando los que corresponden a la Asociación y los que corresponden a cada asociado., La documentación conjunta a presentar, es la siguiente:, La propuesta tendrá una validez de treinta (30) días calendario, desde la fecha fijada para la apertura de propuestas., Los documentos que deben presentar los proponentes son:

### Community 40 - "ADJUDICACIÓN O DECLARATORIA DESIERTA"
Cohesion: 0.33
Nodes (6): ADJUDICACIÓN O DECLARATORIA DESIERTA, El Documento o Resolución de Adjudicación o Declaratoria Desierta será motivada y contendrá mínimamente la siguiente información:, El Documento o Resolución de Adjudicación o Declaratoria Desierta será notificada a los proponentes de acuerdo con lo establecido en el Artículo 51 de las NB-SABS. La notificación, deberá incluir copia de la Resolución y del Informe de Evaluación y Recomendación de Adjudicación o Declaratoria Desierta. En contrataciones hasta Bs200.000 (DOSCIENTOS MIL 00/100 BOLIVIANOS), el documento de adjudicación o declaratoria desierta deberá ser publicado en el SICOES, para efectos de comunicación., El RPA, recibido el Informe de Evaluación y Recomendación de Adjudicación o Declaratoria Desierta y dentro del plazo fijado en el cronograma de plazos, emitirá la Adjudicación o Declaratoria Desierta., En caso de que el RPA solicite al Responsable de Evaluación o la Comisión de Calificación la complementación o sustentación del informe, podrá autorizar la modificación del cronograma de plazos a partir de la fecha establecida para la emisión de la Adjudicación o Declaratoria Desierta. El nuevo cronograma de plazos deberá ser publicado en el SICOES., Para contrataciones mayores a Bs200.000 (DOSCIENTOS MIL 00/100 BOLIVIANOS), el RPA deberá adjudicar o declarar desierta la contratación, mediante Resolución expresa, para contrataciones menores o iguales a dicho monto la entidad determinará el documento de adjudicación o declaratoria desierta.

### Community 41 - "DOCUMENTOS de la propuesta"
Cohesion: 0.33
Nodes (6): Cada asociado, en forma independiente, deberá presentar el Formulario de Identificación de Integrantes de la Asociación Accidental (Formulario A-2d)., DOCUMENTOS de la propuesta, En el caso de Asociaciones Accidentales, los documentos deberán presentarse diferenciando los que corresponden a la Asociación y los que corresponden a cada asociado., La documentación conjunta a presentar, es la siguiente:, La propuesta tendrá una validez de treinta (30) días calendario, desde la fecha fijada para la apertura de propuestas., Los documentos que deben presentar los proponentes son:

### Community 42 - "ADJUDICACIÓN O DECLARATORIA DESIERTA"
Cohesion: 0.33
Nodes (6): ADJUDICACIÓN O DECLARATORIA DESIERTA, El Documento o Resolución de Adjudicación o Declaratoria Desierta será motivada y contendrá mínimamente la siguiente información:, El Documento o Resolución de Adjudicación o Declaratoria Desierta será notificada a los proponentes de acuerdo con lo establecido en el Artículo 51 de las NB-SABS. La notificación, deberá incluir copia de la Resolución y del Informe de Evaluación y Recomendación de Adjudicación o Declaratoria Desierta. En contrataciones hasta Bs200.000 (DOSCIENTOS MIL 00/100 BOLIVIANOS), el documento de adjudicación o declaratoria desierta deberá ser publicado en el SICOES, para efectos de comunicación., El RPA, recibido el Informe de Evaluación y Recomendación de Adjudicación o Declaratoria Desierta y dentro del plazo fijado en el cronograma de plazos, emitirá la Adjudicación o Declaratoria Desierta., En caso de que el RPA solicite al Responsable de Evaluación o la Comisión de Calificación la complementación o sustentación del informe, podrá autorizar la modificación del cronograma de plazos a partir de la fecha establecida para la emisión de la Adjudicación o Declaratoria Desierta. El nuevo cronograma de plazos deberá ser publicado en el SICOES., Para contrataciones mayores a Bs200.000 (DOSCIENTOS MIL 00/100 BOLIVIANOS), el RPA deberá adjudicar o declarar desierta la contratación, mediante Resolución expresa, para contrataciones menores o iguales a dicho monto la entidad determinará el documento de adjudicación o declaratoria desierta.

### Community 43 - "DOCUMENTOS de la propuesta"
Cohesion: 0.33
Nodes (6): Cada asociado, en forma independiente, deberá presentar el Formulario de Identificación de Integrantes de la Asociación Accidental (Formulario A-2d)., DOCUMENTOS de la propuesta, En el caso de Asociaciones Accidentales, los documentos deberán presentarse diferenciando los que corresponden a la Asociación y los que corresponden a cada asociado., La documentación conjunta a presentar, es la siguiente:, La propuesta tendrá una validez de treinta (30) días calendario, desde la fecha fijada para la apertura de propuestas., Los documentos que deben presentar los proponentes son:

### Community 44 - "APERTURA DE PROPUESTAS"
Cohesion: 0.40
Nodes (5): APERTURA DE PROPUESTAS, Concluido el Acto de Apertura, la nómina de proponentes será remitida, por el Responsable de Evaluación o la Comisión de Calificación al RPA en forma inmediata, para efectos de eventual excusa., Durante el Acto de Apertura de propuestas no se descalificará a ningún proponente, siendo esta una atribución del Responsable de Evaluación o de la Comisión de Calificación en el proceso de evaluación., El Acto de Apertura comprenderá:, Inmediatamente después del cierre del plazo de presentación de propuestas o del cierre de la Subasta Electrónica si esta hubiera sido programada, el Responsable de Evaluación o la Comisión de Calificación, procederá a la apertura de las propuestas en acto público en la fecha, hora y lugar señalados en el presente DBC.

### Community 45 - "Evaluación de la Propuesta Económica"
Cohesion: 0.40
Nodes (5): **Determinación de la Propuesta con el Precio Evaluado Más Bajo**, Evaluación de la Propuesta Económica, Evaluación de la Propuesta Técnica, MÉTODO DE SELECCIÓN Y ADJUDICACIÓN PRECIO EVALUADO MÁS BAJO, **Reporte electrónico**

### Community 46 - "GARANTÍAS"
Cohesion: 0.40
Nodes (5): Devolución de la Garantía de Seriedad de Propuesta, Ejecución de la Garantía de Seriedad de Propuesta, El tratamiento de ejecución y devolución de las Garantías de: Cumplimiento de Contrato, Correcta Inversión de Anticipo y Funcionamiento de Maquinaria y/o Equipo, se establecerá en el contrato., GARANTÍAS, Las garantías requeridas, de acuerdo con el objeto, son:

### Community 47 - "APERTURA DE PROPUESTAS"
Cohesion: 0.40
Nodes (5): APERTURA DE PROPUESTAS, Concluido el Acto de Apertura, la nómina de proponentes será remitida, por el Responsable de Evaluación o la Comisión de Calificación al RPA en forma inmediata, para efectos de eventual excusa., Durante el Acto de Apertura de propuestas no se descalificará a ningún proponente, siendo esta una atribución del Responsable de Evaluación o de la Comisión de Calificación en el proceso de evaluación., El Acto de Apertura comprenderá:, Inmediatamente después del cierre del plazo de presentación de propuestas o del cierre de la Subasta Electrónica si esta hubiera sido programada, el Responsable de Evaluación o la Comisión de Calificación, procederá a la apertura de las propuestas en acto público en la fecha, hora y lugar señalados en el presente DBC.

### Community 48 - "Evaluación de la Propuesta Económica"
Cohesion: 0.40
Nodes (5): **Determinación de la Propuesta con el Precio Evaluado Más Bajo**, Evaluación de la Propuesta Económica, Evaluación de la Propuesta Técnica, MÉTODO DE SELECCIÓN Y ADJUDICACIÓN PRECIO EVALUADO MÁS BAJO, **Reporte electrónico**

### Community 49 - "GARANTÍAS"
Cohesion: 0.40
Nodes (5): Devolución de la Garantía de Seriedad de Propuesta, Ejecución de la Garantía de Seriedad de Propuesta, El tratamiento de ejecución y devolución de las Garantías de: Cumplimiento de Contrato, Correcta Inversión de Anticipo y Funcionamiento de Maquinaria y/o Equipo, se establecerá en el contrato., GARANTÍAS, Las garantías requeridas, de acuerdo con el objeto, son:

### Community 50 - "APERTURA DE PROPUESTAS"
Cohesion: 0.40
Nodes (5): APERTURA DE PROPUESTAS, Concluido el Acto de Apertura, la nómina de proponentes será remitida, por el Responsable de Evaluación o la Comisión de Calificación al RPA en forma inmediata, para efectos de eventual excusa., Durante el Acto de Apertura de propuestas no se descalificará a ningún proponente, siendo esta una atribución del Responsable de Evaluación o de la Comisión de Calificación en el proceso de evaluación., El Acto de Apertura comprenderá:, Inmediatamente después del cierre del plazo de presentación de propuestas o del cierre de la Subasta Electrónica si esta hubiera sido programada, el Responsable de Evaluación o la Comisión de Calificación, procederá a la apertura de las propuestas en acto público en la fecha, hora y lugar señalados en el presente DBC.

### Community 51 - "Evaluación de la Propuesta Económica"
Cohesion: 0.40
Nodes (5): **Determinación de la Propuesta con el Precio Evaluado Más Bajo**, Evaluación de la Propuesta Económica, Evaluación de la Propuesta Técnica, MÉTODO DE SELECCIÓN Y ADJUDICACIÓN PRECIO EVALUADO MÁS BAJO, **Reporte electrónico**

### Community 52 - "GARANTÍAS"
Cohesion: 0.40
Nodes (5): Devolución de la Garantía de Seriedad de Propuesta, Ejecución de la Garantía de Seriedad de Propuesta, El tratamiento de ejecución y devolución de las Garantías de: Cumplimiento de Contrato, Correcta Inversión de Anticipo y Funcionamiento de Maquinaria y/o Equipo, se establecerá en el contrato., GARANTÍAS, Las garantías requeridas, de acuerdo con el objeto, son:

### Community 53 - "ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS"
Cohesion: 0.50
Nodes (4): ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS, Consultas Escritas sobre el DBC, Inspección Previa, Reunión Informativa de Aclaración

### Community 54 - "SUBASTA ELECTRÓNICA"
Cohesion: 0.50
Nodes (4): Condiciones para la realización de la Subasta Electrónica, Procedimiento, Programación, Duración y Resultados, SUBASTA ELECTRÓNICA

### Community 55 - "ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS"
Cohesion: 0.50
Nodes (4): ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS, Consultas Escritas sobre el DBC, Inspección Previa, Reunión Informativa de Aclaración

### Community 56 - "SUBASTA ELECTRÓNICA"
Cohesion: 0.50
Nodes (4): Condiciones para la realización de la Subasta Electrónica, Procedimiento, Programación, Duración y Resultados, SUBASTA ELECTRÓNICA

### Community 57 - "ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS"
Cohesion: 0.50
Nodes (4): ACTIVIDADES ADMINISTRATIVAS PREVIAS A LA PRESENTACIÓN DE PROPUESTAS, Consultas Escritas sobre el DBC, Inspección Previa, Reunión Informativa de Aclaración

### Community 58 - "SUBASTA ELECTRÓNICA"
Cohesion: 0.50
Nodes (4): Condiciones para la realización de la Subasta Electrónica, Procedimiento, Programación, Duración y Resultados, SUBASTA ELECTRÓNICA

### Community 59 - "CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES"
Cohesion: 0.67
Nodes (3): CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES, Se deberán considerar como criterios de subsanabilidad, los siguientes:, Se deberán considerar errores no subsanables, siendo objeto de descalificación, los siguientes:

### Community 60 - "CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES"
Cohesion: 0.67
Nodes (3): CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES, Se deberán considerar como criterios de subsanabilidad, los siguientes:, Se deberán considerar errores no subsanables, siendo objeto de descalificación, los siguientes:

### Community 61 - "CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES"
Cohesion: 0.67
Nodes (3): CRITERIOS DE SUBSANABILIDAD Y ERRORES NO SUBSANABLES, Se deberán considerar como criterios de subsanabilidad, los siguientes:, Se deberán considerar errores no subsanables, siendo objeto de descalificación, los siguientes:

## Knowledge Gaps
- **12 isolated node(s):** `erp_sync.py (refrescar historial ERP)`, `clasificador_ia.py (Groq semántico)`, `monitor requirements (playwright/pymupdf/OCR)`, `rubros.py (diccionario de términos)`, `Bucket público dbc (Supabase Storage)` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 424 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next` connect `App Layout & Fonts` to `RadarTable.tsx`, `Dashboard Queries & Charts`, `App Dependencies & Config`, `Procesos Table & Search UI`, `Product Detail Charts`, `SiteHeader`, `types.ts`, `radar/page.tsx`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **What connects `erp_sync.py (refrescar historial ERP)`, `clasificador_ia.py (Groq semántico)`, `monitor requirements (playwright/pymupdf/OCR)` to the rest of the system?**
  _12 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `radar.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08484848484848485 - nodes in this community are weakly interconnected._
- **Why does `SiteHeader()` connect `SiteHeader` to `Dashboard Queries & Charts`, `Procesos Table & Search UI`, `Product Detail Charts`, `types.ts`, `radar/page.tsx`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Should `SICOES Items Scraper (CDP)` be split into smaller, more focused modules?**
  _Cohesion score 0.07291666666666667 - nodes in this community are weakly interconnected._
- **Why does `RadarTable()` connect `RadarTable.tsx` to `radar/page.tsx`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **Should `RadarTable.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.11956521739130435 - nodes in this community are weakly interconnected._