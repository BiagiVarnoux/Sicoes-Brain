# 05 — Entrega del bloque funcional: análisis de demanda por producto

_Fecha: 2026-11-07. Commit base HEAD: `1240e70`. Todo lo cuantificado fue re-ejecutado/medido; nada escrito en producción._

Objetivo del bloque: una **primera versión funcional del análisis histórico de demanda por producto/familia**, implementada, integrada y probada — no otra auditoría. Cuatro frentes.

---

## 1. Qué se implementó realmente

| Frente | Entregable | Estado | Evidencia |
|---|---|---|---|
| 3 | Agregación económica anti doble-conteo | **Implementado + probado** | `monitor/canonicalizacion/demanda/agregador_demanda.py`, `test_integridad.py` (verde) |
| 3 | Prueba reproducible del bug FORM100/110 | **Implementado** (bug ya corregido en código) | `test_integridad.py` bloque A sobre dumps reales |
| 2 | Motor de consumibles de impresión por código | **Implementado + autoprobado** | `monitor/canonicalizacion/impresion/extractor_impresion.py` |
| 2 | Canónicos provisionales versionados | **Implementado** | `monitor/canonicalizacion/provisional/generar_provisionales.py` → `app/src/data/canonicos_provisionales.json` |
| 1 | Etiquetado incremental robusto + cobertura 100% | **Implementado + ejecutado** | `monitor/canonicalizacion/taxonomia/etiquetar_incremental.py` |
| 1 | Consolidación determinista + estado | **Implementado** | `monitor/canonicalizacion/taxonomia/consolidar_determinista.py` |
| 4 | Vista de demanda en el dashboard (demo solo lectura) | **Integrado + build OK + render OK** | `app/src/app/historico/demanda-demo/` + `app/src/lib/demanda.ts` |

---

## 2. Taxonomía (Frente 1) — cifras verificadas

- Corpus vivo: **5.067** descripciones `cuerpo` distintas (**4.423** normalizadas).
- Etiquetas válidas (texto ligado al id): **4.896**; únicas **4.423**; duplicadas colapsadas **473**.
- **Cobertura del corpus: 4.423/4.423 = 100 %** (antes 87 %; se etiquetaron 545 pendientes de forma incremental, 0 re-proceso del corpus completo).
- Consolidación **determinista** de categorías: **585 → 572** (mayúsculas/tildes/plurales/mapa curado). La reducción a ~100 requiere el **merge semántico por LLM** (pendiente; no es seguro hacerlo determinista) → ver limitaciones.
- Evidencia: `monitor/canonicalizacion/taxonomia/taxonomia_estado.md`, `taxonomia_consolidada.json`.

El etiquetador incremental es recuperable: id estable = sha1 del texto normalizado; reintenta solo los ids ausentes; checkpoint separado (`taxonomia_pendientes_checkpoint.jsonl`); si Groq agota el cupo diario, guarda y corta sin bloquear.

---

## 3. Cobertura de canonicalización — antes vs después

| | Descripciones únicas con canónico | % de 5.067 | Familias modeladas |
|---|---|---|---|
| **Antes** | ~340 | ~7 % | 8 por atributos; impresión = 0 |
| **Después** | **1.385** | **27 %** | + consumibles de impresión por código |

- Grupos canónicos provisionales: **381** (268 a nivel *producto*, 106 *subfamilia*, 7 *familia*).
- Motor de impresión: de 1.337 descripciones de impresión, **968 (72 %) con código de consumible** (911 confianza alta, 57 media); equivalencias HP conocidas (78A↔CE278A, etc.) unidas; SKUs distintos (56F4000 vs 56F4H00) preservados separados.

---

## 4. Integridad económica y deduplicación (Frente 3)

Clave de identidad del ítem económico: **`(cuce, nro_item, lote)`** (lote NULL en el 100 % → de hecho `(cuce, nro_item)`).

Prueba `test_integridad.py` — **todas las aserciones pasan**:
- **Bloque A (parser FORM100/110):** sobre 5 dumps HTML reales, el parser por índice fijo (viejo) desalineaba (descripción basura, referencial = total); el parser **por encabezado (actual, commit `21e0f84`) lo corrige**. → El bug que la hoja de ruta `04_PENDIENTES` marcaba como "crítico pendiente" (y el índice de `MEMORY.md`) ya estaba resuelto en el código del scraper; esta prueba lo confirma de forma reproducible. Queda el pendiente operativo de re-scrapear entidades viejas que pudieran tener filas anteriores al fix.
- **Bloque B (anti doble-conteo):**
  - partición exacta: 7.441 filas → **6.945 ítems económicos**, sin pérdida ni duplicado;
  - Σ referencial cruda **Bs 146.154.817** ≥ colapsada **Bs 135.937.517** → **doble conteo eliminado Bs 10.217.300 (7,5 %)**;
  - fases independientes: ref **Bs 135,9M** · adj **Bs 124,7M** · ejec **Bs 106,6M** (nunca se suman entre sí);
  - 462 ítems con requerido+adjudicado toman el referencial del **requerido** (autoritativo), con `ref_adjudicado` guardado para auditoría (difiere en 365 casos).

---

## 5. Demostración reproducible de demanda (Frente 4)

Vista `/historico/demanda-demo` (y detalle `/historico/demanda-demo/[clave]`):
- familias y productos canónicos; entidades que los demandan; cantidades; **precios por fase** (referencial/adjudicado/ejecutado); evolución por año; procesos de origen (link al proceso); estado de **confianza/provisionalidad** (confirmado / provisional alta/media/baja).
- banner de control anti doble-conteo (crudo vs colapsado) con los Bs 10,2M / 7,5 %.
- **Verificado:** `npm run build` OK; `next start` + HTTP 200; render con datos reales (p.ej. "Toner HP CE278A", "Toner LEXMARK 56F4000") y los totales exactos del backend.

---

## 6. Integrado vs demo aislada

- **Integrado al dashboard:** nueva pestaña "Demanda (demo)" en `HistTabs`; dos rutas nuevas; capa `demanda.ts` que reusa el cliente Supabase existente. Build de producción incluye las rutas.
- **Provisional / fuera de producción:** las agrupaciones vienen de `app/src/data/canonicos_provisionales.json` (generado fuera de la BD). **No** se escribió `hist_productos_canonicos` ni `hist_items.producto_canonico_id`. La UI marca cada grupo como *provisional* vs *confirmado*.

---

## 7. Limitaciones y riesgos pendientes

- **Precisión real NO medida:** la coincidencia por código es de alta calidad pero no se validó con muestra independiente a 3 niveles. Un código mal extraído produce una fusión incorrecta. 72 % de impresión tiene código; el 28 % restante queda a nivel subfamilia (provisional, no intercambiable).
- **Consolidación de taxonomía a ~100 categorías:** requiere el merge semántico LLM (el determinista solo llega a 572). Pendiente.
- **`especificaciones` del DBC siguen vacías** en la BD (0/7.441): el motor es description-only.
- **Correspondencia incierta:** 389 ítems económicos marcados (33 por fuente duplicada, 365 por referencial discrepante req↔adj). Se exponen con ⚠, no se ocultan.
- **Persistencia:** nada se escribió en producción; activar canónicos confirmados requiere la migración Etapa 4 + event log + aprobación.
- **Datos limitados a 7 entidades / 965 procesos** (lo scrapeado hasta hoy).

---

## 8. Reproducir (desde `monitor/`)

```bash
# Frente 3 — agregación económica + prueba de integridad
../scraper/venv/bin/python canonicalizacion/demanda/agregador_demanda.py
../scraper/venv/bin/python canonicalizacion/demanda/test_integridad.py

# Frente 2 — motor de impresión + canónicos provisionales versionados
../scraper/venv/bin/python canonicalizacion/impresion/extractor_impresion.py
../scraper/venv/bin/python canonicalizacion/provisional/generar_provisionales.py

# Frente 1 — consolidación determinista + etiquetado incremental (solo pendientes)
../scraper/venv/bin/python canonicalizacion/taxonomia/consolidar_determinista.py
../scraper/venv/bin/python canonicalizacion/taxonomia/etiquetar_incremental.py        # reanudable; --probe para 1 lote

# Frente 4 — dashboard (desde app/)
cd ../app && npm run build        # verifica tipos + rutas (la memoria pide tsc/deploy, no preview)
```

Artefactos versionados: `monitor/canonicalizacion/{demanda,impresion,provisional,taxonomia}/`, `app/src/data/canonicos_provisionales.json`, `app/src/lib/demanda.ts`, `app/src/app/historico/demanda-demo/`.
