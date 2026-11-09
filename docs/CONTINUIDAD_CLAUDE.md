# Continuidad para Claude — SICOES-BRAIN

## Estado actual

La integración selectiva autorizada quedó incorporada en ~/Sicoes-Brain, rama
main, sin commits, merge general ni push. El experimental continúa intacto.
Consultar INTEGRACION_HISTORICA.md para inventario exacto, pruebas y restricciones;
INVENTARIO_INTEGRACION_HISTORICA.json conserva el mapa y hashes de los archivos.

Se incorporaron scraper/historico_local/, procesamiento/historico/ y únicamente
el lanzador Correr Sicoes Local.command. PLAN_INTELIGENCIA_MERCADO.md define las
seis etapas y la publicación progresiva en el dashboard sin duplicar demanda.

Por instrucción del usuario se conservaron todas las funciones internas de
storage.py, parsing.py y brave_bootstrap.py. Se añadió el schema.sql auxiliar
para preservar Store sin trasladar engine, browser, session ni su CLI piloto.
La limpieza interna queda para otra tarea. El perfil nuevo usa exclusivamente
9226; no ejecutar en paralelo el experimental sobre ese puerto.

Todos los archivos rastreados y no rastreados respaldados de ambos worktrees
mantienen sus hashes y permisos. Los cambios previos de Graphify y skills de
main siguen pendientes y no fueron alterados. No ejecutar hooks o regenerar
Graphify como parte de esta entrega. No se modificaron dashboard, Supabase,
scrapers/comandos anteriores ni algoritmos de canonicalización.

## Trabajo previo y evidencia

El corpus local de 0660-10 conserva 24 CUCE de 2022, 29 de 2023 y 19 de 2024.
La extracción estructurada de 2024 produjo 348 observaciones y enriquecimiento
de siete CUCE con DBC, 51 vínculos documentales CONFIRMADA y tres AMBIGUA.
CONFIRMADA no significa identidad comercial ni precisión validada.

La prueba separada 2022–2023 produjo 487 y 517 observaciones; sus 10.089 celdas
extraídas coinciden con un segundo lector. La cobertura es parcial: FORM 170
con encabezados compuestos dejó ocho bienes sin extraer en 2022 y nueve en 2023.
Hay un FORM 170 sin versión válida por año. El cargador general todavía aborta
en ese caso; la tolerancia existía en un adaptador específico no incorporado.
No cambiar reglas para esconder estas incompatibilidades. FORM 600 solo se
inventaría y FORM 100-E sigue excluido; no hay reconstrucción de demanda neta.
No utilizar 2022 para ajustar canonicalización.

El usuario trasladó los corpus originales 2022–2024 de 0660-10 a main. Se
verificaron sus 1.451 archivos contra hashes anteriores al traslado y manifiestos.
Ya no existen esas tres carpetas originales en el experimental. Los resultados
derivados históricos necesarios se copiaron por separado a data/referencias/
dentro de procesamiento/historico, con SHA256 e inventario ORIGEN.json. La nueva
regresión 2024 con DBC se ejecutó solo con fuentes de main en data/regresiones/:
resumen, CSV, JSONL y tablas de datos SQLite coinciden con la referencia; cambian
solo procedencia, rutas y hashes del código/ejecución. Ver CIERRE_MIGRACION_HISTORICA.md.
Los scripts anuales específicos y el resto del experimental se conservan sin borrar.

## Cómo trabajar desde main

Usar la raíz ~/Sicoes-Brain. El lanzador --check comprueba dependencias sin
conexiones; sin --check inicia captura real y requiere decisión del operador.
Usa SICOES_LOCAL_PYTHON o scraper/venv/bin/python. El procesamiento recibe
--source y --output explícitos para seleccionar corpus y preservar ejecuciones.
Ver los README de ambos paquetes. Los CLI conservan los defaults adaptados a main. El corpus 0660-10 de 2024
ya existe en el origen predeterminado; usar siempre --output nuevo para no
reemplazar derivados previos. Las pruebas de corpus ya no necesitan apuntar al
experimental.

El scraper operativo reutiliza por AST la navegación y descarga de los scrapers
base. Se conserva la descarga por context.request con hook temporal de submit
que evita la ventana _blank. El fallback nativo puede robar foco: no prometer
que ese caso fue eliminado. Se probó con mocks, sin abrir Brave real.

## Restricciones y siguiente fase

No migrar ni borrar originales, corridas, bases, perfiles o logs sin una tarea
separada. No eliminar el worktree experimental. No publicar a Supabase ni tocar
el dashboard o canonicalización como continuación automática. No hacer push.
No reemplazar archivos existentes ni modificar Graphify ante conflictos.

Próximos pasos sujetos a instrucciones: validación operativa autorizada de
Brave/sesión; tratamiento explícito de
incompatibilidades; publicación reversible de datasets en el dashboard. El
colapso actual por CUCE/ítem/lote no demuestra identidad entre etapas nuevas.
Conservar observaciones originales separadas de atributos, vínculos y grupos.

El documento original de auditoría permanece en el experimental, sin eliminarlo.
Respaldo: /private/tmp/sicoes-integracion-20261109T145337Z/manifest.json.


## Cierre de migración de datos

Los 72 CUCE de 2022–2024 están disponibles y legibles desde main. Se preservaron
49 archivos derivados de referencia, incluidas cinco SQLite íntegras. La regresión
2024 confirmó 348 observaciones, siete CUCE con DBC, 198 atributos y vínculos 51/3.
Los 17 bienes omitidos siguen pendientes en las mismas posiciones y con las
mismas celdas. Sin cambios de algoritmos, Supabase o dashboard, sin descargas,
borrados, commits ni push. Las huellas y rutas antiguas en las referencias son
históricas, no deben editarse para aparentar otra procedencia.

ARCHIVOS_COMMIT_HISTORICO.txt enumera exactamente los archivos de código/pruebas/
documentación propuestos para un futuro commit; data/, perfiles, logs, SQLite y
secretos quedan excluidos. No se hizo git add. El reporte de cierre y los JSON de
comparación documentan verificaciones y diferencias esperadas.
