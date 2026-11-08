# Canonicalización de productos (SICOES histórico) — Estado actual

_Documento de contexto para revisión externa. Fecha: 2026-11-07._

Este documento resume **dónde estamos, qué está validado y qué no, qué falta y qué hay que mejorar**
en la canonicalización de productos del histórico de compras SICOES. Los documentos de respaldo
citados están en esta misma carpeta.

---

## 1. Objetivo

Analizar la **demanda histórica de productos** del Estado boliviano cruzando ~10 entidades. Para eso hay
que agrupar las descripciones de ítems comprados (texto libre, escrito distinto por cada entidad) en
**productos canónicos comparables**, SIN fusionar productos comercialmente distintos.

> El objetivo NO es maximizar coincidencias, sino identificar demanda histórica **comparable** sin mezclar
> productos diferentes. Un falso positivo (fusionar dos productos distintos) contamina el análisis de
> demanda; es peor que dejar dos descripciones sin agrupar.

**Universo de datos** (cifras actuales, medidas, no estimadas):
- `hist_items` ≈ **7.441 registros** económicos (cada uno con cantidades/precios por FORM).
- **~5.067 descripciones únicas** de producto (texto). Todo el trabajo de agrupación opera sobre las
  descripciones únicas, no sobre los 7.441 registros.
- Las cantidades/precios autoritativos vienen de los campos FORM de `hist_items` (requerido/adjudicado/
  ejecutado), NO del texto. La agregación de demanda es una etapa posterior y separada.

---

## 2. Decisión de método (y por qué)

**Entity resolution por extracción de atributos → llave determinista. NO embeddings.**

- Cada descripción se **parsea** en atributos estructurados (marca, modelo del consumible, medida,
  capacidad, gramaje, color…). Dos ítems son el mismo producto si sus atributos de identidad coinciden.
- NO se usa similitud de texto / embeddings: dos descripciones pueden parecerse mucho y ser productos
  distintos (62 mm ≠ 102 mm; 8 GB ≠ 16 GB; 78A ≠ 78X), y al revés.
- El **prefijo de categoría UNSPSC** que trae cada entidad es RUIDO y no se usa como verdad.
- La **granularidad la cura un humano** por categoría (qué atributos separan y cuáles no).

**Modelo de 3 niveles** (cada par candidato recibe 3 veredictos independientes):
- **FAMILIA_AMPLIA** — mismo tipo de producto (equivalencia comercial amplia).
- **SUBFAMILIA** — familia + atributos de segmento (misma familia de demanda).
- **PRODUCTO_ESPECIFICO** — + atributos de intercambiabilidad (identidad exacta).
- Cada nivel ∈ {SI, NO, INSUF}. Jerarquía lógica: ESP=SI ⟹ SUB=SI ⟹ FAM=SI.
- **Regla dura:** un atributo AUSENTE nunca se asume igual → como mucho INSUF, nunca SI. Una
  contradicción confirmada → NO.

**Separación conceptual clave (3 cosas distintas):**
1. **Extracción** (qué atributos tiene la descripción) — Etapa 1.
2. **Bloqueo / generación de candidatos** (qué pares vale la pena comparar) — Etapa 2.
3. **Verificación** (qué nivel de equivalencia tiene cada par) — Etapa 3.

Y además: **el veredicto de equivalencia es distinto de la autorización a fusionar.** Fusionar exige
ESP=SI; INSUF nunca fusiona.

---

## 3. Estado por etapa (con números medidos)

### Etapa 1 — Extractor de atributos · CERRADA (provisional)
- `extractor_atributos.py`. Extrae y normaliza atributos por categoría. Devuelve
  {atributos, evidencia, nivel_identificable, faltantes, ambiguos}.
- Con regresión contra 4 muestras revisadas a mano + controles negativos (`regresion_extractor.py`).
- Auditoría de extracción (`reportes/auditoria_extraccion.md`): sobre los atributos primarios,
  **0 fallos del extractor**; 3 casos de "no modelado" (gaps de modelado conocidos, no errores de parseo).

### Etapa 2 — Blocker de candidatos · construida
- `blocker_candidatos.py`. Genera pares candidatos GRUESO por familia amplia (= categoría). NUNCA fusiona.
  Descartes agregados y auditables.

### Etapa 3 — Verificador de 3 niveles · CERRADA como experimental-reproducible
- `verificador_niveles.py`. Por cada par candidato emite los 3 veredictos con jerarquía y conservación.
- **Resultado de la corrida** (`reportes/auditoria_final.md`): sobre ~9.828 pares candidatos →
  **595 pares ESP=SI**, **2.699 ESP=INSUF**, resto NO. 0 violaciones de jerarquía.
- Perfil de riesgo auditado: todas las discrepancias con el criterio humano eran "humano INSUF →
  propuesta SI" (más prudente), salvo 7 INSUF→SI y 2 NO→INSUF que se auditaron una a una.
- Corrección quirúrgica de llantas (`reportes/correccion_llantas.md`, "fix4"): huella/pliegues como
  discriminantes SOLO-contradicción (barro vs carretera = NO; denominación ambigua = INSUF; ausencia NO
  degrada). Efecto: 2 pares INSUF→NO, 595 SI intactos, 0 colateral.
- **Limitación declarada y aceptada:** esta etapa NO demuestra una precisión del 98% ni autoriza fusiones
  automáticas. Los 2.699 pares clasificados ≠ verificados individualmente.

### Etapa 4 — Agrupación · SOLO DISEÑO + simulación read-only
- Diseño v2 aprobado (`reportes/diseno_etapa4.md`), 8 invariantes verificables.
- Clúster = **clique completo** de aristas ESP=SI con 0 NO interno (NO se usan componentes conexos:
  evitan el peligro de transitividad A=B, B=C ⇏ A=C). Bron–Kerbosch para cliques maximales; si un nodo
  cae en >1 clique → a REVISIÓN, nunca se elige en silencio.
- 4 estados de relación: SI (compatibilidad) · NO (incompatibilidad) · INSUF (evaluado inconcluso) ·
  NO_EVALUADO (par nunca comparado). INSUF y NO_EVALUADO no fusionan.
- **Simulación read-only** (`simulacion_agrupacion.py` → `reportes/simulacion_clusters.md`):
  **28 clústeres confirmados** (129 descripciones), **1 componente ambiguo** en revisión, 203 candidatos.
  Los **8 invariantes dieron verde** y **no se escribió nada en la BD**.
- Log de eventos append-only diseñado (ASIGNACION/REVOCACION/SUSTITUCION) para que toda fusión sea
  **reversible y auditable**. Migración de esquema BORRADOR (`migracion_etapa4.sql`), **NO aplicada**.

---

## 4. El cuello de botella real: COBERTURA

El pipeline curado (Etapas 1–3) solo modela **8 categorías**:
`llanta, sobre_manila, papel_bond, papel_continuo, papel_impreso, ram, almacenamiento, optico`.

Consecuencia medida: de las ~5.067 descripciones únicas, **solo ~340 entran en pares candidatos** (las de
esas 8 categorías). Las otras ~4.700 descripciones no se tocan todavía. **El límite NO es el verificador;
es cuántas categorías están modeladas.**

### Pasada de cobertura amplia (taxonomía one-pass por LLM)
Para romper ese techo existe un enfoque PARALELO (`canonicalizar_taxonomia.py`): un LLM etiqueta TODAS las
descripciones en un árbol completo (categoría → subcategoría → producto). Sirve como **mapa de cobertura /
triaje** para saber qué familias concentran volumen y priorizar — **no como fuente de fusiones** (las
fusiones siguen saliendo del pipeline curado y verificable).

- La corrida del 5-nov quedó **inutilizable** (mapeo descripción→etiqueta barajado por un bug de índice
  posicional + reuso de checkpoint con un corpus que había crecido). Se detectó verificando que el 94,2%
  de los pares hoja↔descripción no compartían ninguna palabra.
- **Arreglado:** ahora cada etiqueta lleva atado el texto de su descripción en el momento de etiquetar,
  inmune a cambios de corpus. Verificado en muestra limpia: de 5,8% → ~100% de coincidencia correcta.
- Re-corrida completa (~4.966 descripciones) en curso al momento de escribir esto. Detalle y resultado
  en `02_cobertura_taxonomia.md` (se completa al terminar la corrida).

---

## 5. Qué está VALIDADO vs qué NO (importante)

**Validado / sólido:**
- Arquitectura de 3 funciones separadas y modelo de 3 niveles.
- Reproducibilidad: el verificador corre determinista y está congelado (`congelado/`).
- Controles ESTRUCTURALES de la simulación (0 NO interno, clique completo, unicidad) → verdes.
- El extractor no inventa atributos (0 fallos de parseo sobre primarios en la auditoría).

**NO validado todavía (y hay que ser honestos con esto):**
- **Precisión REAL del verificador.** Un clique estructuralmente perfecto puede contener equivalencias
  incorrectas. Falta una **muestra NUEVA etiquetada a mano a 3 niveles** (positivos, negativos duros,
  insuficientes) para medir precisión real, no solo consistencia estructural.
- El objetivo de **98% de precisión** para fusión automática NO está demostrado. Además, el tamaño de
  muestra efectivo NO es el número de pares: los pares comparten descripciones (p. ej. los 474 pares
  ESP=SI de papel bond salen de solo 67 descripciones únicas / 9 clústeres), o sea están correlacionados;
  n efectivo ≠ n de pares. El plan de validación tiene que controlar esa dependencia.
- Nada está integrado al dashboard ni a producción. Ninguna fusión fue persistida.

---

## 6. Qué FALTA (pendientes, en orden)

1. **Cobertura de categorías.** Usar el mapa de taxonomía para priorizar y extender el extractor curado a
   las familias de mayor volumen (perforadora, archivador, clips, limpieza, tóner/cartuchos, mobiliario…).
2. **Muestra de validación independiente** etiquetada a 3 niveles, con diseño que controle la dependencia
   entre pares, para medir precisión real por categoría.
3. **Agrupación final** con prevención de fusión por transitividad (ya diseñada; falta implementarla fuera
   del entorno aislado cuando la precisión lo justifique).
4. **Persistencia reversible**: aplicar la migración de esquema (parent_id / nivel / atributos jsonb /
   exemplar) + el log de eventos append-only. Hoy es BORRADOR, no aplicado.
5. **Agregación de demanda anti doble-conteo**: una vez agrupado, sumar cantidades/montos sin contar dos
   veces (los `hist_items` repiten filas por `fuente` = form110/form220/dbc; nunca mezclar
   precio_referencial / precio_adjudicado / monto_ejecutado). Esto es una etapa SEPARADA de la agrupación.
6. **Wiring al dashboard** del filtro por producto cross-entity (llave = `producto_canonico_id`).

---

## 7. Qué hay que MEJORAR / riesgos abiertos

- **Precisión real antes de automatizar.** No activar fusión automática hasta tener la medición por
  categoría. Mientras tanto, modo asistido (propone, un humano confirma) para las categorías de más volumen.
- **Dependencia estadística de los pares.** El plan de validación debe medir por unidades independientes
  (descripciones/clústeres), no por pares.
- **Robustez de la pasada LLM de cobertura.** Ya se corrigió el bug de mapeo; falta decidir con qué
  frecuencia se re-corre (el corpus crece: pasó de 4.336 → 4.389 → 4.966 descripciones distintas en pocos
  días por el scraper) y cómo versionar sus salidas.
- **Gaps de modelado del extractor** (3 casos "no modelado" detectados): medidas compuestas de papel
  continuo (9½×5½), formatos raros. Ampliar el extractor con cuidado de no romper regresión.
- **Separar siempre** controles estructurales (baratos, verdes) de precisión real (cara, pendiente). Un
  verde estructural no es evidencia de corrección semántica.

---

## 8. Inventario de archivos (en el repo, entorno aislado `monitor/canonicalizacion/`)

**Código (solo lectura, no toca producción):**
- `extractor_atributos.py` (Etapa 1) · `blocker_candidatos.py` (Etapa 2) · `verificador_niveles.py` (Etapa 3)
- `simulacion_agrupacion.py` (Etapa 4, read-only) · `migracion_etapa4.sql` (BORRADOR, no aplicado)
- `../canonicalizar_taxonomia.py` (pasada LLM de cobertura, paralela)

**Documentos de respaldo en esta carpeta:**
- `00_ESTADO_ACTUAL.md` (este documento)
- `01_criterios_aceptacion_etapa3.md` — criterios de cierre, condiciones de fusión, plan de validación.
- `02_cobertura_taxonomia.md` — mapa de cobertura (se completa al terminar la re-corrida).
- `03_diseno_etapa4.md` — diseño de agrupación + invariantes.
- `04_simulacion_clusters.md` — resultado de la simulación read-only (28 clústeres).
- `05_auditoria_final_verificador.md` — auditoría de los veredictos del verificador.
- `06_correccion_llantas.md` — ejemplo de corrección quirúrgica auditada.
- `07_README_pipeline.md` — README técnico del pipeline.

**Principio transversal:** nada de esto escribe en la base de producción ni en el dashboard. Todo es
reproducible y reversible por diseño.
