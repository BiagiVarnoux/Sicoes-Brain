# Procesamiento histórico local

Lee exclusivamente originales y manifiestos existentes. No conecta a SICOES,
Supabase ni proveedores LLM. No hace OCR. No modifica canonicalización.

Desde la raíz del repositorio, indicar el corpus real y una salida independiente:

```sh
scraper/venv/bin/python -B -m procesamiento.historico --source /ruta/al/corpus --output /ruta/a/salida_nueva --all
scraper/venv/bin/python -B -m procesamiento.historico.enrich --source /ruta/al/corpus --output /ruta/a/enriquecido_nuevo
```

El primer comando extrae observaciones por formulario y etapa con CSV, SQLite y
auditoría. El segundo añade inventario DBC, segmentación DOCX/Markdown, atributos
con evidencia, relaciones documentales y representaciones A/B. No crea grupos
canónicos ni publica resultados en el dashboard. Sin --all/--cuce el primer CLI
conserva la selección original del piloto de tres CUCE: usar --all conscientemente.

Las salidas predeterminadas permanecen en data/ de este paquete; el origen
predeterminado apunta al futuro corpus local de 2024 bajo scraper/historico_local/data/.
Los corpus 0660-10 de 2022–2024 ya están verificados en la ubicación definitiva;
2024 está disponible en el origen predeterminado. Usar --source explícito para
otras gestiones y --output nuevo para conservar las ejecuciones. La inexistencia
de otro corpus no debe confundirse con ejecución vacía exitosa. Una salida ya existente
puede reemplazar sus derivados; seleccionar una nueva para preservar ejecuciones.

El DBC debe contar con original DOCX y Markdown preservado en el manifiesto.
La asociación CONFIRMADA acredita una relación documental bajo reglas, no una
equivalencia comercial ni prestaciones verificadas del producto entregado.
No se inyectan atributos de relaciones ambiguas. Unidades, cantidades, precios,
operadores y valores originales/derivados permanecen separados.

FORM 600 solo inventariado y FORM 100-E excluido. No sumar cantidades entre
requerimiento, adjudicación, contratación y recepción ni afirmar demanda neta.
Las columnas y filas desconocidas conservan evidencia para revisión.

Límites preservados: FORM 170 con encabezados compuestos puede dejar bienes sin
extraer; el cargador general aborta ante documentos sin versión válida. La
migración no corrige ni oculta esos problemas. Los scripts específicos de la
prueba 2022–2023 permanecen en el experimental. Sus resultados y los de 2024
se conservaron también como referencias locales inmutables bajo data/referencias/.
La nueva regresión con DBC está bajo data/regresiones/. Ver
docs/CIERRE_MIGRACION_HISTORICA.md para ubicaciones y comparación.

Pruebas: `python -B -m unittest discover -s procesamiento/historico/tests -v`.
Para las regresiones de corpus, configurar SICOES_HISTORICO_TEST_SOURCE con una
ruta local existente. Sin corpus se omiten explícitamente; los tests sintéticos
siguen ejecutándose. Los tests escriben solo derivados temporales en data/tests/.
El entorno del scraper operativo aporta bs4/lxml; el resto usa biblioteca estándar.
technical.py lee por AST patrones literales del extractor de impresión existente,
sin ejecutar su configuración ni modificar sus algoritmos.

Ver docs/PLAN_INTELIGENCIA_MERCADO.md y docs/INTEGRACION_HISTORICA.md.

## Fichas de adquisición locales — v1

La prioridad actual es FORM 500 + FORM 200/220 + DBC. El comando independiente
no modifica los comandos anteriores ni los datos originales:

```bash
scraper/venv/bin/python -m procesamiento.historico.acquisitions --output procesamiento/historico/data/adquisiciones_v1_NUEVO_CORTE
```

La salida debe ser nueva. Produce observaciones separadas, fichas derivadas
SQLite/JSONL, inventario, relaciones con evidencia y procedencia. No suma fases,
no ejecuta LLM y no realiza canonicalización. Véanse el
[esquema y las reglas](../../docs/desarrollo/FICHAS_ADQUISICION_V1.md) y el
[informe de la primera entrega](../../docs/desarrollo/ENTREGA_FICHAS_ADQUISICION_V1.md).

Las reglas de asociación vigentes son `v2`: resuelven unicidad entre aristas
elegibles y conservan las descartadas con motivos y contexto contractual.
Para comparación se puede añadir `--association-rules v1`. El esquema de ficha
no cambia; ambas opciones exigen una salida nueva. Referencia y límites en
[asociación documental v2](../../docs/desarrollo/ASOCIACION_ADQUISICIONES_V2.md).
