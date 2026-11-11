# Bitácora de avance — Inteligencia de mercado histórico (SICOES)

Documento vivo. Fuente única de verdad del estado real, los números medidos, lo
pendiente y las decisiones/errores. **Antes de proponer un cambio, leer la sección
de números: evita rehacer o regresar trabajo que ya funciona.**

Última actualización: 2026-11-10.
Plan rector: [PLAN_INTELIGENCIA_MERCADO.md](../PLAN_INTELIGENCIA_MERCADO.md) ·
Fichas v1: [FICHAS_ADQUISICION_V1.md](FICHAS_ADQUISICION_V1.md) ·
Asociación v2: [ASOCIACION_ADQUISICIONES_V2.md](ASOCIACION_ADQUISICIONES_V2.md)

---

## 1. Estado por etapa (plan de 6)

| Etapa | Estado | Nota |
|---|---|---|
| 1. Extracción documental | **Funciona** | Scraper HTTP guarda originales + Markdown por CUCE. OCR de escaneados pendiente. ~23 forms anunciados-no-descargados (ver §5). |
| 2. Estructuración de observaciones | **Funciona** | 220/200/500 parseados; regresión 2024 verificada; 2.070 observaciones. Deuda: 17 filas FORM 170 (no bloqueante). |
| 3. Atributos + DBC | Parcial | Enriquecimiento 2024 reproducible (198 atributos, 54 bloques). DBC segmentable solo en 26/194 CUCE. |
| Capa de fichas (puente 500↔200/220↔DBC) | **En corrección** | v2 por descripción (ver §3). |
| 4–6 (candidatos, verificador, agrupación) | No iniciado | Módulos experimentales existen; no validados sobre el corpus nuevo. |

---

## 2. Corpus local (verificado)

Ruta: `scraper/historico_local/data/historico_http_paginas_<entidad>_<gestion>/<CUCE>/`.

- **194 manifiestos** (0660-10: 2022–2024; 0660-11: 2023–2026). 188 CUCE con contratación.
- Docs con versión válida: **182 FORM 500, 82 FORM 200, 106 FORM 220** (200 y 220 son el
  mismo formulario en distinta modalidad; ningún CUCE tiene ambos).
- Filas de bienes: 500=1016, 200=665, 220=389.

### Perfil de campos por fila (clave para el matching)

| Campo | FORM 500 | FORM 200 | FORM 220 |
|---|---:|---:|---:|
| `nro_item_documento` | 100% | 100% | 100% |
| descripción | 100% | 100% | 100% |
| `nro_contrato_documentado` en fila | 100% | 100% | **0%** |
| `proveedor_documentado` en fila | — | **0%** | 99% |
| `unidad_medida` | **0%** | 100% | 100% |

**FORM 200 y 220 son espejo:** 200 trae contrato en la fila (proveedor va en el contexto
contractual, ligado por nº de contrato); 220 trae proveedor en la fila (contrato va en el
contexto, ligado por nombre de proveedor — lo resuelve `form220_context.py`).

---

## 3. Asociación recepción↔contratación: el número que importa

**La llave de unión correcta es la DESCRIPCIÓN, no el nro_item.** Verificado: dentro de un
mismo CUCE la descripción normalizada es llave **1:1 perfecta en ambos sentidos**
(1016/1016 filas de 500 → 1 solo ítem de contratación; 0 colisiones inversas; 176/182 CUCE
perfectos). El `nro_item` **se renumera** entre FORM 500 y 200/220, así que solo corrobora;
su diferencia **no es conflicto**.

### Baseline de aristas confirmadas (recepción↔contratación)

| Corrida | Confirmadas | Ambiguas | Descartadas | Nota |
|---|---:|---:|---:|---|
| v1 (regla vieja) | 63 | 8.998 | 0 | exige contrato igual; casi todo ambiguo |
| **v2 previo (bueno)** | **560** | 55 | 8.446 | acierta FORM 200; descarta FORM 220 (no trae contrato en fila) |
| v2 item-key (ERROR, descartar) | 245 | 771 | 8.560 | nro_item como llave primaria → 771 falsas ambiguas |
| v2 por descripción (objetivo) | ~900–1.000 | — | — | descripción 1:1 + corroboración; en corrección por Codex |

Invariantes que deben mantenerse siempre: **2.070 observaciones idénticas a v1, una sola
ficha por observación, montos por etapa idénticos, salidas reproducibles (mismos SHA-256)**.

---

## 4. Hecho hoy (2026-11-10)

- **Diagnóstico de asociación** sobre el corpus completo (perfil de campos, unicidad de
  descripción, cardinalidad multi-proveedor). Confirmó que el 94% ambiguo del informe v1
  era artefacto de la regla, no de los datos.
- **Corrección de asociación v2** encargada a Codex: llave=descripción, dropear
  `contract_equal`, nro_item/contrato/proveedor como corroboración; gate = 75 tests +
  `acquisiciones_referencia_v2.json` (19 pares curados con ítems renumerados). **Pendiente
  de revisión del resultado.**
- **Variante del scraper por CUCE**: `scraper/historico_local/por_cuce.py` (+ tests y
  lanzador). Busca **por nº de convocatoria** (campo `cuce4` del buscador avanzado;
  `cuce1`/`cuce2`/`cuce3` quedan vacíos), así que NO pide entidad ni año: `1199042`
  → variante `-1-1`; `1199042-1-2` llena `cuce5`/`cuce6`. El CUCE completo del
  resultado define la carpeta de guardado (misma ruta que el lanzador por entidad/gestión).
  `buscar()` en `probe_historico.py` se extendió con `num/var1/var2` opcionales (firma
  posicional intacta → el scraper por entidad/año no cambia). Suite del scraper **OK**.

---

## 5. Pendiente

1. **Revisar la corrección v2 de Codex** (confirmadas 560 → ~1000, 75/75 tests, invariantes).
2. **Re-scrapear los ~23 forms anunciados-no-descargados** con la variante por CUCE:
   10×FORM 500, 5×170, 4×200, 2×220, 2×100. FORM 500 faltantes:
   - 2022–2024 (reparables, el 500 existe en el portal): `22-0660-10-1199042-1-2`,
     `23-0660-10-1309108-1-1`, `23-0660-11-1333011-1-1`, `23-0660-11-1333799-1-1`,
     `23-0660-11-1390009-1-1`, `24-0660-11-1456215-1-1`.
   - 2026 (probable: no recibido aún): `26-0660-11-1647655-1-1`, `-1651293-1-1`,
     `-1655391-1-1`, `-1655431-1-1`.
3. **Control de completitud en el scraper**: reconciliar anunciado vs capturado, reintentar
   y fallar fuerte (prompt de Codex redactado; aún no implementado).
4. **Cobertura DBC** (etapa 3): segmentar los 54 CUCE con DBC sin bloques; cargar texto DBC
   ya extraído en disco.
5. OCR de escaneados.

### Hallazgo 2026-11-10 — formas repetidas (FORM 170 múltiple) y FORM 180

Sobre los 194 manifiestos (`announced.forms` vs `documents`):
- **4 procesos anuncian ≥2 FORM 170 y solo se capturó 1**: `22-0660-10-1199042-1-2`
  (2), `23-0660-10-1309108-1-1` (3), `23-0660-11-1390009-1-1` (2),
  `24-0660-11-1456215-1-1` (2). Causa (confirmada en código): `process()` y
  `open_form()` resolvían el token **por etiqueta** y abortaban si había más de una
  (`len(matches)!=1`). Teoría del usuario sobre el *por qué* hay varias: un proponente
  se preadjudica, lo descalifican y el siguiente FORM 170 adjudica al siguiente.
  **Corregido** por índice de ocurrencia (`nth_link`): se captura la N-ésima forma de
  cada etiqueta por ORDEN sobre la fila refrescada. El mismo bug sub-capturaba
  **FORM 250** (procesos 2026 anuncian 2–3, se guardó 1) y FORM 180/190.
  → Hay que **re-scrapear** esos 4 procesos para traer el/los 170 faltantes.
- **4 procesos tienen FORM 180 (y 0 ó mixto 170)**: `23-0660-11-1333011-1-1` (180×2),
  `23-0660-11-1333433-1-1` (180×1), `23-0660-11-1333799-1-1` (180×3),
  `24-0660-11-1456215-1-1` (180×1 + 170×2). Se dejan **sin 170** por ahora (no se sabe
  qué documenta el 180). Igual les faltan 500/220 → entran al re-scrapeo.

---

## 6. Comandos útiles

Doble clic (lanzador, igual que los demás `.command`):
`Correr Sicoes Local (por CUCE).command` — pega uno o más por nº de convocatoria,
guarda en la misma carpeta que `Correr Sicoes Local.command`.

```sh
# Listar lo que se buscaría, sin conectar (por nº de convocatoria)
scraper/venv/bin/python -B -m scraper.historico_local.por_cuce 1199042-1-2 --check

# Capturar varias convocatorias (sin entidad ni año: busca por el 4º campo del CUCE)
scraper/venv/bin/python -B -m scraper.historico_local.por_cuce 1199042-1-2 1333011 1456215

# Fichas de adquisición (asociación v2)
scraper/venv/bin/python -B -m procesamiento.historico.acquisitions --output <salida_nueva> --association-rules v2

# Tests
scraper/venv/bin/python -B -m unittest discover -s procesamiento/historico/tests -p "test_*.py"
scraper/venv/bin/python -B -m unittest discover -s scraper/historico_local/tests -p "test_*.py"
```

---

## 7. Bitácora de decisiones y errores

- **2026-11-10 — ERROR (corregido): llave de asociación.** Se basó el diagnóstico en el
  informe v1 (63 confirmadas) sin ver que **ya existía una corrida v2 con 560 confirmadas**
  (`adquisiciones_v2_20261109_01`). El prompt resultante puso `nro_item` como llave primaria
  y **regresó** el v2 de 560 → 245, rompiendo 3 tests curados. Lección: **consultar esta
  bitácora y los `resumen.json` existentes antes de proponer un rediseño**; la descripción,
  no el nro_item, es la llave 1:1.
- **2026-11-10 — Verificación de completitud.** Se cruza `announced.forms` del manifiesto vs
  documentos con versión válida. Reveló los ~23 forms del §5.
