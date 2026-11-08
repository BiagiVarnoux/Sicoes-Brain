# 02 — Arquitectura REAL de Sicoes-Brain

_Fecha: 2026-11-07. Commit HEAD: `1240e70`. Describe cómo funciona el sistema hoy, no cómo se planeó._

---

## 1. Estructura del proyecto

```
Sicoes-Brain/
├─ app/                      # Dashboard Next.js (App Router, TypeScript) → Vercel
│  └─ src/
│     ├─ app/historico/...   # vistas de histórico (entidad, proceso, proveedor, producto, análisis)
│     ├─ app/radar/...       # vistas del radar de convocatorias
│     ├─ components/         # charts (Recharts), tablas, filtros
│     └─ lib/                # historico.ts, queries.ts, supabase.ts, types.ts
├─ scraper/                  # navegación SICOES (Playwright) + venv de Python del proyecto
├─ monitor/                  # TODO el backend de datos (scrapers, parsers, canonicalización)
│  ├─ schema_historico.sql   # DDL del histórico (hist_procesos, hist_items, hist_productos_canonicos)
│  ├─ schema.sql             # DDL del radar/erp
│  ├─ asignar_canonicos.py   # [A] asignador canónico declarativo (ESCRIBE BD)
│  ├─ canonicalizar_taxonomia.py  # [C] pasada de cobertura LLM (read-only)
│  ├─ dbc_*.py               # descarga / markdown / OCR / specs del DBC
│  └─ canonicalizacion/      # [B] pipeline experimental por atributos (read-only, aislado)
│     ├─ extractor_atributos.py   (Etapa 1)
│     ├─ blocker_candidatos.py    (Etapa 2)
│     ├─ verificador_niveles.py   (Etapa 3)
│     ├─ simulacion_agrupacion.py (Etapa 4, simulación)
│     ├─ migracion_etapa4.sql     (BORRADOR, no aplicada)
│     ├─ congelado/               (snapshots inmutables de versiones cerradas)
│     └─ reportes/                (evidencia: auditorías, CSVs, simulación)
└─ docs/estado_proyecto/     # este paquete de documentación
```

## 2. Tecnologías y dependencias

- **Frontend/dashboard:** Next.js (App Router) + React + TypeScript + Recharts; desplegado en Vercel (push a `main` despliega).
- **Backend de datos:** Python 3.13 (venv en `scraper/venv`), `urllib`/`requests`, Playwright para navegación, Tesseract (spa) para OCR.
- **Base de datos:** Supabase (PostgreSQL + PostgREST), proyecto `envohbgqbxukutnbqcxr`. RLS: lectura pública (anon) para el dashboard; escritura con service key del `.env`.
- **LLM:** Groq (`openai/gpt-oss-120b`) para la pasada de cobertura y para el clasificador del radar; failover multi-key. (Gemini soportado como backend alterno.)

## 3. Fuentes de datos

- **Portal SICOES** (formularios estandarizados por proceso): FORM100/110 (requerido), FORM200/220 (adjudicado), FORM500 (recepción/ejecución). Backbone **determinista**, sin IA.
- **DBC** (Documento Base de Contratación, `.docx`/PDF/imagen): solo en modalidades ANPE/ANPP/LP. Da especificaciones finas. Se procesa con parser + OCR.
- **UNSPSC**: código de catálogo que trae cada entidad. Se conserva como referencia pero **se trata como ruido** para decidir equivalencia de productos.

## 4. Flujo de datos (adquisición → histórico → canonicalización → dashboard)

```mermaid
flowchart TD
    subgraph ADQ["Adquisición (scraper, ESCRIBE BD)"]
        SIC["Portal SICOES"] -->|Playwright| NAV["sicoes_nav.py"]
        NAV --> FORMS["Parser FORM100/110/200/220/500<br/>(determinista, sin IA)"]
        NAV --> DBCDL["Descarga DBC (POST+Turnstile)<br/>redescargar_dbc.py"]
        DBCDL --> DBCMD["DBC→Markdown + OCR<br/>dbc_store.py / dbc_ocr.py<br/>(en DISCO: scraper/salidas)"]
        DBCMD -.->|specs por ítem<br/>NO PERSISTIDO hoy| SPECS["dbc_specs.py"]
    end

    FORMS -->|datos ORIGINALES| HP[("hist_procesos")]
    FORMS -->|datos ORIGINALES| HI[("hist_items<br/>desc, cantidad, precios, proveedor")]
    SPECS -.->|especificaciones = vacío| HI

    subgraph CANON["Canonicalización"]
        direction TB
        A["A. asignar_canonicos.py<br/>matchers declarativos<br/>(ESCRIBE BD)"]
        B["B. Pipeline por atributos (read-only)<br/>extractor→blocker→verificador→clique"]
        C["C. Pasada cobertura LLM (read-only)<br/>canonicalizar_taxonomia.py"]
    end

    HI --> A
    HI --> B
    HI --> C
    A -->|producto_canonico_id<br/>ASIGNACIÓN (1 prod/36 ítems)| HI
    A -->|upsert| HC[("hist_productos_canonicos<br/>(1 fila)")]
    B -->|PROPUESTA, no persistida| SIM["reportes/simulacion_clusters.md<br/>28 clústeres"]
    C -->|PROPUESTA, no persistida| TAX["taxonomia_propuesta.json<br/>mapa de cobertura"]

    subgraph DASH["Dashboard (Next.js, LEE BD)"]
        H["historico.ts<br/>agruparProductos()"]
    end
    HP --> H
    HI --> H
    HC --> H
    H -->|"c:&lt;id&gt; si hay canónico,<br/>si no d:&lt;desc&gt; (provisional)"| VIEW["Vistas: entidad / proceso /<br/>proveedor / producto / análisis"]
```

**Lectura del diagrama:** el único lazo cerrado hoy es **A → `hist_items.producto_canonico_id` → dashboard**. B y C producen **propuestas en archivos**, no tocan la BD.

## 5. Extracción de productos y atributos (Etapa 1, enfoque B)

`extractor_atributos.py`: dada una descripción, detecta su **categoría** (de 8 modeladas) y extrae/normaliza atributos (medida, gramaje, color, marca, modelo del consumible, capacidad, generación…). Devuelve `{atributos, evidencia, nivel_identificable, faltantes, ambiguos}`. Congelado en `congelado/extractor_atributos_etapa1_cerrada.py`.

## 6. Generación de candidatos (Etapa 2, blocker)

`blocker_candidatos.py`: agrupa descripciones por **familia amplia (= categoría)** y emite pares candidatos GRUESOS dentro de cada familia. **Nunca fusiona**; solo decide qué pares vale la pena comparar. Función `cuerpo()` normaliza el texto base (sensible a mayúsculas → define el denominador "5.067").

## 7. Verificación de equivalencias (Etapa 3)

`verificador_niveles.py`: por cada par candidato emite **3 veredictos independientes** con jerarquía:

- **FAMILIA_AMPLIA** / **SUBFAMILIA** / **PRODUCTO_ESPECIFICO**, cada uno ∈ {SI, NO, INSUF}.
- Jerarquía: ESP=SI ⟹ SUB=SI ⟹ FAM=SI.
- **Reglas duras:** atributo ausente nunca se asume igual (como mucho INSUF, nunca SI); contradicción confirmada → NO.
- Flags de corrección aislables (`fix1..fix4`), p. ej. fix4 = huella/pliegues de llanta como discriminantes solo-contradicción.
- `IDENT[cat]` define, por categoría, qué atributos deben coincidir para ESP. Congelado en `congelado/`.

## 8. Agrupación canónica por niveles (Etapa 4, diseño + simulación)

`simulacion_agrupacion.py` (read-only):

- Grafo de aristas **ESP=SI**; clúster = **clique COMPLETO** (todos los pares internos ESP=SI explícito, 0 NO interno). **No** se usan componentes conexos (evita transitividad A=B, B=C ⇏ A=C).
- Bron–Kerbosch para cliques maximales; si un nodo cae en >1 clique → a **REVISIÓN**, nunca se elige en silencio.
- 4 estados de relación: **SI / NO / INSUF / NO_EVALUADO**. INSUF y NO_EVALUADO no fusionan.
- Verifica 8 invariantes y escribe `reportes/simulacion_clusters.md`. **No escribe en la BD.**

## 9. Tratamiento de incertidumbre y conflictos

- **INSUF** (evaluado inconcluso) ≠ **NO_EVALUADO** (par nunca comparado): ninguno de los dos fusiona.
- **Veredicto de equivalencia ≠ autorización a fusionar.** Fusionar exige ESP=SI.
- Conflictos de clique (no-unicidad) → revisión humana.
- Diseño de **log de eventos append-only** (`ASIGNACION/REVOCACION/SUSTITUCION`) para que toda fusión sea reversible y auditable (en `migracion_etapa4.sql`, **no aplicado**).

## 10. Persistencia y estructura de base de datos

Tres tablas del histórico (`monitor/schema_historico.sql`):

- **`hist_procesos`** (PK `cuce`): un renglón por proceso. Datos ORIGINALES del portal.
- **`hist_items`** (PK `id`, FK `cuce`, FK `producto_canonico_id`): un renglón por ítem económico. Campo `fuente` (form110/form220/dbc) → puede repetir filas por ítem. Datos ORIGINALES + `producto_canonico_id` (asignación) + `especificaciones` (derivado DBC, hoy vacío).
- **`hist_productos_canonicos`** (PK `id`): catálogo de bienes canónicos. Hoy 1 fila.

`migracion_etapa4.sql` (BORRADOR) añadiría `nivel/parent_id/atributos jsonb/exemplar_item_id/metodo/confianza/corrida_version` + tabla `hist_canonico_eventos` (append-only) + vista `hist_canonico_vigente`. **No aplicada.**

## 11. Integración con el dashboard y consultas

`app/src/lib/historico.ts`:
- `fetchHistorico()` trae `hist_procesos`, `hist_items` (con todos los campos económicos + `producto_canonico_id`) y `hist_productos_canonicos`.
- `productoKey(it)` = `c:<producto_canonico_id>` si existe; si no `u:<unspsc>`/`d:<descripcion normalizada>` → marcado **provisional** (`isProvisional`).
- `agruparProductos()` agrupa ítems en productos; la etiqueta sale del canónico o de la descripción.
- Vistas en `app/src/app/historico/*`: entidad, proceso (`[cuce]`), proveedor, producto (`[key]`), y `analisis` (ritmo de pedido, proyección de demanda, estacionalidad).

## 12. Clasificación de datos: original / derivado / propuesto

| Dato | Clase | Dónde |
|---|---|---|
| CUCE, entidad, modalidad, fechas, objeto | **ORIGINAL** (del portal) | `hist_procesos` |
| descripción, unidad, cantidad, precio_referencial, precio_adjudicado, monto_ejecutado, proveedor, UNSPSC | **ORIGINAL** (de los FORM) | `hist_items` |
| texto del DBC (Markdown/OCR) | **ORIGINAL** (del pliego) | disco (`scraper/salidas`) |
| `especificaciones` finas por ítem | **DERIVADO** (parseo IA del DBC) | `hist_items.especificaciones` (**vacío hoy**) |
| atributos del extractor (medida, gramaje, modelo…) | **DERIVADO** (parseo determinista) | en memoria / reportes (no en BD) |
| veredictos ESP/SUB/FAM, clústeres | **PROPUESTO** (no persistido) | `reportes/*` |
| árbol de taxonomía LLM | **PROPUESTO** (no persistido) | `taxonomia_propuesta.json` |
| `producto_canonico_id` | **ASIGNACIÓN** (persistida, reversible) | `hist_items` (hoy solo 36 filas, del enfoque A) |

## 13. Separación entre componentes antiguos y nuevos

- **Antiguo / base (producción):** scraper + forms + DBC + radar + dashboard + asignador declarativo `asignar_canonicos.py`. Es lo que vive en la BD y en Vercel.
- **Nuevo / experimental (aislado en `monitor/canonicalizacion/`):** el pipeline por atributos de 3 niveles y su simulación de agrupación. Es read-only, reproducible y **todavía no conectado** a producción.
- **Nuevo / auxiliar:** la pasada de cobertura LLM (`canonicalizar_taxonomia.py`), que solo informa prioridades.

El límite es deliberado: nada del bloque experimental escribe en la BD de producción ni en el dashboard hasta que su precisión real esté medida y se apruebe la persistencia reversible.
