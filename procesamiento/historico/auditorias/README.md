# Auditoría de asociaciones documentales v2

Esta carpeta contiene un generador de muestras de revisión; no modifica ni
invoca las reglas de vinculación. Lee las salidas congeladas v1/v2, selecciona
parejas y coteja sus referencias con los HTML originales.

La entrega de 100 casos está en:

- [CSV para revisión](../data/auditoria_v2_100_20261109_01/muestra_auditoria_100.csv).
- [Método, distribución y poblaciones](../data/auditoria_v2_100_20261109_01/RESUMEN.md).
- [Todas las celdas de estratificación](../data/auditoria_v2_100_20261109_01/estratos_poblacion_muestra.csv).
- [Semilla, selección, hashes y controles](../data/auditoria_v2_100_20261109_01/seleccion_y_procedencia.json).
- [Validación final y repetibilidad](../data/auditoria_v2_100_20261109_01/validacion_final.json).

Son 50 asociaciones nuevas confirmadas, 20 ambiguas, 20 hipótesis descartadas y
10 recepciones sin vínculo con una contratación comparable. Abarcan 48 CUCE y
las siete combinaciones de entidad/gestión. Se excluye por completo el CUCE
`25-0660-11-1517374-1-1`, empleado en desarrollo.

La población de nuevas confirmadas auditables es 480: las 497 nuevas incluyen
17 del CUCE excluido. Las otras poblaciones son 55 aristas ambiguas y 8.366
aristas descartadas. Para los casos sin vínculo se identificaron 401 recepciones
con comparable; el marco queda en 393 tras excluir ocho parejas ya seleccionadas
en el grupo de descartadas. Se seleccionan diez de ese marco.

La asignación se equilibra primero por entidad/gestión, después por causa y por
etiqueta exploratoria de producto, con selección pseudoaleatoria de semilla fija
dentro de cada celda. Las ambiguas existentes solo pertenecen a 0660-10; todas
tienen contexto contractual no único. Se incluyen las cuatro combinaciones de
causas de descarte existentes. Las etiquetas de producto no son canonicalización.

La unidad de los tres primeros grupos es la arista entre formularios. En el
último es la recepción sin vínculo y su comparable fijo, solo para auditoría.
Los diez comparables seleccionados tienen una arista descartada: el CSV distingue
`ESTADO_ANCLA=SIN_VINCULAR` de `ESTADO_ALGORITMO_PAREJA=DESCARTADA`. Ningún estado
se ha cambiado ni se ha confirmado esa pareja. No hay parejas duplicadas entre
los grupos, aunque pueden compartir CUCE o una observación.

El CSV conserva descripciones originales y visibles, literales/normalizados,
cantidades, unidades y proveedores explícitos por fila, precios explícitos y
derivados separados, contrato, estado algorítmico, documento/hash/tabla/fila y
campos/contextos originales con columnas. Si un proveedor o unidad no consta en
la fila, queda vacío; el contexto contractual se muestra aparte, sin inferirlo.
Las columnas `REVISION_HUMANA`, `ESTADO_CORRECTO` y `OBSERVACIONES_REVISION` están
vacías. Esta entrega no contiene respuestas humanas ni estimaciones de precisión.

Se verificaron 96 originales y 191 filas distintas de bienes, con sus contextos;
las 200 descripciones del CSV coinciden con las celdas originales extraídas.
Se comprobó que los hashes de los módulos/reglas v2 coinciden con la procedencia
de su corrida congelada. Una segunda ejecución produjo los cuatro archivos
principales idénticos byte por byte. Las corridas y referencias previas se conservan.

La muestra es diagnóstica y desproporcionada. No debe usarse el porcentaje bruto
de aciertos de los 100 casos como precisión global: la precisión de nuevas
confirmadas se estudia sobre sus 50 casos, con ponderación/estratos y dependencia
por CUCE al extrapolar. Los casos de desarrollo excluidos, estratos no muestreados
y observaciones sin comparable quedan fuera de esa inferencia. La muestra de
sin vínculo no permite estimar por sí sola recall global.

Para reproducir, desde la raíz y con una salida nueva:

```bash
scraper/venv/bin/python -m procesamiento.historico.auditorias.generar_muestra_v2_100 --output procesamiento/historico/data/auditoria_v2_100_NUEVA
```

Los archivos de datos locales pueden estar ignorados por Git. Esta entrega no
los publica ni modifica producción, reglas, originales o manifiestos; no ejecuta
APIs, LLM ni nuevas extracciones. No se hicieron commits ni push.

## Diagnóstico posterior sobre originales

La revisión asistida recibida dio 50 respaldadas, 12 no respaldadas y 38
indeterminadas. El [diagnóstico de causas raíz](../../../docs/desarrollo/DIAGNOSTICO_CAUSAS_AUDITORIA_V2.md)
coteja los 38 indeterminados y los 12 controles negativos con originales.

Sus anexos están en `../data/diagnostico_auditoria_v2_20261109_01/`. El diagnóstico
identifica 16 correspondencias por contexto FORM 220, 20 con proveedor corroborado
por FORM 170 y dos mediante modificatorio de plazo FORM 250; mantiene los 12
pares incompatibles descartados. Estas son conclusiones documentales separadas:
no se modifican etiquetas, reglas ni estados v1/v2 y no son precisión certificada.

`diagnostico_originales_v2.py` reproduce el cotejo y sus controles con una salida
nueva. No implementa las mejoras propuestas. Conserva copias exactas de la revisión
recibida y prueba por hashes que fuentes, reglas y salidas congeladas no cambian.
