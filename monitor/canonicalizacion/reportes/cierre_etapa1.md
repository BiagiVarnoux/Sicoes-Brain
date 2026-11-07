# Cierre PROVISIONAL de la Etapa 1 (extractor de atributos) — 2026-11-06

Opción A: corregidos los 4 defectos de correctitud detectados en la muestra v4 (55, propuesta asistida de
ChatGPT, NO verdad certificada), con regresión limpia. Producción intacta. Versión congelada:
`congelado/extractor_atributos_etapa1_cerrada.py`.

## Correcciones aplicadas (por raíz, sin excepciones por SKU; con las 2 precauciones de ChatGPT)
1. **E049 case/rack**: se excluyen SOLO cuando son el producto LÍDER (`^(case|rack)` al inicio de la
   cabeza). Si "rack" aparece como mención ("disco … para rack/servidor"), el disco sigue siendo el
   producto. NO es regla global.
2. **E014 tipo_medio óptico**: se asigna cd/dvd SOLO con token explícito; "disco compacto" por sí solo
   queda INDETERMINADO (a faltantes) y se conserva la capacidad. NO se deriva el medio por la capacidad;
   si token y capacidad se contradicen (cd↔4.7GB), indeterminado.
3. **E043 gramaje rango**: "75-80 g/m²" se conserva como rango normalizado `"75-80"` (límites min/max),
   sin colapsar a exacto.
4. **E034/E050 vías papel continuo**: regex de `partes` corregida (se quitó el `\b` que fallaba en
   "…x4x5.5"); toma una sola cifra tras "11x", así "5.5" nunca se confunde con la vía.

## Regresión — impacto AISLADO de las 4 correcciones (metodología correcta)
Salida del extractor ACTUAL vs la MISMA versión con solo esas 4 funciones revertidas a su estado
pre-cierre, sobre TODO el corpus (**5.067 descripciones ÚNICAS**, NO los ~7.441 registros hist_items).
Esto aísla el efecto de las correcciones (no mezcla mejoras de rondas previas). Script: `baseline_diff.py`.

| corrección | filas afectadas | naturaleza |
|---|---|---|
| E049 case/rack | 1 | el gabinete real → fuera de alcance; 0 pérdidas de almacenamiento |
| E014 tipo_medio | 7 | "disco compacto" → indeterminado conservando capacidad |
| E043 gramaje rango | 5 | "75-80" → rango (antes 80 exacto inventado) |
| E034 partes | 8 | solo GANANCIAS: "…x4x5.5" ahora extrae partes=4 |
| **total** | **21 / 5.067** | **todas intencionales; 0 extracciones previamente correctas alteradas** |

Durante la regresión se detectó y corrigió un error propio (1er fix de `partes` rechazaba la vía seguida
de puntuación "11 x 3."). Ya corregido.

### Pruebas (script `regresion_extractor.py`)
- Test objetivo producto-vs-componente: **11/11**.
- Controles negativos nuevos de las 4 correcciones: **11/11**.

## Omisiones PENDIENTES documentadas (no críticas, no resueltas)
- E044 "PC4 3200": frecuencia sin "MHz"/"frec" no se extrae.
- E001/E022/E050: presentación jerárquica (1500 hojas/caja, 750 juegos, por hoja).
- E003 identidad del membrete; E004 "tamaño memorándum"; E011 "90 NGRS" (ruido OCR).
- "DISCO … PARA SERVIDOR/NVR/DVR …" cae en None por la palabra de equipo (ampliar `es_accesorio_ctx`).
- "FORMULARIO CONTINUO" sin la palabra "papel" (sinónimo no cubierto).

## Límite explícito
Las 4 muestras (54+61+50+55 = 220) NO autorizan a declarar precisión del 100% sobre todo el histórico.
Son propuestas asistidas, no verdad humana certificada. Cierre PROVISIONAL: la Etapa 1 alimenta al blocker
con categoría sólida y atributos sin invenciones conocidas; omisiones de arriba como trabajo pendiente.
