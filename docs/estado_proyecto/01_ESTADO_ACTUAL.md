# 01 — Estado actual de Sicoes-Brain

_Auditoría del estado REAL del repositorio. Fecha: 2026-11-07. Commit HEAD: `1240e70`._
_Las cifras marcadas "(en vivo)" se midieron hoy contra Supabase en modo lectura; no son estimaciones ni recuerdos._

---

## 1. Objetivo general y utilidad comercial

Sicoes-Brain analiza las compras públicas de Bolivia (portal SICOES). Tiene **dos frentes**:

1. **Radar de convocatorias** (en producción): detecta convocatorias nuevas por fecha para rubros de computación/oficina y las clasifica con IA. (Tablas `convocatorias_radar`, `erp_*`, `convocatoria_specs`; scripts `radar.py`, `clasificador_ia.py`.)
2. **Histórico de demanda** (foco de esta auditoría): reconstruye qué productos pidió el Estado a lo largo del tiempo, cruzando entidades, para analizar **demanda histórica comparable por producto**.

**Utilidad comercial del histórico:** permitir a un proveedor (o al propio Estado) responder "¿cuánto se compra de este producto, quién lo compra, a qué precio y con qué estacionalidad, sumando todas las entidades?". Eso exige agrupar descripciones de ítems escritas de forma distinta por cada entidad en **productos canónicos comparables, sin fusionar productos comercialmente diferentes** (un falso positivo contamina el análisis de demanda y es peor que no agrupar).

---

## 2. Funcionalidades actuales (resumen)

- **Scraper histórico** que baja procesos SICOES por entidad y parsea los formularios (FORM100/110/200/220/500) a tablas estructuradas. **Funciona y poblado** (en vivo: 965 procesos, 7.441 ítems, 7 entidades).
- **Descarga y extracción de DBC** (pliegos) a Markdown en disco, con OCR para los escaneados.
- **Dashboard Next.js** (Vercel) con vistas de histórico por entidad, proceso, proveedor y producto, series de tiempo, estacionalidad y proyección de demanda.
- **Canonicalización de productos** en **tres enfoques distintos y en distinto grado de madurez** (ver §4): un asignador declarativo integrado a producción (mínimo), un pipeline experimental por atributos (read-only, no persistido), y una pasada de cobertura por LLM (read-only, triaje).

---

## 3. Cifras del universo de datos (en vivo, 2026-11-07)

| Métrica | Valor | Fuente |
|---|---:|---|
| `hist_items` (registros económicos) | **7.441** | count exact Supabase |
| `hist_procesos` (procesos / CUCE) | **965** | count exact Supabase |
| `hist_procesos` con `tiene_dbc=true` | **511** | count exact Supabase |
| Entidades distintas (`entidad_codigo`) | **7** | distinct en vivo |
| Descripciones distintas (raw, `lower()`) | **4.966** | distinct en vivo |
| `hist_items` con `especificaciones` (specs DBC) no nulo | **0** | count exact Supabase |
| `hist_productos_canonicos` (catálogo canónico) | **1** | count exact Supabase |
| `hist_items` con `producto_canonico_id` asignado | **36** (todos → canónico id 1) | count exact Supabase |
| `hist_items` con `unspsc_codigo` | **7.441** (100%) | count exact Supabase |

**Notas de denominador (importantes para no confundir métricas):**
- El trabajo de agrupación opera sobre **descripciones únicas**, no sobre los 7.441 registros.
- Hay **dos definiciones de "descripción única"** en el código y dan números distintos: `4.966` (raw en minúsculas, medido hoy) vs `5.067` que reporta la simulación de Etapa 4 (función `cuerpo()`, sensible a mayúsculas, commit `1240e70`). No son contradictorias: `cuerpo()` conserva mayúsculas y por eso cuenta más variantes. Al citar un porcentaje de cobertura hay que decir contra cuál denominador.
- El único producto canónico persistido es **"Etiqueta/rollo continuo autoadhesivo Brother DK-2205 62mm × 30.48m"** (categoría "Consumibles de impresión", 36 ítems). Lo generó `asignar_canonicos.py` (matcher declarativo), **no** el pipeline por atributos.
- **`especificaciones` por ítem está vacía en la BD (0 de 7.441):** el texto del DBC está extraído en disco pero el enriquecimiento fino por ítem **no está persistido**.

---

## 4. Los TRES enfoques de canonicalización (no confundirlos)

Este es el punto que más se presta a malentendidos. Coexisten tres caminos:

| Enfoque | Script | Método | ¿Escribe BD? | ¿Dashboard lo usa? | Estado real |
|---|---|---|---|---|---|
| **A. Asignador declarativo** | `monitor/asignar_canonicos.py` | Matchers de substrings (AND de grupos OR + exclusiones) curados a mano | **Sí** (upsert `hist_productos_canonicos` + PATCH `hist_items.producto_canonico_id`) | **Sí** | **Integrado a producción, pero mínimo: 1 producto, 36 ítems.** |
| **B. Pipeline por atributos (Etapas 1–4)** | `monitor/canonicalizacion/*.py` | Extracción de atributos → blocker → verificador de 3 niveles → clique | **No** (todo read-only) | No | Experimental-reproducible; **0 fusiones persistidas**. |
| **C. Pasada de cobertura (LLM)** | `monitor/canonicalizar_taxonomia.py` | Un LLM etiqueta TODAS las descripciones en un árbol | **No** (genera JSON/MD) | No | Triaje de cobertura; mapeo correcto, consolidación a medias. |

**Relación entre ellos (modelo mental correcto):**
- **A** es lo único en producción hoy; es simple y preciso pero no escala a mano a miles de productos.
- **B** es la apuesta de calidad: decide equivalencias con reglas auditables por atributos, pero todavía **no está conectado** a la BD ni al dashboard.
- **C** no decide fusiones; solo dice "qué familias hay y cuántas descripciones tiene cada una" para **priorizar** qué modelar en B (o curar en A).

---

## 5. Estado por componente

| Componente | Archivo / ruta | Usa BD | Estado |
|---|---|---|---|
| Scraper histórico (navegación + forms) | `scraper/`, `monitor/sicoes_nav.py`, `monitor/c1_parse.py` | Escribe | **IMPLEMENTADO** |
| Parser de formularios FORM100/110/200/220/500 | scraper (backbone determinista) | Escribe | **IMPLEMENTADO** (con bug conocido de alineación FORM100/110, ver §8) |
| Descarga de DBC (POST + captcha Turnstile) | `monitor/redescargar_dbc.py`, `dbc/` | Disco + Storage | **IMPLEMENTADO** |
| DBC → Markdown + OCR escaneados | `monitor/dbc_store.py`, `monitor/dbc_ocr.py` | Disco | **IMPLEMENTADO** |
| Specs finas por ítem desde DBC | `monitor/dbc_specs.py` | Escribe `hist_items.especificaciones` | **PARCIAL / NO PERSISTIDO** (columna vacía en vivo: 0 de 7.441) |
| Catálogo canónico (asignador declarativo) | `monitor/asignar_canonicos.py` | Escribe | **PARCIAL** (1 producto / 36 ítems) |
| Extractor de atributos (Etapa 1) | `monitor/canonicalizacion/extractor_atributos.py` | Lee | **IMPLEMENTADO** (congelado; 8 categorías) |
| Blocker de candidatos (Etapa 2) | `monitor/canonicalizacion/blocker_candidatos.py` | Lee | **IMPLEMENTADO** |
| Verificador 3 niveles (Etapa 3) | `monitor/canonicalizacion/verificador_niveles.py` | Lee | **IMPLEMENTADO** (congelado; precisión real sin medir) |
| Agrupación por clique (Etapa 4) | `monitor/canonicalizacion/simulacion_agrupacion.py` | Lee | **PROTOTIPO** (simulación read-only; 28 clústeres propuestos) |
| Migración de esquema Etapa 4 (event log) | `monitor/canonicalizacion/migracion_etapa4.sql` | — | **PENDIENTE** (BORRADOR, no aplicada) |
| Pasada de cobertura LLM | `monitor/canonicalizar_taxonomia.py` | Lee | **PROTOTIPO** (mapeo OK; consolidación incompleta por cupo Groq) |
| Dashboard histórico (Next.js) | `app/src/app/historico/*`, `app/src/lib/historico.ts` | Lee | **IMPLEMENTADO** (ya cableado a `producto_canonico_id` con fallback) |
| Agregación de demanda anti doble-conteo | — | — | **PENDIENTE** (diseñado, no implementado) |
| Persistencia reversible de fusiones (event log) | — | — | **BLOQUEADO** (espera migración + precisión validada) |

---

## 6. Avances recientes (desde la última revisión con ChatGPT)

1. **Pipeline por atributos Etapas 1–3 construido y auditado** (commits `4627e74`→`71d3478`): extractor, blocker y verificador de 3 niveles, con reportes de auditoría reproducibles.
2. **Cierre formal de Etapa 3** como "experimental-reproducible con limitaciones conocidas" (commit `72afa0f`), criterios de aceptación escritos (`criterios_aceptacion_etapa3.md`).
3. **Diseño de Etapa 4 v2** (clique completo anti-transitividad, 4 estados de relación, 8 invariantes) + **simulación read-only** con 28 clústeres y migración borrador (commits `5a68641`, `1240e70`).
4. **Corrección quirúrgica de llantas (fix4):** huella/pliegues como discriminantes solo-contradicción.
5. **Pasada de cobertura LLM arreglada:** se detectó y corrigió un bug que barajaba el mapeo descripción→etiqueta (ver §8 y doc 03); re-corrida completa validada hoy.
6. **Dashboard** ya preparado para agrupar por `producto_canonico_id` (fallback a UNSPSC y a descripción normalizada, marcando "provisional").

> **No confirmado en commits (cambios locales de hoy):** la pasada de cobertura LLM (`canonicalizar_taxonomia.py`), sus salidas (`taxonomia_*`), la carpeta `monitor/canonicalizacion/entrega_chatgpt/` y este paquete `docs/estado_proyecto/` están **sin commitear** al momento de esta auditoría.

---

## 7. Qué está terminado / parcial / pendiente

- **Terminado:** scraper histórico + forms; descarga y conversión de DBC; extractor/blocker/verificador (como artefactos congelados reproducibles); dashboard histórico.
- **Parcial:** specs DBC por ítem (extraídas en disco, no persistidas en BD); asignador canónico declarativo (1 producto); pasada de cobertura (mapeo OK, consolidación incompleta).
- **Pendiente / bloqueado:** agrupación canónica persistida; event log reversible (migración); agregación de demanda anti doble-conteo; cobertura de las ~130 familias no modeladas; medición de precisión REAL del verificador.

---

## 8. Problemas conocidos y limitaciones

1. **Cobertura es el cuello de botella, no el verificador.** El pipeline por atributos modela **8 categorías** (`llanta, sobre_manila, papel_bond, papel_continuo, papel_impreso, ram, almacenamiento, optico`) y solo ~340 descripciones entran en pares candidatos. La mayoría del volumen sin cubrir está en **impresión (tóner/cartuchos/tinta, ~640 descripciones)**.
2. **Precisión REAL del verificador sin medir.** Los controles estructurales de la simulación están verdes, pero un clique estructuralmente perfecto puede contener equivalencias incorrectas. Falta una muestra NUEVA etiquetada a mano a 3 niveles. El objetivo de 98% para fusión automática **no está demostrado**.
3. **Dependencia estadística de los pares.** Los pares comparten descripciones (474 pares ESP=SI de papel bond salen de 67 descripciones); n efectivo ≠ n de pares.
4. **`especificaciones` DBC no persistida** (0 en vivo): el enriquecimiento fino por ítem no llega a la BD; el motor hoy es "description-only".
5. **Bug de parser FORM100/110** (conocido, pendiente): desalineación por índice fijo que mete basura y pierde el precio referencial en algunos casos (ver memoria `historico-bug-parser-requerido`).
6. **Consolidación de la taxonomía incompleta** por cupo diario de Groq (576 nombres crudos de categoría en vez de ~100); el mapeo descripción→hoja NO depende de esto y es correcto.
7. **Corpus en crecimiento** (4.336 → 4.389 → 4.966 descripciones en pocos días): cualquier salida basada en snapshots necesita fecha/versión.

---

## 9. Evidencia (archivos reales en el repo)

- Auditoría del verificador: `monitor/canonicalizacion/reportes/auditoria_final.md`
- Auditoría de extracción: `monitor/canonicalizacion/reportes/auditoria_extraccion.md`
- Conteos bond (dependencia de pares): `monitor/canonicalizacion/reportes/auditoria_conteos_bond.md`
- Corrección llantas: `monitor/canonicalizacion/reportes/correccion_llantas.md`
- Diseño Etapa 4: `monitor/canonicalizacion/reportes/diseno_etapa4.md`
- Simulación de clústeres: `monitor/canonicalizacion/reportes/simulacion_clusters.md` (+ `.jsonl`)
- Criterios de aceptación Etapa 3: `monitor/canonicalizacion/reportes/criterios_aceptacion_etapa3.md`
- Mapa de cobertura (taxonomía): `monitor/canonicalizacion/entrega_chatgpt/02_cobertura_taxonomia.md`
- Esquema histórico: `monitor/schema_historico.sql`
