# 03 — Resultados y validación

_Fecha de auditoría: 2026-11-07. Commit HEAD: `1240e70`._
_Regla de este documento: cada métrica indica, cuando es posible, **fecha de ejecución, versión/commit, conjunto evaluado, denominador y archivo de evidencia**. No se reutilizan métricas viejas como si fueran actuales. Donde no hay medición fiable, se dice "no disponible" en vez de inventarla._

---

## 0. Taxonomía de resultados (cómo leer este documento)

- **(E) Exploratorio** — corrida de observación sobre todo el corpus; describe el comportamiento del sistema, NO mide precisión contra verdad de terreno.
- **(R) Regresión** — comparación contra un conjunto chico revisado a mano, para detectar cambios de comportamiento entre versiones.
- **(I) Evaluación independiente** — scoring contra una muestra etiquetada por separado.
- **(NV) No verificado / no disponible** — métrica que todavía no se puede calcular de forma fiable.

---

## 1. Volumen de datos (en vivo, 2026-11-07, count exact Supabase)

| Métrica | Valor | Denominador / nota |
|---|---:|---|
| `hist_items` | 7.441 | registros económicos |
| `hist_procesos` | 965 | procesos (CUCE) |
| `hist_procesos` con DBC | 511 | de 965 (53%) |
| Entidades distintas | 7 | `entidad_codigo` |
| Descripciones distintas (raw `lower()`) | 4.966 | de 7.441 ítems |
| `especificaciones` DBC por ítem | 0 | de 7.441 → **no persistido** |
| `hist_productos_canonicos` | 1 | catálogo canónico |
| `hist_items.producto_canonico_id` asignado | 36 | todos → canónico id 1 |

> **DBC disponibles:** 511 procesos marcados `tiene_dbc=true` en BD. El texto extraído vive en disco (`scraper/salidas`, memoria `historico-cobertura-dbc`); su conteo exacto de archivos no se midió en esta auditoría (no se listó el disco) → **(NV)** para "nº de archivos DBC en disco".

---

## 2. Cobertura del extractor por categoría (enfoque B)

**Categorías modeladas (8):** `llanta, sobre_manila, papel_bond, papel_continuo, papel_impreso, ram, almacenamiento, optico`.
_Fuente: `monitor/canonicalizacion/extractor_atributos.py` (congelado), verificado por grep de claves._

- **(E)** De las ~5.067 descripciones únicas (denominador `cuerpo()`, commit `1240e70`), **solo ~340 entran en pares candidatos** (las que caen en esas 8 categorías). El resto (~4.700) no se modela todavía.
- **(E)** Auditoría de extracción (`reportes/auditoria_extraccion.md`, 2026-11-07): sobre los atributos primarios, **0 fallos del extractor**; 3 casos "no modelado" (gaps conocidos, no errores de parseo): medidas compuestas de papel continuo (9½×5½), formato "3×90", moto 2.75/18.

## 3. Cobertura del blocker (Etapa 2)

- **(E)** Corrida exploratoria: **~9.828 pares candidatos** generados dentro de las 8 familias.
  Evidencia: `reportes/blocker_cobertura.md`, `reportes/blocker_candidatos_muestra.csv` (2026-11-07).
- El blocker NUNCA fusiona; solo propone pares a comparar.

## 4. Resultados del verificador por niveles (Etapa 3)

- **(E)** Corrida completa sobre los ~9.828 pares (verificador congelado, commit de cierre `72afa0f`; reporte 2026-11-07):
  - **595 pares ESP=SI**
  - **2.699 pares ESP=INSUF**
  - resto NO
  - **0 violaciones de jerarquía** (ESP=SI ⟹ SUB=SI ⟹ FAM=SI)
  - Evidencia: `reportes/auditoria_final.md`, `reportes/verificador_reporte.md`, `reportes/verificador_veredictos_muestra.csv`.
- Descomposición de los 595 ESP=SI por categoría (de `auditoria_final.md`): bond 474, continuo 76, óptico 22, sobre 15, impreso 6, llanta 2.
- **Perfil de riesgo (E):** casi todas las discrepancias con el criterio humano fueron "humano INSUF → propuesta SI" (más prudente). Excepciones auditadas una a una: 7 casos INSUF→SI y 2 casos NO→INSUF.

## 5. Corrección de llantas (fix4) — regresión

- **(R)** `reportes/correccion_llantas.md` (2026-11-07): huella/pliegues como discriminantes solo-contradicción. Efecto: **2 pares INSUF→NO** (recuperación intencional), **595 ESP=SI intactos**, 0 colateral.
- **(R)** Regresión del verificador: muestra v2 22/22/22; muestra de 53, 53/49/51; regresión del extractor 11/11.
  Evidencia: `reportes/scoring_verificador.md`, `reportes/verificador_impacto_correcciones.md`.

## 6. Evaluación independiente

- **(I)** Scoring independiente sobre una muestra de **22 pares de papel** etiquetada por separado.
  Evidencia: `reportes/scoring_verificador2_independiente.md` (2026-11-07).
- **Alcance real:** es una muestra pequeña y de una sola familia (papel). **No** constituye una medición de precisión por categoría representativa del corpus. Ver §10.

## 7. Familias, subfamilias y productos específicos identificados

- El modelo distingue 3 niveles por par (FAM/SUB/ESP), pero **no** existe hoy un conteo persistido de "cuántas familias/subfamilias/productos canónicos" porque la agrupación no se persistió. Lo más cercano:
  - **(E) Simulación Etapa 4** (`reportes/simulacion_clusters.md`, commit `1240e70`, 2026-11-07):
    - **28 clústeres confirmados** (clique único), cubren **129 descripciones**.
    - **1 componente en revisión** (ambiguo, nodo en >1 clique), 8 descripciones.
    - **203 descripciones candidatas** (singleton / INSUF / NO_EVALUADO).
    - Por categoría: papel_bond 9 clústeres (67 desc), papel_continuo 5 (23), sobre_manila 5 (14), papel_impreso 4 (9), optico 3 (12), llanta 2 (4).
    - Tamaños mayores: [22, 21, 9, 6, 5, 5, 5, 4, …].
  - Universo de la simulación: 5.067 descripciones (denominador `cuerpo()`), de las cuales 340 participan en pares; 9.828 pares.

## 8. Grupos canónicos propuestos vs persistidos

- **Propuestos (no persistidos):** 28 clústeres de la simulación (enfoque B) + árbol de taxonomía (enfoque C).
- **Persistidos (en BD):** **1** producto canónico — "Etiqueta/rollo continuo autoadhesivo Brother DK-2205 62mm × 30.48m", 36 ítems (enfoque A, `asignar_canonicos.py`). Verificado en vivo hoy.

## 9. Invariantes de la simulación (controles ESTRUCTURALES) — (E)

Los 8 invariantes dieron **verde** y **no se escribió en la BD** (`reportes/simulacion_clusters.md`, 2026-11-07):
1 sin NO interno · 2 clique completo · 3 anti-transitividad · 4 unicidad · 5 INSUF/NO_EVALUADO no fusionan · 6 conservación · 7 sin escritura · 8 reproducible.

> **Advertencia (crítica):** estos son controles **estructurales**, no de precisión semántica. Un clique estructuralmente perfecto **puede** contener equivalencias incorrectas. Verde aquí ≠ "las fusiones son correctas".

## 10. Pasada de cobertura LLM (enfoque C) — resultados y validación del bug

- **Bug detectado y corregido (2026-11-07):**
  - La corrida del 5-nov quedó **barajada**: mapeo descripción→etiqueta por índice posicional + reuso de checkpoint con corpus crecido. **(I)** Medido: **94,2% de pares hoja↔descripción sin ninguna palabra en común** (de 2.880 ejemplos), 0–20% de coincidencia uniforme por categoría → barajado total.
  - Causa raíz: `et["i"]=b+li` y ejemplos vía `descripciones[idx]` global. Corregido atando el texto de la descripción a la etiqueta al etiquetar.
  - **(R) muestra limpia:** 5,8% → 92,2% de coincidencia (las no-coincidencias restantes son falsos negativos de la heurística, no barajado).
- **Re-corrida completa (2026-11-07), validación:**
  - **(I)** **93,4% de coincidencia cruda** hoja↔descripción (de 3.446 ejemplos); no-coincidencias revisadas a mano → todas correctas (ej. hoja `TN 316` ← "TONER BROTHER TN 316 NEGRO"). **Mapeo efectivamente correcto.**
  - **Cifras:** 4.351 descripciones etiquetadas (de 4.966 leídas; ~615 sin etiqueta por lotes que devolvieron menos ítems). **576 categorías crudas · 2.406 hojas.**
  - **(NV / incompleto):** la fase de **consolidación** (unificar nombres de categoría + fusionar hojas equivalentes) **falló a mitad por cupo diario de Groq (TPD)** → 576 nombres crudos en vez de ~100. El mapeo descripción→hoja NO depende de esto. Se completa con `canonicalizar_taxonomia.py --solo-consolidar` cuando resetee el cupo.
  - Mapa de cobertura por familia: ver `monitor/canonicalizacion/entrega_chatgpt/02_cobertura_taxonomia.md`. Familia #1 sin modelar = **impresión (tóner/cartuchos/tinta/tambores/fusores, ~640 descripciones)**.

## 11. Casos de fusiones incorrectas detectadas

- **Enfoque C, corrida 5-nov:** fusiones groseramente incorrectas (hoja "Cartucho Epson L210" conteniendo "CAJA DE CONEXIÓN ELÉCTRICA", "CREDENZA", "CONVERSOR VGA A HDMI"). Causa = bug de mapeo, ya corregido. Evidencia: respaldo en `monitor/_taxo_backup_barajada/`.
- **Enfoque B:** no se detectaron fusiones incorrectas en los controles estructurales, **pero** no se han buscado con una muestra de verdad de terreno (ver §13). Ausencia de detección ≠ ausencia de error.

## 12. Casos de equivalencias omitidas

- **(E)** fix1 (fase previa) había quitado huella/pliegues de la identidad de llanta, lo que **omitía** una contradicción válida (semi pantanera vs H/T autopista). Se recuperó con fix4 (2 pares pasaron a NO). Evidencia: `reportes/correccion_llantas.md`.
- **(E)** El extractor tiene 3 gaps "no modelado" (§2) que provocan INSUF donde un humano quizás agruparía; p. ej. 4 descripciones de papel continuo "pelado" generan 239 pares INSUF por ausencia de medida. Evidencia: `reportes/auditoria_extraccion.md`.

## 13. Limitaciones conocidas de la validación

- **(NV) Precisión REAL del verificador por categoría:** no medida. Falta una muestra NUEVA etiquetada a mano a 3 niveles (positivos, negativos duros, insuficientes), con diseño que controle la **dependencia entre pares** (los 474 pares ESP=SI de bond salen de solo 67 descripciones / 9 clústeres → n efectivo ≪ n de pares).
- **(NV) Objetivo 98% para fusión automática:** no demostrado.
- **(NV) Precisión del árbol de taxonomía (enfoque C):** solo se validó que el **mapeo** descripción→hoja es correcto; la **corrección de las agrupaciones** (que dos hojas sean el mismo producto) no se evaluó contra verdad de terreno.

## 14. Ejemplos reales de agrupaciones correctas (E)

De `reportes/simulacion_clusters.md` (enfoque B, inspección visual):
- **papel_bond (22 desc)** → exemplar "PAPEL BOND; TAMAÑO OFICIO; 75 GRS; BLANCO; PAQUETE" agrupa variantes tipográficas del mismo bond oficio 75g blanco.
- **optico (6 desc)** → "DISCO COMPACTO; 4.7 GB; DVD+R 8X; VIRGEN CON CAJA PLÁSTICA" agrupa variantes de puntuación/acentos.
- **papel_continuo** → clústeres separados correctamente por medida (9½×11×2 vs ×3 vs ×4×5.5), que es justo lo que debe discriminar.

## 15. Resumen de qué está medido vs no

| Afirmación | Tipo | Estado |
|---|---|---|
| El extractor no inventa atributos primarios | (E) | Sostenido (0 fallos en auditoría) |
| El verificador respeta la jerarquía y es reproducible | (E)/(R) | Sostenido |
| Las correcciones empujan hacia prudencia (SI→INSUF), salvo 7/2 auditados | (E) | Sostenido |
| Los clústeres cumplen invariantes estructurales | (E) | Sostenido (verde) |
| El mapeo de la taxonomía es correcto | (I) | Sostenido (93,4%) |
| **Las fusiones propuestas son semánticamente correctas** | — | **NO medido** |
| **Precisión ≥98% para fusión automática** | — | **NO demostrado** |
| **Consolidación del árbol de taxonomía** | — | **Incompleta (cupo Groq)** |
