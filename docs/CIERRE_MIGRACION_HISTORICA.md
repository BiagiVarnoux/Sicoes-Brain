# Cierre de migración histórica — 20261109T152013Z

Trabajo operativo y regresión desde main. No se modificaron algoritmos, Supabase, dashboard, scrapers/comandos previos ni Graphify. Sin descargas, commits, staging o push; no se borraron datos ni el worktree experimental.

## Corpus definitivos verificados

| Gestión | CUCE | Archivos cotejados | Versiones con hash/tamaño verificados | Markdown legibles |
|---|---:|---:|---:|---:|
| 2022 | 24 | 486 | 102 | 91 |
| 2023 | 29 | 570 | 122 | 103 |
| 2024 | 19 | 395 | 84 | 72 |

Ubicación: `scraper/historico_local/data/historico_http_paginas_0660-10_<gestión>/`. Los 1.451 archivos cotejados coinciden con los SHA256 guardados antes del traslado, sin faltantes ni diferencias. Se excluyó .DS_Store por ser metadato de Finder. Los originales ya existentes no se copiaron ni sobrescribieron.

El usuario movió las tres carpetas: ya no están en el experimental. Por eso no se afirma comparación simultánea entre dos copias; se contrastó con `compatibilidad_2022_2023/integridad_antes.json` y con los hashes/tamaños de las versiones de los manifiestos. Todo Markdown referenciado se abrió como UTF-8. Los cuerpos inválidos históricos se conservan; legibilidad e integridad no garantizan que todos los documentos publicados se hayan capturado.

Las otras carpetas de entidades/gestiones quedaron inventariadas en el informe JSON local, fuera de la comparación de regresión 0660-10. No se afirma cobertura ni equivalencia de sus datos.

## Referencias preservadas

Ubicación aislada e ignorada por Git: `procesamiento/historico/data/referencias/experimental_20261109T152013Z`.

Se copiaron únicamente los tres conjuntos derivados siguientes; no se copiaron tests/, logs de ejecución ni metadatos Finder. Todos los archivos se verificaron por SHA256 antes/después; los manifiestos originales se conservaron sin edición. ORIGEN.json registra las ubicaciones y huellas sin reinterpretar sus rutas históricas.

| Conjunto | Archivos | SQLite |
|---|---:|---:|
| piloto_0660-10_2024 | 6 | 1 |
| integral_0660-10_2024 | 21 | 2 |
| compatibilidad_2022_2023 | 22 | 2 |

Total: 49 archivos derivados y cinco SQLite, todas con integrity_check y foreign_key_check correctos. No había copias en main en el inventario previo; no se sobrescribió ninguna. Las referencias conservan los resultados del código experimental, no se presentan como nuevas corridas.

## Regresión local 2024 con DBC

Nueva ejecución: `procesamiento/historico/data/regresiones/20261109T152013Z/integral_0660-10_2024`. Fuente exclusiva: corpus definitivo de main. Se bloquearon globalmente socket.connect, connect_ex y create_connection: cero intentos de conexión.

Resultado: 19 CUCE, 64 formularios procesados y uno excluido, 348 observaciones, 100 requerimientos A/B, siete CUCE con DBC, 54 bloques de especificación, 198 atributos, 51 vínculos CONFIRMADA y tres AMBIGUA; cotejo de 3.523 celdas correcto. El resumen coincide íntegramente con la referencia.

Archivos iguales byte por byte: 15. Incluyen CSV, inventario DBC, atributos, relaciones y A/B. Las tablas de datos de ambas SQLite coinciden fila por fila; su contenido lógico se compara excluyendo solo la tabla metadatos, sin editar las bases.

Diferencias esperadas: ejecución/procedencia/SQLite registran la raíz de main, hashes del código integrado y nuevo run_id. Las bases no tienen por qué coincidir en bytes debido a estos metadatos. huellas_repeticion.json y verificacion_final.json son comprobaciones de la referencia antigua y no salidas del ejecutor actual; se preservan solo en referencias.

Diferencias de procedencia: `[{"file": "observaciones/ejecucion.json", "keys": ["code_sha256", "input_sha256", "run_id", "source_root"], "reason": "Raíz definitiva y hashes del código/identificador de ejecución nuevos; original preservado"}, {"file": "procedencia.json", "keys": ["code_hashes", "inputs"], "reason": "Raíz definitiva y hashes del código/identificador de ejecución nuevos; original preservado"}]`.

Diferencias inesperadas: `[]`.

Detalle reproducible en `comparacion_referencia.json` y `verificacion_corpus.json`, junto al directorio nuevo de regresión. No se alteraron las referencias para obtener igualdad.

## FORM 170 pendientes

Se releen los HTML definitivos con el parser actual y se contrastan las celdas con el registro de compatibilidad: ocho bienes de 2022 y nueve de 2023 siguen sin extraerse por column_count_mismatch en encabezados compuestos. No se cambió ninguna regla.

| Año | CUCE | Bienes pendientes |
|---|---|---:|
| 2022 | 22-0660-10-1199037-2-2 | 4 |
| 2022 | 22-0660-10-1250273-1-1 | 4 |
| 2023 | 23-0660-10-1323309-1-1 | 3 |
| 2023 | 23-0660-10-1337681-1-1 | 1 |
| 2023 | 23-0660-10-1356740-1-1 | 5 |

También siguen pendientes los FORM 170 sin versión válida de 22-0660-10-1199042-1-2 y 23-0660-10-1309108-1-1; el cargador general no los tolera todavía. No se ejecutó una nueva corrida integral de esos años ni se convirtieron faltantes en éxitos.

## Inventario para un futuro commit

Lista exacta: [ARCHIVOS_COMMIT_HISTORICO.txt](ARCHIVOS_COMMIT_HISTORICO.txt), 41 archivos de código, pruebas, esquemas auxiliares, documentación y referencias de prueba de código. Ningún archivo se añadió a staging.

Excluye data/ completos: originales, Markdown descargado, CSV/JSONL de corridas, SQLite, perfiles, logs y referencias migradas. Excluye secretos/.env, skills y Graphify pendientes ajenos a esta entrega. No usar git add . ni git add -A para preparar este commit.

Rama main, HEAD 60f50de9d6644b40b9be1de53d486e50e7dbd9d9; continúa seis commits delante de la referencia local origin/main. Los 12 cambios previos de Graphify y los no rastreados anteriores permanecen intactos. No se consultó el remoto.

## Pendientes

Resolver por separado los 17 bienes omitidos y documentos sin versión válida; validar operación real de Brave/sesión cuando se autorice; publicar progresivamente datos en el dashboard en otra fase. FORM 600 sigue solo inventariado y FORM 100-E excluido; no hay demanda neta ni nuevas equivalencias canónicas. pypdf sigue opcional para el convertidor PDF auxiliar.

Las referencias guardan rutas históricas del experimental: se conservan como evidencia, no son dependencias de ejecución. Los comandos normales y las pruebas de corpus pueden utilizar ya la ubicación definitiva de main; no requieren el worktree experimental.
