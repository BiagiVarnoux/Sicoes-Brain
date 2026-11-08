# 04 — Pendientes y hoja de ruta

_Fecha: 2026-11-07. Commit HEAD: `1240e70`._
_Objetivo: convertir el desarrollo actual en una herramienta comercial funcional (analizar demanda histórica por producto cross-entidad). Plan por **entregables completos**, no microtareas._

---

## 1. Pendientes por categoría

### 1.1 Errores críticos de integridad o identificación
- **Bug parser FORM100/110** (memoria `historico-bug-parser-requerido`): desalineación por índice fijo que mete basura y pierde `precio_referencial` en algunos casos. Afecta la calidad del dato ORIGINAL → impacta todo aguas abajo. **Crítico.**
- **`especificaciones` DBC no persistida** (0 de 7.441 en vivo): el enriquecimiento fino existe en disco pero no llega a la BD. Hoy el motor es "description-only". **Alto.**
- **Anti doble-conteo en agregación de demanda**: `hist_items` repite filas por `fuente` (form110/form220/dbc); si se suman cantidades/montos sin deduplicar, la demanda se infla. Nunca mezclar `precio_referencial`/`precio_adjudicado`/`monto_ejecutado`. **Crítico antes de mostrar números de demanda.**

### 1.2 Componentes incompletos
- **Agrupación canónica persistida (enfoque B)**: diseñada y simulada, pero no implementada fuera del entorno aislado ni conectada a la BD.
- **Log de eventos reversible**: `migracion_etapa4.sql` es BORRADOR, no aplicado.
- **Consolidación del árbol de taxonomía (enfoque C)**: incompleta por cupo Groq; falta `--solo-consolidar`.
- **Recuperación del ~12% de descripciones sin etiquetar** en la pasada C (lotes que devolvieron menos ítems).

### 1.3 Cobertura insuficiente de categorías
- El pipeline curado modela **8 categorías** (~340 de ~5.067 descripciones). Falta modelar, por volumen (ver `02_cobertura_taxonomia.md`):
  1. **Impresión: tóner/cartuchos/tinta/tambores/fusores (~640)** — prioridad #1.
  2. Útiles de escritura (~160), archivo/clips/grapas/folders (~260), mobiliario (~150), repuestos (~115).

### 1.4 Mejoras del extractor y canonicalización
- Cerrar los 3 gaps "no modelado" (medidas compuestas papel continuo, formatos raros) sin romper regresión.
- Definir con el humano la granularidad de las familias difusas (útiles de oficina).

### 1.5 Integración con base de datos
- Aplicar la migración Etapa 4 (parent_id/nivel/atributos jsonb/exemplar + event log).
- Mantener `producto_canonico_id` como caché derivado reconstruible desde el event log.

### 1.6 Integración con dashboard
- El dashboard ya lee `producto_canonico_id`. Falta: vista de producto canónico cross-entidad completa, indicador de "provisional vs confirmado", y filtros por familia/subfamilia cuando existan.

### 1.7 Evaluación y pruebas
- **Muestra de validación independiente** etiquetada a 3 niveles por categoría, con control de dependencia entre pares, para medir **precisión real** (hoy NV).
- Negativos duros cross-familia para FAM.

### 1.8 Rendimiento, mantenimiento y operación
- Versionar las salidas de la pasada C (el corpus crece: 4.336 → 4.966 en días).
- Política de cupo Groq (failover de keys dedicadas; la consolidación no cabe el mismo día que el etiquetado).
- Decidir cadencia de re-corrida de canonicalización tras cada scrapeo.

---

## 2. Priorización (impacto × dificultad × dependencias)

| # | Entregable | Impacto | Dificultad | Depende de |
|---|---|---|---|---|
| P0 | Integridad del dato (fix FORM100/110 + persistir specs DBC) | Alto | Media | — |
| P1 | Agregación de demanda anti doble-conteo (correcta y mostrada) | Alto | Media | P0 |
| P2 | Cobertura categoría impresión (tóner/cartuchos/tinta) en enfoque A y/o B | Alto | Media | mapa C |
| P3 | Medición de precisión real (muestra 3 niveles por categoría) | Alto | Media-alta | P2 |
| P4 | Persistencia reversible (migración Etapa 4 + event log) + wiring | Alto | Media | P3 |
| P5 | Consolidación del árbol de taxonomía (triaje limpio) | Medio | Baja | cupo Groq |

**Racional:** sin P0/P1 el producto muestra números de demanda poco confiables (es la promesa comercial). P2 desbloquea el mayor volumen no cubierto. P3 es la condición para automatizar fusiones (no persistir fusiones a ciegas). P4 hace las fusiones reversibles y auditables. P5 es barato y mejora el triaje.

---

## 3. Plan por entregables completos

### Entregable 1 — "Datos de demanda confiables" (P0 + P1)
Cerrar el bug FORM100/110, persistir `especificaciones` del DBC en `hist_items`, e implementar la agregación de demanda anti doble-conteo (dedup por unidad económica correcta; nunca mezclar los tres precios). **Criterio de aceptación:** un producto muestra demanda (cantidad y monto) reproducible y defendible, con prueba de que no hay doble conteo por `fuente`.

### Entregable 2 — "Cobertura de impresión" (P2)
Modelar la familia impresión (identidad = modelo del consumible: 78A, TN-316, GPR-63…) en el extractor/verificador (enfoque B) y/o como matchers declarativos (enfoque A). **Criterio:** las ~640 descripciones de impresión entran en candidatos y producen clústeres revisables; regresión del extractor intacta.

### Entregable 3 — "Precisión medida" (P3)
Muestra NUEVA etiquetada a mano a 3 niveles por categoría modelada, con diseño que controle la dependencia entre pares. **Criterio:** precisión y cobertura por categoría reportadas con denominador por unidades independientes (descripciones/clústeres), no por pares.

### Entregable 4 — "Fusiones persistidas y reversibles" (P4)
Aplicar `migracion_etapa4.sql`, implementar la agrupación por clique fuera del entorno aislado y escribir vía event log append-only; refrescar `producto_canonico_id` como caché. Wiring final al dashboard (producto canónico cross-entidad, provisional vs confirmado). **Criterio:** toda fusión es reversible (REVOCACION/SUSTITUCION) y auditable; el dashboard muestra demanda por producto canónico.

### Entregable 5 — "Triaje limpio" (P5)
Correr `--solo-consolidar` cuando resetee Groq; versionar la salida. **Criterio:** árbol de ~100 categorías consolidadas como mapa de priorización estable.

---

## 4. Reglas de operación (del usuario, a respetar)
- Trabajo terminado se commitea y pushea directo a `main` (despliega Vercel); nada de PR.
- Nunca borrar la tabla `procesos` (la puebla otro scraper).
- No activar fusión automática hasta tener precisión real medida; mientras tanto, modo asistido (propone, humano confirma) para las familias de más volumen.
- No persistir fusiones ni aplicar migraciones sin aprobación explícita (escriben en producción).
