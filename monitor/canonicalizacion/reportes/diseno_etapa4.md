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
transitividad: A≡B y B≡C ⇒ A,B,C juntos aunque A≡C nunca se haya verificado (o sea INSUF/NO). **Rechazado.**

**Propuesta: agrupación por CLIQUE anclada en un exemplar, con restricciones cannot-link.**
Modelo de clustering con restricciones:
- **must-link** = par ESP=SI.
- **cannot-link** = par ESP=NO.
- **sin arista** = par INSUF (candidato; no fusiona por sí mismo).

Procedimiento (determinista, por categoría y dentro de cada bloque del blocker):
1. Ordenar las descripciones de forma estable (p. ej. por completitud de atributos de identidad, luego
   alfabética) para que el resultado no dependa del orden de llegada.
2. Para cada descripción `d`:
   - Buscar clústeres existentes cuyos miembros sean **todos ESP=SI con `d`** y **ninguno ESP=NO con `d`**.
   - Si existe exactamente uno → `d` se une (el clúster sigue siendo un **clique**: todo par interno
     verificado ESP=SI directamente).
   - Si no existe ninguno → `d` abre un clúster nuevo con `d` como **exemplar** provisional.
   - Si `d` califica para **dos o más** clústeres a la vez, o tiene ESP=SI con un clúster pero ESP=NO con
     otro miembro candidato → **conflicto** (sección 3): no se asigna automáticamente, va a revisión.
3. Resultado: cada clúster auto-confirmado es un **clique bajo ESP=SI** → **garantía anti-transitividad**:
   no hay ningún par interno que no haya sido verificado SI de forma directa.

**Variante relajada (opcional, solo si el usuario la aprueba):** permitir "casi-clique" con densidad ≥ τ
(fracción de pares internos SI) y **0 pares NO**, marcando el clúster como *asistido* (requiere revisión)
en vez de *confirmado*. Por defecto τ = 1.0 (clique completo) para auto-confirmación.

**Exemplar** = la descripción más completa del clúster (más atributos de identidad presentes); sirve de
etiqueta canónica y de ancla para futuras altas (una nueva descripción debe ser ESP=SI con el exemplar **y**
con todos los miembros, no solo con uno).

## 2. Tratamiento de pares SI / NO / INSUF
| veredicto | rol en la agrupación |
|---|---|
| **ESP=SI** | arista must-link; habilita fusión **dentro del clique** (todos los pares internos SI). |
| **ESP=NO** | arista cannot-link; **prohíbe** que ese par quede en el mismo clúster. Restricción dura. |
| **ESP=INSUF** | **no fusiona.** Queda como *candidato*: singleton o adjunto blando a revisión (sección 4). |

SUBFAMILIA y FAMILIA_AMPLIA no fusionan producto; definen el **nivel** del nodo (jerarquía): un clúster de
ESP=SI es un nodo "producto específico"; agrupaciones más amplias (misma subfamilia) se representan como
nodos padre en el árbol (`parent_id`), **sin** fusionar los productos específicos entre sí.

## 3. Evitar que una descripción termine en grupos incompatibles
- **Enforcement de cannot-link:** un clúster es válido solo si **ningún par interno es ESP=NO**. Antes de
  unir `d`, se comprueba contra todos los miembros; un solo NO bloquea la unión.
- **Detección de conflicto:** si `d` es ESP=SI con miembros de dos clústeres que entre sí tienen algún par
  NO (o que no pueden unirse en un clique), `d` **no se asigna**: se marca `conflicto` y va a una **cola de
  revisión humana**. Nunca se resuelve el empate automáticamente.
- **Transitividad negativa:** si A≡B (SI) y A≠C (NO), entonces B y C quedan en clústeres distintos por
  construcción (C no puede entrar al clique de A porque A-C es NO; y si B intentara unirse a C, se revisa
  B-C directamente). No se propaga el NO como regla transitiva, pero sí se respeta localmente como cannot-link.
- **Invariante final:** todo clúster confirmado cumple (i) clique ESP=SI y (ii) 0 pares ESP=NO internos.
  Cualquier violación posible ⇒ revisión, no asignación.

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

**Log de auditoría append-only (nueva tabla `hist_canonico_asignaciones`):**
`id, item_id, producto_canonico_id, veredicto_origen, razon, corrida_version, decidido_por (auto|humano),
vigente boolean, creado_en`. El puntero `hist_items.producto_canonico_id` es el estado **actual**; el log es
el **historial completo**. 
- **Reversibilidad:** deshacer = marcar `vigente=false` y restaurar el puntero anterior desde el log (o
  volver a una `corrida_version` previa). Nada se borra; toda asignación es un registro nuevo.
- **Versionado:** cada ejecución = una `corrida_version` (timestamp + hash de reglas/umbral). Re-ejecutar
  **no sobrescribe en silencio**: produce una versión nueva y un **diff** contra la anterior (altas, bajas,
  cambios de clúster). Coherente con "fusión persistente pero reversible, con versionado y registro".

## 6. Simulación read-only (evaluar clústeres SIN escribir)
Script propuesto `simulacion_agrupacion.py` (cuando se apruebe): 
- Lee los veredictos del verificador congelado, corre el algoritmo de la sección 1 **en memoria**.
- **No escribe `producto_canonico_id` ni ninguna tabla.** Solo produce `reportes/simulacion_clusters.md` +
  un `clusters.jsonl` de trabajo (membresías, exemplar, nivel, pares internos y su veredicto, conflictos).
- Permite inspeccionar clústeres, conflictos y métricas **antes** de cualquier migración o escritura.
- Parametrizable por τ (densidad) y por categoría, para comparar clique estricto vs asistido.
Es la superficie de evaluación obligatoria previa a escribir nada.

## 7. Métricas de calidad de clústeres y cobertura
Por categoría y agregado, separando **pares** de **descripciones/clústeres**:
- **Pureza:** % de clústeres con **0 pares ESP=NO** internos (debe ser 100% por construcción; se verifica).
- **Densidad de confirmación:** fracción de pares internos que son ESP=SI (vs INSUF toleitale en variante
  relajada). Clique estricto ⇒ 1.0.
- **Conflictos:** nº de descripciones enviadas a revisión por ambigüedad / cannot-link.
- **Cobertura:** % de descripciones en clúster **confirmado**, vs **candidato/singleton** (INSUF), vs **en
  revisión**. Reportado sobre descripciones únicas, no sobre pares.
- **Distribución de tamaños** de clúster (y nº de singletons).
- **Estabilidad entre versiones:** % de descripciones que cambian de clúster entre corridas (debe ser bajo).
- **Precisión de clúster (requiere validación independiente, Etapa 3 §3):** la precisión por pares **no** la
  garantiza; se mide etiquetando clústeres completos (¿hay intrusos?) sobre unidades independientes.

## 8. Separación entre agrupación y agregación de demanda (anti-doble-conteo)
**Son dos etapas distintas. La Etapa 4 produce IDENTIDAD, no demanda.**
- **Agrupación (Etapa 4):** asigna `producto_canonico_id`. **No suma cantidades ni montos.**
- **Agregación de demanda (etapa posterior, separada):** suma por `producto_canonico_id`, pero **primero debe
  deduplicar la fuente**. Riesgo real en el esquema: `hist_items.fuente ∈ {form110, form220, dbc, …}` — el
  **mismo ítem económico** puede aparecer en varias filas por distinta fuente. Sumar `monto_total` a ciegas
  **doble-cuenta**. Reglas anti-doble-conteo (para esa etapa, no ahora):
  - Deduplicar por **(cuce, nro_item)** antes de sumar; una fila por ítem económico.
  - **No mezclar magnitudes:** `precio_referencial`/`cantidad` (requerido, FORM110/100) ≠ `precio_adjudicado`/
    `monto_total` (adjudicado, FORM220/200) ≠ `monto_ejecutado` (ejecutado, FORM500). Son tres preguntas
    distintas; nunca se suman entre sí.
  - La agregación declara explícitamente **qué magnitud** responde (demanda requerida vs adjudicada vs
    ejecutada) y sobre qué universo de ítems deduplicados.
- Mantener el **veredicto de equivalencia** (Etapa 3), la **autorización a fusionar** (criterios §2) y la
  **agregación** como tres capas separadas, cada una con su control.

---

## Puertas antes de implementar (recordatorio)
Nada de esto se codifica hasta: (1) aprobar este diseño; (2) tener la validación independiente por unidades
independientes de la Etapa 3; (3) aprobar la migración de esquema. La fusión automática sigue bloqueada;
el primer entregable implementable será la **simulación read-only** (sección 6), que no escribe nada.
