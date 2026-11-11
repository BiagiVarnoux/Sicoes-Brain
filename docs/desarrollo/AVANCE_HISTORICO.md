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
- **Variante del scraper por CUCE**: `scraper/historico_local/por_cuce.py` (+ tests).
  Acepta uno o más CUCE, forma larga (autodescrita, multi-entidad) o corta con tu
  convención (`1199042` → `-1-1`; `1199042-1-2` explícito). Delega en el `run()` existente,
  no cambia la captura. 13 tests nuevos; suite del scraper **75/75 OK**.

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
5. OCR de escaneados; deuda FORM 170 (17 filas, no bloqueante).

---

## 6. Comandos útiles

Doble clic (lanzador, igual que los demás `.command`):
`Correr Sicoes Local (por CUCE).command` — pega uno o más CUCE, guarda en la
misma carpeta que `Correr Sicoes Local.command`.

```sh
# Verificar/listar procesos puntuales sin conectar
scraper/venv/bin/python -B -m scraper.historico_local.por_cuce 22-0660-10-1199042-1-2 --check

# Capturar varios CUCE (forma corta usa --entidad/--anio)
scraper/venv/bin/python -B -m scraper.historico_local.por_cuce 1199042-1-2 --entidad 0660-10 --anio 2022

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
