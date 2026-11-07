# Canonicalización por atributos — pipeline (entorno aislado, SOLO LECTURA)

> ⚠️ **PIPELINE EXPERIMENTAL NO VALIDADO.** Sus veredictos NO están validados para agrupación
> automática definitiva y NO se integran al dashboard ni a producción. Se conserva en el repo como
> versión reproducible para comparaciones futuras. No ejecutar contra producción ni migrar datos.


Resolución de entidades para la demanda histórica de productos (SICOES). NO fusiona en producción, NO
migra datos, NO escribe en la BD. Todo opera sobre **descripciones únicas** (~5.067), no sobre los
registros `hist_items` (~7.441). Las cantidades/precios/adjudicaciones autoritativos vienen de los campos
FORM de `hist_items`, no del texto; la agregación de demanda (anti doble-conteo) es una etapa posterior.

## Modelo de 3 niveles (diseño v2 aprobado)
- **FAMILIA_AMPLIA** = el tipo del producto (equivalencia comercial amplia; demanda total).
- **SUBFAMILIA** = tipo + atributos de segmento por valor normalizado EXACTO (misma familia de demanda).
- **PRODUCTO_ESPECIFICO** = + atributos de intercambiabilidad (identidad exacta).
BLOQUEO (generación de candidatos, grueso) ≠ NIVEL (lo asigna el verificador). Tres conceptos SEPARADOS.

## Etapas
1. **`extractor_atributos.py`** (Etapa 1, CERRADA provisional) — extrae y normaliza atributos por categoría;
   devuelve {atributos, evidencia, nivel_identificable, faltantes, ambiguos}. Un atributo ausente NO se
   asume igual. Reportes: `reportes/extractor_cobertura.md`. Ver `reportes/cierre_etapa1.md`.
   - `regresion_extractor.py` — estabilidad de salida vs las 4 muestras revisadas (~/Downloads) + test
     objetivo + controles negativos.
   - `baseline_diff.py` — aísla el impacto de las correcciones de cierre sobre todo el corpus.
2. **`blocker_candidatos.py`** (Etapa 2) — generador de candidatos GRUESO por familia amplia (=categoría);
   NUNCA fusiona; descartes AGREGADOS y auditables. Reporte: `reportes/blocker_cobertura.md`.
3. **`verificador_niveles.py`** (Etapa 3) — por cada par candidato emite 3 veredictos SEPARADOS
   {FAMILIA_AMPLIA, SUBFAMILIA, PRODUCTO_ESPECIFICO} ∈ {SI,NO,INSUF}, con jerarquía lógica
   (específico⟹subfamilia⟹amplia) y conservación (falta de evidencia → INSUF). Reporte:
   `reportes/verificador_reporte.md`, veredictos en `reportes/verificador_veredictos_muestra.csv`.

## Estado
- Etapa 1 cerrada provisional; Etapa 2 y 3 construidas y corridas (exploratorias).
- Pendientes: ampliar categorías del extractor (perforadora/archivador/clip/limpieza…); muestra NUEVA
  etiquetada a 3 niveles para medir precisión real del verificador; agrupación final con prevención de
  fusión por transitividad (ajuste #3); agregación de demanda (ajuste #4); migración de esquema
  (parent_id/nivel/atributos jsonb) — todo FUERA de este entorno aislado, sin tocar producción.
- `congelado/` conserva versiones previas (extractor Etapa 1, motor v2 por códigos).

Dependencias: `scraper/venv` (dotenv + urllib). Config en `monitor/.env` (SUPABASE_URL/KEY service-role).
Ejecutar p.ej.: `scraper/venv/bin/python monitor/canonicalizacion/verificador_niveles.py`.
