# Diseño técnico — Etapa 4: agrupación de productos (DISEÑO, NO IMPLEMENTACIÓN)

**Estado:** propuesta para revisión y aprobación. **No se implementa nada.** No se toca extractor ni
verificador, no se escribe `producto_canonico_id`, no se agregan cantidades ni montos, no se ejecuta la
agrupación. Este documento define el algoritmo, el esquema, la simulación read-only y las métricas, para
que el usuario los apruebe antes de cualquier código.

Insumo: los veredictos del verificador congelado (Etapa 3) por par candidato — FAMILIA_AMPLIA / SUBFAMILIA /
PRODUCTO_ESPECIFICO ∈ {SI, NO, INSUF}. La agrupación consume esos veredictos; no los recalcula.

---

## 1. Algoritmo para formar grupos sin fusiones indebidas por transitividad

**Problema.** Tratar ESP=SI como aristas y tomar **componentes conexos** (union-find ingenuo) fusiona por
transitividad: A≡B y B≡C ⇒ A,B,C juntos aunque A≡C nunca se haya verificado (o sea INSUF/NO/no evaluado).
**Rechazado.**

**ESP=SI es evidencia de COMPATIBILIDAD confirmada, no una obligación de fusionar.** Puede entrar en
conflicto con otras relaciones y entonces NO se realiza. Caso canónico: A-B=SI, A-C=SI, **B-C=NO**. No se
pueden satisfacer las dos fusiones y la incompatibilidad a la vez → el algoritmo **no debe** fusionar
{A,B,C}; debe reconocer que hay **soluciones alternativas incompatibles** (p. ej. {A,B}+{C} o {A,C}+{B}) y
no elegir una en silencio (ver §2). Modelo correcto:
- **ESP=SI** = arista de **compatibilidad confirmada** (candidata a fusión; **no** must-link obligatorio).
- **ESP=NO** = **incompatibilidad** (cannot-link, restricción dura).
- **ESP=INSUF** = evaluado, inconcluso → **no autoriza fusión**.
- **NO_EVALUADO** = el par nunca se comparó (fuera del blocker) → **no autoriza fusión** (ver §3).

La agrupación es por tanto un problema de **partición restringida**: encontrar grupos donde **todo par
interno sea ESP=SI explícito** y **ningún par interno sea ESP=NO**, respetando que los SI son permisos, no
imperativos. Un grupo válido = **clique completo de aristas ESP=SI sin ningún NO interno**.

Procedimiento (determinista, por categoría y dentro de cada bloque del blocker):
1. Construir, por bloque, el grafo de relaciones con las cuatro etiquetas (SI / NO / INSUF / NO_EVALUADO).
2. Enumerar los **cliques maximales** usando **solo** aristas ESP=SI, descartando cualquier conjunto que
   contenga un par NO, INSUF o NO_EVALUADO interno (un clique exige SI explícito en **todos** sus pares).
3. **Comprobar unicidad de la partición** (§2). Si la cobertura por cliques es **única**, esos cliques son
   los clústeres confirmados. Si **no** es única (un nodo cabe en >1 clique maximal, o hay cliques que se
   solapan y no pueden coexistir), el conjunto afectado va a **revisión** con sus alternativas; **no** se
   auto-asigna.
4. Lo que no forma clique confirmado (INSUF, NO_EVALUADO, nodos en conflicto) queda como **candidato /
   singleton / en revisión**, nunca fusionado automáticamente.

**Variante relajada (opcional, solo si el usuario la aprueba):** permitir "casi-clique" con densidad de SI
≥ τ, **0 pares NO** y **0 pares NO_EVALUADO**, marcando el clúster como *asistido* (requiere revisión) en vez
de *confirmado*. Por defecto τ = 1.0 (clique completo con todos los pares SI) para auto-confirmación.

**Exemplar** = la descripción más completa del clúster (más atributos de identidad presentes); etiqueta
canónica y ancla para altas futuras (una nueva descripción debe ser ESP=SI con **todos** los miembros —no
solo con el exemplar— para preservar el clique; si con alguno es INSUF/NO_EVALUADO, no se auto-une).

## 2. Tratamiento de pares SI / NO / INSUF / NO_EVALUADO y no-unicidad

### 2a. Las cuatro etiquetas de relación
| etiqueta | significado | rol en la agrupación |
|---|---|---|
| **ESP=SI** | compatibilidad confirmada | arista candidata; habilita fusión **solo dentro de un clique completo** sin NO. No obliga. |
| **ESP=NO** | incompatibilidad confirmada | cannot-link; **prohíbe** co-clúster. Restricción dura. |
| **ESP=INSUF** | evaluado, inconcluso (falta evidencia) | **no fusiona.** Candidato a revisión / enriquecimiento DBC. |
| **NO_EVALUADO** | el par **nunca se comparó** (fuera del blocker) | **no fusiona.** Causa distinta de INSUF: no hay juicio, no es que falte evidencia del producto. |

INSUF y NO_EVALUADO **ambos impiden la fusión directa, pero son distintos**: INSUF es un veredicto del
verificador (se comparó y no alcanzó); NO_EVALUADO es ausencia de comparación (el blocker no generó el par).
Para confirmar un clique, **cada par interno debe tener un ESP=SI explícito**; un par NO_EVALUADO interno
**no** se completa por transitividad — o se evalúa explícitamente, o el clique no se auto-confirma.

SUBFAMILIA y FAMILIA_AMPLIA no fusionan producto; definen el **nivel** del nodo (jerarquía): un clúster de
ESP=SI es un nodo "producto específico"; agrupaciones más amplias (misma subfamilia) se representan como
nodos padre en el árbol (`parent_id`), **sin** fusionar los productos específicos entre sí.

### 2b. Dependencia del orden y no-unicidad de la partición
Ordenar de forma estable hace el resultado **reproducible**, pero **no demuestra que la partición sea única
ni óptima**. Un grafo de compatibilidad con incompatibilidades puede admitir **varias coberturas por cliques
igualmente válidas** (ej. A-B=SI, A-C=SI, B-C=NO ⇒ {A,B}+{C} o {A,C}+{B}). El diseño debe **detectar** esos
casos y **no** elegir uno en silencio:
- **Detección de ambigüedad:** para cada componente, comprobar si la partición en cliques (bajo SI, sin NO
  interno) es **única**. Señal de no-unicidad: un nodo pertenece a **más de un** clique maximal, o existen
  cliques maximales solapados que no pueden coexistir en la misma partición.
- **Acción:** el componente ambiguo se marca `ambiguo` y se envía a **revisión**, **enumerando todas las
  particiones máximas alternativas** en el reporte. Nunca se auto-asigna una de ellas.
- **Caso no ambiguo:** si la partición es única (p. ej. el componente ya es un único clique completo sin NO),
  se confirma directamente.
- **Trazabilidad:** la simulación reporta, por componente, nº de alternativas detectadas y cuáles nodos son
  el punto de ambigüedad, para que la revisión humana decida — no el algoritmo.
- **Optimalidad:** no se afirma optimalidad global; el objetivo es **seguridad** (no fusionar de más), no
  maximizar el tamaño de los clústeres. Ante duda, fragmentar/revisar, no unir.

## 3. Evitar que una descripción termine en grupos incompatibles
- **Enforcement de cannot-link:** un clúster es válido solo si **ningún par interno es ESP=NO**. Antes de
  unir `d`, se comprueba contra todos los miembros; un solo NO bloquea la unión.
- **Detección de conflicto:** si `d` es ESP=SI con miembros de dos clústeres que entre sí tienen algún par
  NO (o que no pueden unirse en un clique), `d` **no se asigna**: se marca `conflicto` y va a una **cola de
  revisión humana**. Nunca se resuelve el empate automáticamente.
- **Transitividad negativa:** si A≡B (SI) y A≠C (NO), entonces B y C quedan en clústeres distintos por
  construcción (C no puede entrar al clique de A porque A-C es NO; y si B intentara unirse a C, se revisa
  B-C directamente). No se propaga el NO como regla transitiva, pero sí se respeta localmente como cannot-link.
- **Invariante final:** todo clúster **confirmado** cumple (i) **todos** sus pares internos son ESP=SI
  explícito, (ii) **0** pares ESP=NO internos, (iii) **0** pares INSUF o NO_EVALUADO internos, y (iv) su
  partición es **única** (no ambigua, §2b). Cualquier violación o ambigüedad ⇒ revisión, no asignación.

## 4. Manejo de descripciones incompletas (INSUF)
- **No se auto-fusionan.** Por defecto cada descripción INSUF-only es **singleton candidato**.
- **Adjunto blando (opcional, en reporte, no en `producto_canonico_id`):** registrar a qué clúster se parece
  más (ESP=INSUF con el exemplar) como *sugerencia de revisión*, con el atributo que falta. Esto vive en el
  reporte/cola de revisión, **nunca** como asignación canónica.
- **Enriquecimiento por DBC:** las descripciones incompletas son candidatas a re-verificación cuando exista
  texto de DBC (los `DBC_*.md` ya en disco, ver memoria del proyecto). Un INSUF puede pasar a SI/NO tras
  enriquecer; ese flujo es posterior y opcional, no parte del primer corte.
- **Cobertura reportada aparte:** se informa cuántas descripciones quedan sin clúster confirmado por INSUF,
  distinguiendo ausencia real vs no-modelado (ver `auditoria_extraccion.md`).

## 5. Reversibilidad, trazabilidad y versionado
**Migración de esquema propuesta (NO ejecutar todavía).** Sobre `hist_productos_canonicos`:
- `nivel text` — familia_amplia / subfamilia / producto (nodo del árbol).
- `parent_id bigint references hist_productos_canonicos(id)` — jerarquía sin fusionar hijos.
- `atributos jsonb` — atributos canónicos del nodo (los del exemplar).
- `exemplar_item_id bigint` — ítem/descr. representante.
- `metodo text` — clique_auto / asistido / manual.
- `confianza text` — confirmado / asistido / candidato.
- `corrida_version text` — id de la corrida que creó el nodo.

**Log de EVENTOS append-only de verdad (nueva tabla `hist_canonico_eventos`).** Para ser genuinamente
append-only, **no** se actualiza ningún registro previo (nada de `UPDATE ... SET vigente=false`). Se insertan
**eventos inmutables** y el estado vigente se **reconstruye** plegando los eventos:
`id, item_id, tipo_evento ∈ {ASIGNACION, REVOCACION, SUSTITUCION}, producto_canonico_id (destino; NULL en
REVOCACION), producto_canonico_anterior (en SUSTITUCION/REVOCACION, para auditoría), veredicto_origen, razon,
corrida_version, decidido_por (auto|humano), creado_en`.
- **ASIGNACION**: liga `item_id` a un `producto_canonico_id`. **REVOCACION**: anula la asignación vigente de
  `item_id` (lo deja sin canónico). **SUSTITUCION**: cambia `item_id` de un canónico a otro (equivale a
  revocar+asignar, registrado como un solo evento con origen y destino).
- **Estado vigente** = para cada `item_id`, el **último evento por `creado_en`** (o nº de secuencia). Una
  vista materializada `hist_canonico_vigente` lo expone; `hist_items.producto_canonico_id` puede mantenerse
  como caché derivado de esa vista (actualizado por la aplicación de un corte, nunca editado a mano).
- **Reversibilidad:** deshacer = **añadir** un evento REVOCACION/SUSTITUCION, no editar el pasado. Volver a
  un estado anterior = reconstruir plegando eventos hasta una `corrida_version` dada.
- **Versionado:** cada ejecución = una `corrida_version` (timestamp + hash de reglas/umbral). Re-ejecutar
  **no sobrescribe en silencio**: emite eventos nuevos y un **diff** contra el estado vigente anterior
  (altas, revocaciones, sustituciones, cambios de clúster). Coherente con "fusión persistente pero reversible,
  con versionado y registro de auditoría reconstruible".

## 6. Simulación read-only (evaluar clústeres SIN escribir)
Script propuesto `simulacion_agrupacion.py` (cuando se apruebe): 
- Lee los veredictos del verificador congelado, corre el algoritmo de la sección 1 **en memoria**.
- **No escribe `producto_canonico_id` ni ninguna tabla.** Solo produce `reportes/simulacion_clusters.md` +
  un `clusters.jsonl` de trabajo: membresías, exemplar, nivel, **todos los pares internos con su etiqueta
  (SI/NO/INSUF/NO_EVALUADO)**, conflictos, **componentes ambiguos con sus particiones alternativas** (§2b),
  y el resultado de **cada invariante verificable** (lista al final del documento).
- Permite inspeccionar clústeres, conflictos y métricas **antes** de cualquier migración o escritura.
- Parametrizable por τ (densidad) y por categoría, para comparar clique estricto vs asistido.
Es la superficie de evaluación obligatoria previa a escribir nada.

## 7. Métricas de calidad de clústeres y cobertura

**Separar dos cosas que no son lo mismo:** (A) **controles estructurales internos** — propiedades del grafo
de veredictos, calculables sin etiquetado humano — y (B) **precisión real** — si el clúster agrupa productos
que de verdad son el mismo, medida por **revisión independiente**. **Un clique perfecto según el verificador
(0 NO, todos SI) puede contener equivalencias incorrectas** si el verificador se equivocó; los controles
estructurales **no** detectan eso.

### A. Controles estructurales (automáticos, por construcción; se verifican, no se asumen)
- **Pureza:** % de clústeres con **0 pares ESP=NO** internos (debe ser 100%; es invariante, se comprueba).
- **Completitud de clique:** % de clústeres con **todos** los pares internos ESP=SI explícito (sin INSUF ni
  NO_EVALUADO). Clique estricto ⇒ 100%.
- **Densidad de SI:** fracción de pares internos SI (relevante solo en la variante relajada).
- **Cobertura de evaluación:** % de pares internos que tienen veredicto (no NO_EVALUADO) — mide cuánto se
  apoya el clúster en comparaciones reales vs huecos del blocker.
- **Ambigüedad:** nº de componentes con partición no única (§2b) enviados a revisión.
- **Conflictos:** nº de descripciones a revisión por cannot-link / ambigüedad.
- **Estabilidad entre versiones:** % de descripciones que cambian de clúster entre corridas (debe ser bajo).

### B. Precisión real (requiere revisión independiente — NO la dan los controles A)
- **Precisión de clúster:** % de clústeres sin ninguna descripción intrusa, etiquetando clústeres completos
  sobre **unidades independientes** (Etapa 3 §3). La precisión por pares **no** la garantiza.
- Es la métrica que condiciona la **fusión automática persistente**; los controles A son necesarios pero
  **no suficientes**. Un clique estructuralmente perfecto sigue requiriendo validación B antes de persistir.

### Cobertura (descripciones, no pares)
- % de descripciones en clúster **confirmado**, vs **candidato/singleton** (INSUF/NO_EVALUADO), vs **en
  revisión** (conflicto/ambigüedad). Distribución de **tamaños** de clúster y nº de singletons.

## 8. Separación entre agrupación y agregación de demanda (anti-doble-conteo)
**Son dos etapas distintas. La Etapa 4 produce IDENTIDAD, no demanda.**
- **Agrupación (Etapa 4):** asigna `producto_canonico_id`. **No suma cantidades ni montos.**
- **Agregación de demanda (etapa posterior, separada):** suma por `producto_canonico_id`, pero **primero debe
  deduplicar la fuente**. Riesgo real en el esquema: `hist_items.fuente ∈ {form110, form220, dbc, …}` — el
  **mismo ítem económico** puede aparecer en varias filas por distinta fuente. Sumar `monto_total` a ciegas
  **doble-cuenta**. Reglas anti-doble-conteo (para esa etapa, no ahora):
  - Deduplicar antes de sumar (una fila por ítem económico). **(cuce, nro_item) es una HIPÓTESIS de clave,
    no un supuesto:** debe **validarse con los datos reales** antes de la agregación (comprobar si hay
    colisiones, lotes, re-ediciones o múltiples filas legítimas por ítem que la rompan). Si no identifica
    de forma única, definir la clave correcta a partir de la evidencia antes de sumar nada.
  - **No mezclar magnitudes:** `precio_referencial`/`cantidad` (requerido, FORM110/100) ≠ `precio_adjudicado`/
    `monto_total` (adjudicado, FORM220/200) ≠ `monto_ejecutado` (ejecutado, FORM500). Son tres preguntas
    distintas; nunca se suman entre sí.
  - La agregación declara explícitamente **qué magnitud** responde (demanda requerida vs adjudicada vs
    ejecutada) y sobre qué universo de ítems deduplicados.
- Mantener el **veredicto de equivalencia** (Etapa 3), la **autorización a fusionar** (criterios §2) y la
  **agregación** como tres capas separadas, cada una con su control.

---

## Invariantes verificables (contratos que la simulación debe comprobar y reportar)
Cada uno es comprobable automáticamente sobre la salida, sin etiquetado humano:
1. **Sin NO interno:** ningún clúster contiene un par ESP=NO. (pureza = 100%)
2. **Clique completo:** en todo clúster *confirmado*, **todos** los pares internos son ESP=SI explícito;
   **0** pares INSUF o NO_EVALUADO internos.
3. **Anti-transitividad:** no existe clúster con un par interno cuyo veredicto sea NO_EVALUADO o INSUF
   "asumido" como SI. (ninguna relación completada por transitividad)
4. **Unicidad:** todo clúster confirmado proviene de un componente con partición única; los ambiguos están
   en `revision`, no en `confirmado`, con sus alternativas enumeradas.
5. **INSUF/NO_EVALUADO no fusionan:** ninguna descripción solo-INSUF o solo-NO_EVALUADO aparece fusionada.
6. **Conservación:** cada descripción está en exactamente un estado {confirmado, candidato/singleton,
   revisión}; la unión de los tres = universo, sin solapes ni pérdidas.
7. **Sin escritura:** la corrida de simulación no modifica `producto_canonico_id` ni ninguna tabla (se
   verifica que no hubo statements de escritura).
8. **Reproducibilidad:** misma entrada + misma `corrida_version` ⇒ misma salida (hash estable).
Un fallo de cualquier invariante 1–6 es un bug del algoritmo; 7–8 son contratos de seguridad/operación.

## Puertas antes de implementar (recordatorio)
- **Simulación read-only (§6):** se autorizará por separado tras aprobar este diseño, **sin exigir
  previamente** la validación estadística de fusiones. No escribe nada, no asigna identificadores canónicos
  definitivos, no agrega cantidades ni montos; sirve para inspeccionar clústeres, conflictos, ambigüedades e
  invariantes sobre los datos existentes.
- **Fusión automática persistente:** sigue **bloqueada** hasta (1) diseño aprobado, (2) migración de esquema
  aprobada, y (3) **validación independiente por unidades independientes** con la precisión real (métrica B,
  §7) que exigen los criterios de la Etapa 3. La simulación informa; no autoriza persistir.
- **Agregación de demanda:** etapa aparte y posterior, con su propia validación de la clave de deduplicación
  (§8) y de las magnitudes.
