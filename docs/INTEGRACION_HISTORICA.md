# Integración selectiva del histórico — 2026-11-09

Integración aditiva en main; no se hizo merge general, commits ni push. Todos los archivos incorporados son nuevos. El worktree experimental permanece intacto.

## Respaldo y protección

Respaldo verificado: `/private/tmp/sicoes-integracion-20261109T145337Z`. 555 archivos rastreados/no rastreados no ignorados de ambos worktrees, parches pendientes, metadatos Git y bundle verificado. No contiene una migración de datos ignorados. El respaldo reside en /private/tmp, una ubicación temporal.

Los 555 archivos preexistentes mantienen SHA256 y permisos. Incluye scrapers/comandos anteriores, Graphify, skills, dashboard y canonicalización. No se reemplazó código existente; no apareció un conflicto que requiriera detener la incorporación.

## Inventario exacto

39 archivos incorporados, incluidos este informe y el inventario JSON.

| Origen experimental | Destino en main | Adaptación |
|---|---|---|
| prueba2/__init__.py | `scraper/historico_local/__init__.py` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/historico_http_paginas.py | `scraper/historico_local/historico_http_paginas.py` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/historico_http_directo.py | `scraper/historico_local/historico_http_directo.py` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/http_forms.py | `scraper/historico_local/http_forms.py` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/storage.py | `scraper/historico_local/storage.py` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/parsing.py | `scraper/historico_local/parsing.py` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/brave_bootstrap.py | `scraper/historico_local/brave_bootstrap.py` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/schema.sql | `scraper/historico_local/schema.sql` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| prueba2/.gitignore | `scraper/historico_local/.gitignore` | Paquete/rutas definitivos; funciones internas conservadas. Schema auxiliar conserva Store sin incorporar su motor piloto. |
| Nuevo | `scraper/historico_local/__main__.py` | Entrada operativa por páginas; sin CLI del piloto. |
| prueba2/requirements.txt | `scraper/historico_local/requirements.txt` | Dependencias efectivas; no se instalan ni actualizan en esta integración. |
| procesamiento_historico/__init__.py | `procesamiento/historico/__init__.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/__main__.py | `procesamiento/historico/__main__.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/parser.py | `procesamiento/historico/parser.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/pipeline.py | `procesamiento/historico/pipeline.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/review.py | `procesamiento/historico/review.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/piloto_referencia.json | `procesamiento/historico/piloto_referencia.json` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/schema.sql | `procesamiento/historico/schema.sql` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/dbc.py | `procesamiento/historico/dbc.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/technical.py | `procesamiento/historico/technical.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/linking.py | `procesamiento/historico/linking.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/enrich.py | `procesamiento/historico/enrich.py` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| procesamiento_historico/.gitignore | `procesamiento/historico/.gitignore` | Solo ROOT/origen predeterminado cuando corresponde; reglas y contratos conservados. |
| Nuevo | `procesamiento/__init__.py` |  |
| Correr Sicoes Local.command | `Correr Sicoes Local.command` | Paquete, intérprete y logs nuevos; opciones, caffeinate y códigos conservados. |
| prueba2/tests/test_http_paginas.py | `scraper/historico_local/tests/test_http_paginas.py` | Imports/puerto/lanzador; excluir solo prueba del alias no trasladado. |
| prueba2/tests/test_http_primary.py | `scraper/historico_local/tests/test_http_primary.py` | Imports/puerto/lanzador; excluir solo prueba del alias no trasladado. |
| prueba2/tests/test_http_forms.py | `scraper/historico_local/tests/test_http_forms.py` | Imports/puerto/lanzador; excluir solo prueba del alias no trasladado. |
| prueba2/tests/test_brave_bootstrap.py | `scraper/historico_local/tests/test_brave_bootstrap.py` | Imports/puerto/lanzador; excluir solo prueba del alias no trasladado. |
| prueba2/tests/test_prueba2.py | `scraper/historico_local/tests/test_validation.py` | Conservar casos sintéticos de parsing; no importar engine/browser ni sus tests. |
| procesamiento_historico/tests/test_processing.py | `procesamiento/historico/tests/test_processing.py` | Imports y corpus externo configurable, sin copiar datos. |
| procesamiento_historico/tests/test_enrichment.py | `procesamiento/historico/tests/test_enrichment.py` | Imports y corpus externo configurable, sin copiar datos. |
| docs/CONTINUIDAD_CLAUDE.md | `docs/PLAN_INTELIGENCIA_MERCADO.md` | Extraer plan de seis etapas y publicación progresiva sin doble conteo. |
| docs/CONTINUIDAD_CLAUDE.md | `docs/CONTINUIDAD_CLAUDE.md` | Conservar antecedente; añadir autorización actual y prevalencia de módulos completos. |
| prueba2/HTTP_POR_PAGINA.md + SCRAPER_SICOES_LOCAL.md | `scraper/historico_local/README.md` | Manual consolidado para rutas definitivas. |
| procesamiento_historico/README.md + ENRIQUECIMIENTO.md | `procesamiento/historico/README.md` | Manual consolidado y límites conocidos conservados. |
| Nuevo | `scraper/historico_local/tests/test_integration.py` | Regresiones de rutas, helpers conservados, perfil real y protección del foco con mocks. |
| Nuevo | `docs/INTEGRACION_HISTORICA.md` | Informe final con inventario y evidencia de verificación. |
| Nuevo | `docs/INVENTARIO_INTEGRACION_HISTORICA.json` | Mapa exacto, hashes y procedencia; sin hash de sí mismo para evitar autorreferencia. |

## Pruebas ejecutadas

Ejecutor local con socket.connect, connect_ex y create_connection bloqueados globalmente. Cero intentos de conexión; no se abrió Brave ni se llamaron servicios externos. Se verificaron también --help de los tres CLI, --check y dependencias operativas.

- `procesamiento/historico/tests`: 41 pruebas; fallos 0; errores 0; omitidas 0.
- `scraper/historico_local/tests`: 62 pruebas; fallos 0; errores 0; omitidas 0.

Las regresiones de procesamiento leyeron el corpus de 2024 desde el experimental mediante SICOES_HISTORICO_TEST_SOURCE; validan 19 CUCE, 348 observaciones, el cotejo de piloto, DBC, atributos, asociaciones y SQLite. Sin copiar el corpus ni las SQLite anteriores.

El scraper comprueba recorrido/paginación, captura HTTP, cierres, recuperación, reanudación, validación, perfil/puerto y lanzador. Se ejercitaron descarga HTTP sin ventana, fallback nativo y restauración de hooks con mocks. Las funciones internas de los tres soportes se conservaron.

La primera corrida tuvo un fallo por una expectativa del test que aún apuntaba al módulo antiguo del lanzador. Se actualizó ese test al paquete definitivo, se añadieron dos regresiones del downloader y se repitió únicamente la suite afectada. Los 41 tests de procesamiento ya habían pasado sin cambios.

Logs de esta verificación: /private/tmp/sicoes-tests-integracion-20261109.log y /private/tmp/sicoes-tests-integracion-revision-20261109.log. Resultados estructurados: /private/tmp/sicoes-tests-integracion-20261109.json. No se trasladaron logs históricos.

No se ejecutaron pruebas antiguas que leen Supabase ni navegación real. La ausencia de cambios en componentes anteriores se comprobó por hashes y por las funciones base ejercitadas por el adaptador; no equivale a una validación operativa del portal.

## Dependencias y uso

Intérprete utilizado: `scraper/venv/bin/python`, sin instalaciones ni actualizaciones.

- beautifulsoup4: 4.15.0.
- lxml: 6.1.1.
- playwright: 1.60.0.
- markitdown: 0.0.2.
- pdfminer.six: 20260107.
- mammoth: 1.13.0.
- pypdf: no instalado; opcional para el convertidor auxiliar PDF.

No hay dependencias Python pendientes para --check, el scraper operativo o el procesamiento en este equipo. pypdf solo es pendiente si se invoca explícitamente parsing.convert_document sobre PDF; MarkItDown es el convertidor operativo. Brave, lsof y sesión/captcha requieren validación real autorizada. No se trasladó el perfil antiguo.

```sh
cd ~/Sicoes-Brain
./"Correr Sicoes Local.command" --check
scraper/venv/bin/python -B -m procesamiento.historico --source /ruta/al/corpus --output /ruta/a/salida_nueva --all
scraper/venv/bin/python -B -m procesamiento.historico.enrich --source /ruta/al/corpus --output /ruta/a/enriquecido_nuevo
```

Sin --check, el lanzador inicia extracción real: no fue ejecutada en esta entrega. Las carpetas de datos de main contienen únicamente resultados de pruebas y un perfil vacío de validación, no corridas migradas. Quedaron cinco logs nuevos de los tests del lanzador con intérprete ficticio; no corresponden a descargas ni fueron copiados del experimental. Se conservan sin borrarlos. Los temporales de las pruebas se limpian por sus propios contextos; no se eliminaron archivos preexistentes.

## Estado Git

Rama main, HEAD 60f50de9d6644b40b9be1de53d486e50e7dbd9d9, seis commits por delante de la referencia local origin/main. HEAD experimental 6ed56b9a2fc0aafe2fe345f07b0ecc8a8bc3e3ee, sin cambios de rama ni eliminación del worktree. No hubo fetch para consultar el remoto actual.

Los 12 archivos modificados de Graphify y los no rastreados previos siguen pendientes e intactos. Los nuevos archivos permanecen sin rastrear; no se hizo git add. Los datos de prueba están ignorados. Consultar el inventario JSON para la lista exacta.

## Límites y siguiente fase

Las incompatibilidades de FORM 170 y de documentos sin versión válida permanecen sin corregir. FORM 600 solo inventariado y 100-E excluido. No se cambiaron reglas ni se entrenó con 2022. No se modificaron Supabase, el dashboard o canonicalización.

Pendiente: migrar datos por separado con hashes/rutas y respaldos consistentes; validar Brave en operación autorizada; decidir correcciones documentadas de incompatibilidades; publicar datasets del dashboard en una fase independiente y reversible.
