# Corrección puntual — llantas: `huella` y `pliegues` como discriminantes solo-contradicción

Autorizada tras la auditoría final. Línea base previa congelada en
`congelado/verificador_niveles_baseline_prellanta.py`. Aislada con bandera `fix4` (antes/después).
NO toca RAM, almacenamiento, papel membretado ni ninguna otra categoría. NO avanza a agrupación.

## Regla implementada (condiciones de ChatGPT respetadas)
`huella`/`pliegues` NO entran al IDENT duro (su ausencia NO degrada). Actúan solo por contradicción:
1. **Diferencia técnica CONFIRMADA → NO.** Para huella, solo cuando una es de grupo *barro*
   (pantanera / semi pantanera) y la otra de *carretera* (autopista; H/T se normaliza a autopista en el
   extractor). Para pliegues, dos enteros explícitos distintos → NO (lona/carga distinta, número inequívoco).
2. **Denominación AMBIGUA → INSUF, no NO.** Diferencias que involucran todo terreno (A/T), normal, lisa, o
   pantanera↔semipantanera NO se declaran contradicción: si estaba en SI baja a INSUF; nunca a NO.
3. **Ausencia → se ignora** (no confirma ni contradice).
4. No se presume que H/T, A/T, (semi)pantanera sean incompatibles entre sí salvo el par barro/carretera.

Fuente de normalización: `huella_llanta()` del extractor congelado (ya mapea H/T→autopista, A/T→todo terreno).
No se modificó el extractor.

## Impacto sobre los 9.828 pares (fix4 OFF → ON, resto de correcciones fijas)
| estado ESP | OFF (antes) | ON (después) |
|---|---|---|
| SI | 595 | **595** (sin cambios) |
| INSUF | 2699 | 2697 |
| NO | 6534 | **6536** |

**Transiciones (todas): únicamente `INSUF → NO`, 2 pares, ambos en llanta.** 0 en cualquier otra categoría,
0 pérdidas de SI, 0 transiciones hacia INSUF. El cambio es quirúrgico.

### Las 2 transiciones NO→INSUF de la auditoría quedaron revertidas a NO
Ambas son la llanta 205/70 R15: A = "SEMI PANTANERA" (grupo barro) vs B = Firestone "TRILLA H/T"
(→ autopista, grupo carretera). `huella` incompatible barro/carretera → **ESP=NO** recuperado.
Razón emitida: `huella: semi pantanera ≠ autopista (incompatible barro/carretera → distinto)`.

## Regresión (pruebas, no validación de esta versión)
- **Muestra v2 (22, papel): 22/22/22** — sin cambios (fix4 no aplica a papel).
- **Muestra 53 (papel): FAM 53 / SUB 49 / ESP 51** — idéntica a antes (la tensión conocida de gramaje).
- **Extractor: 11/11.**
- Por construcción fix4 está acotado a `cat=="llanta"`; las muestras de papel no pueden verse afectadas, y
  se confirmó numéricamente.

## Qué NO hace (matices aceptados de la revisión)
- No autoriza fusión: ESP=SI sigue siendo veredicto de equivalencia, separado de la autorización a fusionar.
- No amplía la incompatibilidad a denominaciones ambiguas (A/T, normal, lisa) — esas quedan INSUF.
- No toca RAM/almacenamiento/membretado.

## Pendiente para decidir el cierre de Etapa 3
1. Los 595 ESP=SI son equivalencia dentro de los atributos modelados; **membretado no prueba identidad
   absoluta del impreso** (diseño/impresión/gramaje pueden variar) → tratar como candidatos a equivalencia
   comercial, no fusión automática.
2. RAM/almacenamiento 0 confirmados: estricto por diseño; la subauditoría de extracción (ver
   `auditoria_extraccion.md`) confirma 0 fallos de extracción de atributos primarios.
3. Validación independiente de ESTA versión aún pendiente (los 22/22/22 son regresión).
