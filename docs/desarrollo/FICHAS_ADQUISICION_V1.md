# Fichas de adquisición v1: contrato previo a implementación

Prioridad comercial: FORM 500 (recepción), FORM 200/220 (contratación) y DBC
(requisitos). Observaciones originales inmutables; fichas derivadas. No incluye
candidatos de canonicalización, equivalencias de productos ni agrupación canónica.

Esquema mínimo: ficha_id, versión, entidad, gestión, CUCE, observaciones de origen,
identificadores de ítem, descripción original, campos comerciales con referencias
por celda, fechas y moneda documentadas, relaciones con evidencia, requisitos DBC,
atributos con operadores y fragmentos, faltantes, alertas y contexto no asociado.
Cada dato conserva documento, SHA256, tabla/fila/columna o sección. Valores
numéricos son decimales en texto; desconocido es null. Cantidad reportada solo
se presenta como recibida cuando el estado confirma recepción; importe de FORM
500 permanece como monto ejecutado reportado si ese estado no la confirma.

Reglas iniciales: mismo CUCE; descripción original igual tras normalizar espacios,
acentos y caja; contrato explícito igual; ninguna unidad conocida incompatible;
ningún proveedor explícito incompatible; cantidad solicitada coherente si existe.
El número de ítem nunca basta. Confirmar exige candidato único en ambos sentidos.
Relaciones múltiples se conservan como grafo de candidatos ambiguos, sin consolidar
ni repartir cantidades. Una recepción sin unidad puede vincularse por descripción,
contrato y cantidad solicitada igual, conservando la unidad solo en contratación.
No se suman contratación y recepción. Una ficha consolidada contiene las dos
etapas; fichas sin vínculo siguen separadas y no son demanda aditiva.

DBC: reutilizar segmentador, atributos y comprobaciones de linking.candidate;
no alterar el vínculo histórico sobre requerimientos. Confirmar solo con evidencia
textual fuerte, cantidad/unidad compatibles y unicidad en ambas direcciones.
Descripciones genéricas, varios bloques o conflictos quedan para revisión humana.
Se conserva sección original aunque no haya bloques interpretables. Ningún requisito
DBC se presenta como característica comprobada del bien recibido.

Casos previos: 23-0660-11-1314047-1-1, FORM 200 tabla 11 fila 3 y FORM 500 tabla
5 fila 3: escritorios, contrato 925, 20 piezas contratadas, 20 recibidas, 3090
unitario, 61800 total, proveedor TOLA MAMANI PEDRO. El DBC DOCX tabla 9 fila 2
contiene requisitos de escritorios pero el segmentador existente devuelve cero
bloques: no inventar vínculo ni perder esa sección; revisión humana pendiente.
Regresión 0660-10/2024: 348 observaciones, 54 bloques, 198 atributos, 51 vínculos
DBC confirmados y 3 ambiguos bajo reglas históricas, sin cambiar esos resultados.
Otros casos se seleccionarán del inventario real, incluyendo múltiples ítems,
proveedores, diferencias de unidad y fuentes faltantes. El cotejo de celdas con
lector HTML independiente verifica fidelidad, no precisión comercial independiente.

Salida nueva y exclusiva; rechazo si existe. JSONL completos, SQLite consultable,
inventario por proceso/documento, conciliación de filas y métricas por entidad/año.
Se registran hashes de fuentes y código; dos corridas deben producir registros
idénticos. Un fallo de integridad es fatal; falta local queda explícita.

## Uso y esquema consultable

Desde la raíz, con el entorno local ya instalado:

```bash
scraper/venv/bin/python -m procesamiento.historico.acquisitions --output procesamiento/historico/data/adquisiciones_v1_NUEVO_CORTE
scraper/venv/bin/python -m unittest discover -s procesamiento/historico/tests -v
```

El comando exige que la salida no exista; no sobrescribe referencias ni corridas.
`fichas.jsonl` contiene cada ficha completa y `fichas.sqlite` ofrece tablas
`fichas`, `observaciones` y `ficha_observacion` con integridad referencial.
Los IDs de observación se calculan con el mismo origen relativo al corpus que
el pipeline anterior; `source_root` permite resolver la ruta desde el repositorio.

| Bloque | Contenido y significado |
|---|---|
| Identificación | `ficha_id`, `schema_version`, `entity`, `entity_name`, `year`, `cuce`, `process_metadata`, `manifest_path`, `observation_ids` |
| Observaciones | Descripción original, FORM, etapa, referencia documento/hash/tabla/fila/sección, contexto documental y contractual |
| Comercial por observación | Proveedor, cantidades, unidad, importes, precios y fechas como objetos con literal, normalizado, columna y referencia; sin mezclar fases |
| Recepción | `cantidad_recibida` e `importe_recibido` solo con estado confirmatorio; monto ejecutado y cantidad reportada originales siempre separados; precio derivado con fórmula, operandos y fracción exacta |
| Técnica | Menciones de la descripción por separado; `technical_requirements` solo para relaciones DBC confirmadas, texto de requisitos y atributos con operador, evidencia, contexto, span y celda DOCX |
| Relaciones | Aristas de contratación/recepción y observación/DBC con IDs, evidencia, respaldo y estado; no se elige un ganador entre candidatos múltiples |
| Calidad | Estado de vinculación, campos/fuentes faltantes, advertencias originales, contexto sin asignar y secciones DBC disponibles aunque no sean segmentables |

En FORM 200/220, el campo literal `cantidad` dentro de una observación de etapa
`contratacion` corresponde a la cantidad contratada; se conserva ese nombre del
parser cuando el encabezado no dice “cantidad contratada”. No se interpreta así
en una sección de bienes no contratados.

No hay proveedor contratado inferido a partir de una lista general de proveedores.
El dato explícito del FORM 500 permanece en recepción; una relación documental
permite consultar la evidencia conjunta, sin copiarlo como dato literal de FORM 200.
`NO_CONTRATADO` se conserva para auditoría y debe excluirse de compras realizadas.
La gestión se obtiene del corpus, no sustituye las fechas documentadas. La moneda
queda en contexto cuando el formulario la declara; no se inventa moneda para una
recepción que no la indica ni se combinan monedas sin comprobar equivalencia.

## Límites deliberados de v1

- El contrato compartido entre muchos ítems produce muchos candidatos; esta versión
  se abstiene aunque exista una correspondencia textual aparentemente fuerte.
  No prueba que los bienes sean diferentes: exige revisión antes de consolidar.
- Relaciones uno a varios se representan como múltiples aristas ambiguas. No se
  consolidan automáticamente recepciones parciales ni se prorratean importes.
- La unidad ausente en FORM 500 no se rellena como si estuviera documentada allí.
  Una unidad DBC no reconocida debe coincidir literalmente con la de la observación
  para permitir confirmación; no se deducen conversiones caja/pieza.
- El segmentador DBC existente cubre diseños concretos de tablas DOCX. La sección
  completa se guarda aunque no encuentre bloques; PDFs y otros formatos permanecen
  explícitamente fuera del segmentador y no se someten a OCR en esta entrega.
- No se extraen todas las marcas, modelos, maderas, dimensiones en metros ni atributos
  de todas las familias. La evidencia textual queda disponible para ampliar reglas
  posteriormente; desconocido no significa ausencia del atributo en el documento.
- Los atributos de la descripción son menciones documentadas, no características
  comprobadas. Los DBC asociados siguen siendo requisitos. No se construye una
  descripción sintética que borre esa diferencia.
- Cero filas omitidas detectadas se refiere a tablas reconocidas por el parser.
  No demuestra recall exhaustivo de tablas desconocidas ni completitud anual.
- Confirmación automática bajo reglas no equivale a precisión comercial medida.
  Hace falta referencia humana independiente, en particular para todos los casos
  complejos y para cualquier futura agregación/publicación de demanda.

## Uso posterior en dashboard

Explorador: ficha, fases y originales enlazados. Precios: separar contratado,
recibido y derivado; controlar moneda/unidad y estado. Cantidades por entidad:
elegir explícitamente recepción o contratación; fichas ambiguas no son aditivas.
Búsqueda: descripciones y menciones técnicas sin afirmar identidad. Comparación:
requisitos DBC frente a menciones del formulario, con operadores y desconocidos.
Proveedores: dato explícito por fila o contexto sin asignar, sin repartir montos.
Canonicalización y recurrencia: consumir después un subconjunto validado, preservando
IDs y evitando contar contrato y recepción como compras independientes. Ninguna
vista del dashboard ni Supabase se modifica en esta entrega.

## Continuación: reglas de asociación v2

La [revisión v2](ASOCIACION_ADQUISICIONES_V2.md) actualiza únicamente la resolución
contratación/recepción. El contrato y esquema v1 se conservan como antecedente;
la política vigente distingue aristas descartadas y elegibles antes de exigir
unicidad. Las evidencias originales y los requisitos DBC no cambian. El comando
adquiere `--association-rules v1|v2`, con v2 por defecto. El informe v1 describe
exclusivamente su corte histórico; sus métricas no se reemplazan por las nuevas.
