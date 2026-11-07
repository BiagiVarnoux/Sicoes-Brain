# Revisión de precauciones (análisis y propuestas, SIN implementar) — 2026-11-07

Línea base CONGELADA (commit 829c108). No se reajusta el verificador ni se usan los 22 pares nuevos
hasta completar su evaluación (precaución #5). Esto es diagnóstico + propuestas; las correcciones se
deciden DESPUÉS de etiquetar la muestra nueva.

## #1 — ESP=SI no debe cambiar de significado silenciosamente. Identidad confirmada ≠ candidato
**Problema:** hoy ESP=SI significa "todos los atributos MODELADOS coinciden", lo que puede ocultar
requisitos no modelados (ISO, alcalino, norma) → se lee como identidad probada sin serlo.

**Propuesta (sin romper los 3 niveles, sin agregar un 4º estado):** redefinir el umbral de ESP usando
el vocabulario existente {SI, NO, INSUF}, haciendo que **INSUF sea el bucket de "candidato a identidad"**:
- **ESP=SI = identidad CONFIRMADA**: (i) todos los atributos de IDENTIDAD de la categoría están
  presentes en AMBOS lados y son iguales, y (ii) no hay un requisito/calificador en un lado ausente en
  el otro (detector de "residuo no explicado": `ISO\s?\d+`, "norma", "certificaci", "alcalino/alkalino",
  material/estándar específico).
- **ESP=INSUF = CANDIDATO a identidad**: coincide en lo modelado pero falta ≥1 atributo de identidad, o
  hay un residuo no explicado en un lado. (Aquí caen los 7 casos actuales: V018 ISO, V040/V047 alcalino/ISO,
  V030 juegos-vs-hojas, V004/V005/V023 por lo del punto #2.)
- **ESP=NO = diferencia confirmada** (sin cambios).
Esto NO agrega un nivel: "candidato" = INSUF, que ya significa "no se puede concluir identidad". La
agrupación final tratará ESP=SI como fusionable y ESP=INSUF como "requiere confirmación (humano/DBC)".
Requiere definir por categoría el conjunto mínimo de *atributos de identidad* (curaduría del usuario).

## #2 — químico / desglose / carbónico NO son sinónimos: separar mecanismo, físico y demanda
**Corrijo mi over-corrección (v2):** colapsé los cuatro términos a "autocopiativo". Es demasiado grueso.
Lo correcto, separando dimensiones:
- **Mecanismo de copia:** "químico" = "autocopiativo" = papel NCR (capas químicas CF/CB, sin carbón) →
  son el MISMO mecanismo. "carbónico" = papel con carbón intercalado → mecanismo DISTINTO (y más antiguo).
- **Característica física/presentación:** "con desglose" = copias separables/colacionadas → ORTOGONAL al
  mecanismo (un formulario puede ser "químico CON desglose"). NO es un tipo de papel.
- **Familia de demanda:** químico y carbónico sirven la misma necesidad (formulario continuo multicopia)
  → MISMA subfamilia; el mecanismo es un discriminante de PRODUCTO ESPECÍFICO, no de subfamilia.

**Propuesta:** extraer DOS atributos separados — `mecanismo_copia` ∈ {ncr (químico/autocopiativo),
carbon (carbónico)} y `desglose` ∈ {sí} — en vez del `tipo` único actual que mezcla ambas cosas (artefacto
que causaba el falso ESP=NO de V004/V005). Reglas: desglose NO discrimina mecanismo; ncr vs carbon es un
discriminante de específico SOFT (la terminología en los pliegos es imprecisa/OCR) → ESP=INSUF, no NO.
Mientras tanto, mi colapso actual a "autocopiativo" queda marcado como provisional a revertir por esta
versión más fina. (NO implementado aún; decisión tras etiquetar.)

## #3 — Auditoría de la caída de SUBFAMILIA=INSUF: la regla de secundarios SÍ arriesga falsos positivos
Efecto AISLADO de la regla de secundarios (usar_sec True vs False, mismos atributos enriquecidos; detalle
y ejemplos en `auditoria_precauciones.md`):
- **1.035 pares pasan de SUBFAMILIA INSUF → SI** por la regla (el primario coincide y el secundario
  —gramaje/aplicación— no degrada por ausencia).
- **901 de esos 1.035 tienen el secundario declarado en UN lado y ausente en el otro** → se ASUME que el
  lado omiso coincide. **Eso es un riesgo de falso positivo real** (ej.: bond oficio 75g vs bond oficio sin
  gramaje → se agrupan; si el omiso fuera 56g, es fusión indebida de subfamilia).
- Solo 134 tienen el secundario ausente en AMBOS lados (riesgo bajo). 0 contradicciones (INSUF→NO).

**Conclusión:** la regla "ausencia no degrada → SI" es demasiado permisiva. **Propuesta:** que una AUSENCIA
de secundario mantenga SUBFAMILIA=INSUF (candidato), y solo una CONTRADICCIÓN la baje a NO; el SI de
subfamilia se reserva para cuando el secundario está presente e igual (o la categoría no tiene secundario).
Esto conecta con #1 (INSUF = candidato) y elimina los 901 falsos positivos potenciales. (NO implementado aún.)

## #4 — FAMILIA_AMPLIA 53/53 NO es discriminación validada; faltan negativos cross-familia
- El blocker SOLO empareja dentro de la misma categoría; el verificador devuelve **FAM=SI por hardcode**.
  Nunca se le presentan pares de distinta familia → **53/53 es tautológico**, no mide discriminación.
- La separación de familias ocurre en el BLOCKER (regla dura de tipo). Prueba: 28/28 pares cross-categoría
  quedan separados por `categoria()` (ver auditoría). Pero eso valida el BLOCKER, no el verificador.
- **Propuestas:** (a) que el verificador CALCULE FAMILIA_AMPLIA = SI si misma categoría, NO si distinta
  (en vez de hardcode), para que sea un juicio real y no una asunción; (b) incluir en la validación un
  conjunto de NEGATIVOS cross-familia etiquetados (deberían dar FAM=NO) para medir discriminación de verdad.
  (NO implementado aún.)

## #5 — Línea base conservada
Reglas y resultados actuales (commit 829c108) quedan como línea base. No se reajusta el verificador con los
22 pares hasta completar su evaluación. Las propuestas #1–#4 se implementarán solo tras etiquetar la muestra
nueva y decidir en conjunto. No se avanza a agrupación definitiva ni agregación de demanda.
