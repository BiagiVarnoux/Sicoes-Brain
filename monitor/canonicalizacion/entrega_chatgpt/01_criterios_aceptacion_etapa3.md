# Criterios de aceptación — Etapa 3 (verificador por niveles)

> ## ✅ CIERRE FORMAL (aprobado por el usuario, 2026-11-07)
> La **Etapa 3 queda formalmente cerrada como desarrollo experimental reproducible, con limitaciones
> conocidas.** Esto **NO** significa que el verificador haya demostrado 98% de precisión, y **NO** autoriza
> fusiones automáticas (que siguen bloqueadas). La versión congelada se conserva como candidata de referencia.
>
> **Precisiones del usuario incorporadas:**
> 1. Las 67 descripciones, 9 componentes y 5 variantes de papel_bond son **unidades de análisis distintas**;
>    **no** representan automáticamente 67, 9 o 5 observaciones estadísticamente independientes. El **tamaño
>    efectivo** deberá determinarse con un diseño de validación apropiado (no por recuento directo de ninguna
>    de esas unidades).
> 2. La fusión debe definirse como una **operación persistente pero reversible**, con **versionado y registro
>    de auditoría**. (Se traslada al diseño de la Etapa 4: `diseno_etapa4.md`.)


**Estado:** documento de decisión. NO modifica código, reglas ni muestras. El verificador queda
**congelado como versión experimental candidata a cierre** (último commit de la fase de corrección;
baselines en `congelado/`). Este documento define qué debe cumplirse para (a) cerrar formalmente la
Etapa 3 y (b) autorizar fusiones automáticas en la Etapa 4. Lo revisa el usuario antes de decidir.

## Precisiones registradas (de la última revisión)
- **`huella` y `pliegues` de llanta son discriminantes SOLO-CONTRADICCIÓN** (comportamiento real del código,
  verificado): su **ausencia NO degrada** el veredicto — si los atributos de identidad modelados
  (medida, tipo_constr, cámara) coinciden, el par puede ser **ESP=SI aunque huella/pliegues falten**
  (confirmado: existe 1 llanta ESP=SI con huella ausente en ambos lados). Solo una **contradicción técnica
  confirmada** baja a NO, y una **diferencia ambigua** baja SI→INSUF. (Corrige la afirmación errónea de una
  versión previa de este documento que decía que la ausencia "siempre produce INSUF".)
- **La ausencia de huella/pliegues no acredita igualdad:** no añade confirmación; simplemente no bloquea un
  SI ya ganado por los demás atributos de identidad. No se infiere igualdad a partir de la ausencia.
- **Los "0 fallos de extracción" valen solo para los atributos primarios auditados** (`formato_continuo`,
  `medida`) y los casos examinados. **No validan todo el extractor.** La cobertura del extractor en los
  demás atributos (gramaje, color, generación, interfaz, etc.) no está medida y es una limitación conocida.
- **La precisión del verificador POR PARES no garantiza la precisión de los CLÚSTERES.** La agrupación
  (Etapa 4) requerirá su propia validación a nivel de clúster y controles de transitividad; un clúster con
  una sola descripción intrusa es un error aunque casi todos sus pares internos sean correctos.
- No se amplía todavía el soporte de formatos no modelados (continuo 9½×5½, "3×90", moto `2.75/18`).

---

## 1. Criterios para cerrar formalmente la etapa experimental

El cierre de la Etapa 3 es **documental y de reproducibilidad**, no implica autorizar fusiones. Se cierra
cuando se cumplan TODOS:

1. **Reglas documentadas.** Cada veredicto (FAMILIA_AMPLIA / SUBFAMILIA / PRODUCTO_ESPECIFICO) tiene su
   definición, los atributos que lo deciden por categoría (SEGMENTO vs IDENT), y la jerarquía lógica
   (ESP=SI ⟹ SUB=SI ⟹ FAM=SI). → cubierto por `auditoria_final.md` + docstrings del verificador.
2. **Base reproducible y congelada.** Versión candidata y baselines previas en `congelado/`; corrida
   determinista sobre los 9.828 pares reproducible con un comando. → cubierto.
3. **Errores conocidos controlados.** El único defecto de correctitud detectado (llantas huella/pliegues)
   está corregido y con prueba antes/después. → cubierto por `correccion_llantas.md`.
4. **Limitaciones explícitas.** Documentadas: FAM hardcode=SI (no discrimina familia); cobertura del
   extractor sin medir salvo primarios auditados; formatos no modelados; muestras de validación solo papel.
   → sección 5.
5. **Pruebas de regresión estables.** v2 22/22/22, muestra 53 53/49/51, extractor 11/11, todas re-ejecutables.
   → cubierto.

**El cierre NO requiere alcanzar el 98% de precisión.** Ese umbral es condición para la Etapa 4 (fusiones),
no para cerrar la etapa experimental. Cerrar = "el verificador está documentado, es reproducible y sus
límites son explícitos", que es distinto de "es suficientemente confiable para fusionar sin humano".

## 2. Condiciones necesarias para autorizar fusiones automáticas

La fusión automática es la acción irreversible (unir descripciones bajo un `producto_canonico_id`). Se
autoriza **por categoría**, no global, y solo cuando:

1. **Veredicto = ESP=SI.** Nunca se fusiona sobre INSUF ni NO. INSUF = candidato → cola de revisión humana
   o enriquecimiento por DBC, no fusión.
2. **Precisión de fusión validada ≥ 98%** (ver objetivo en §4) en esa categoría, con muestra independiente
   y 0 o pocos errores dentro del límite estadístico.
3. **Error de fusión indebida acotado.** Un "error de fusión" = dos descripciones comercialmente distintas
   unidas (determinante para un DBC). Es el error caro; su cota es más estricta que la de no-fusión.
4. **Transitividad controlada** (Etapa 4): que A≡B y B≡C no implique fusionar A con C sin que A≡C se haya
   verificado directamente. Sin esta prevención no se autoriza fusión automática.
5. **Reversibilidad operativa.** La asignación de `producto_canonico_id` debe poder deshacerse (versión /
   log), porque la validación es muestral y habrá errores residuales.
6. **Categorías sin confirmaciones (hoy RAM y almacenamiento, 0 ESP=SI) NO se auto-fusionan**: sin
   confirmaciones no hay precisión que medir. Quedan como candidatos a revisión hasta que existan ESP=SI
   validados.

Donde no se cumpla el 98%, la categoría opera en **modo asistido**: el verificador propone, un humano
confirma. Equivalencia (veredicto) y autorización a fusionar quedan separadas, como se acordó.

## 3. Plan de validación independiente por categoría

Objetivo: medir la precisión **de esta versión congelada**, no reutilizar muestras que ya la ajustaron
(las 53 + 22 pasan a ser solo regresión). Para cada categoría con volumen suficiente:

- **Estratos por veredicto**: positivos (ESP=SI), negativos difíciles (ESP=NO que comparten medida/familia
  pero difieren en un discriminante: p. ej. llanta misma medida distinta huella; RAM misma capacidad
  distinta generación; bond mismo tamaño distinto gramaje), e insuficientes (ESP=INSUF por ausencia).
- **Negativos cross-familia** (precaución #4): pares de distinta categoría que el sistema debería separar,
  para medir FAMILIA_AMPLIA de verdad (hoy es hardcode SI → no discrimina). Incluir errores de
  categorización deliberados.
- **Etiquetado ciego**: el revisor no ve el veredicto del verificador al etiquetar.
- **Trazabilidad**: cada par con su descripción, atributos extraídos y justificación del humano.
- **Prioridad de categorías**: papel_bond (474 ESP=SI, mayor volumen) primero; luego continuo (76),
  óptico (22), sobre (15), impreso (6). RAM/almacenamiento/llanta tienen muy pocos o cero ESP=SI → validar
  sobre todo sus NO/INSUF y conseguir positivos nuevos antes de hablar de fusión.

Tamaño por estrato: ver §4. No se generan muestras todavía (instrucción vigente); esto define el plan.

## 4. Métricas — y el objetivo del 98%

**Distinguir pares vs descripciones únicas** (como advirtió la revisión): un error de extracción o una
descripción incompleta contamina muchos pares. Por eso toda métrica se reporta en dos niveles.

- **Precisión de fusión (pairwise):** de los pares ESP=SI, % realmente equivalentes. Es la métrica del 98%.
- **Precisión de clúster (a nivel descripción):** tras agrupar, % de clústeres sin ninguna descripción
  intrusa. Más estricta y más cercana al daño real (un clúster malo arruina todo el producto canónico).
- **Cobertura / recall de agrupación:** % de descripciones verdaderamente equivalentes que terminan juntas.
  Se reporta aparte: el objetivo NO es maximizar coincidencias (INSUF de más es aceptable; fusión de más no).
- **Errores de fusión indebida:** conteo y tasa, en pares y en descripciones. Métrica de seguridad.
- Reporte por categoría y agregado, con los denominadores (nº pares y nº descripciones únicas).

### Dependencia entre pares (limitación estadística, NO resuelta aún)
Los pares del corpus **no son observaciones independientes**: comparten descripciones y sus errores están
**correlacionados**. La auditoría de conteos (`auditoria_conteos_bond.md`) lo demuestra en papel_bond: los
474 pares ESP=SI se reducen a **67 descripciones únicas, 9 clústeres y 5 variantes**, con 231 pares dentro de
un solo clúster de 22 descripciones. Un acierto o error sobre "oficio 75g blanco" se repite en decenas de
pares. **Por tanto, 150 pares cualesquiera NO equivalen a 150 observaciones independientes**, y el cálculo
binomial de abajo es un límite optimista que solo vale sobre unidades independientes.

**Propuesta de validación que controla la dependencia** (sin cambiar el umbral del 98%):
- **Unidad de muestreo = descripción única / variante / clúster, no el par.** Contar éxitos por clúster
  (¿el clúster es homogéneo?) y por variante, no por par.
- **Muestreo estratificado por variante** (tamaño × gramaje × color × presentación / empaque) para no
  sobre-representar la variante dominante; cubrir las variantes raras aunque aporten pocos pares.
- **Cobertura de atributos relevantes por categoría**: registrar qué fracción de las descripciones declara
  cada atributo de identidad (p. ej. % de bond que trae gramaje) — un n alto con baja cobertura de gramaje
  no respalda identidad.
- **n efectivo**, no n de pares: aplicar el cálculo binomial sobre el número de unidades independientes
  (clústeres/descripciones), o usar un intervalo que corrija el efecto de diseño por correlación intra-clúster.
- El umbral del **98% se mantiene**; lo que cambia es que el n debe medirse en unidades independientes.

### Objetivo provisional: precisión de fusión ≥ 98%

Marco estadístico (proporción binomial, una cola, para **afirmar un piso** de precisión, **sobre unidades
independientes** — ver la limitación de dependencia arriba):

- **Con 0 errores observados** (regla de tres): el límite superior 95% de la tasa de error es ≈ 3/n.
  Para que ese límite sea ≤ 2% (precisión ≥ 98%): **n ≈ 150 pares ESP=SI por categoría, 0 errores → 95%
  de confianza en que la precisión ≥ 98%.**
  - A **99% de confianza** (regla ≈ 4.6/n ≤ 0.02): **n ≈ 230**, 0 errores.
- **Si se tolera 1 error** en la muestra, el n sube: para mantener el límite 95% ≤ 2% hace falta **n ≈ 240**
  (límite superior de Clopper–Pearson con 1/240 ≈ 2%). Con 2 errores, n ≈ 330. Regla práctica: por cada
  error admitido, sumar ~90–100 pares.
- **Estimación puntual (no piso)** con intervalo de Wilson a ±2% y 95%, cerca de p=0.98: **n ≈ 190**.

**Recomendación:** fijar **n = 150 unidades independientes por categoría con criterio de 0 errores** como
condición mínima de fusión automática a 95% de confianza; 230 para 99%. "Unidad independiente" = descripción
única / clúster / variante, **no par**.

Universo actual de referencia (post-corrección, 9.828 pares / 5.067 descripciones únicas). La columna que
importa es el **volumen efectivo independiente**, no el nº de pares — ver `auditoria_conteos_bond.md`:

| categoría | ESP=SI (pares) | desc. únicas / clústeres / variantes | ¿n independiente ≈150? |
|---|---|---|---|
| papel_bond | 474 | **67 desc / 9 clústeres / 5 variantes** | **NO** (474 pares ≠ 474 obs.) |
| papel_continuo | 76 | pendiente de auditar (menor aún) | no |
| optico | 22 | — | no |
| sobre_manila | 15 | — | no |
| papel_impreso | 6 | — | no |
| llanta | 2 | — | no |
| ram / almacenamiento | 0 | sin confirmaciones | no aplica |

**Corrección respecto de la versión previa de este documento:** afirmé que papel_bond "alcanza n=150".
La auditoría de conteos lo desmiente: su volumen efectivo son ~5 variantes / 9 clústeres / 67 descripciones.
**Ninguna categoría tiene hoy volumen independiente para una validación del 98% defendible.** Para lograrlo
hacen falta **más descripciones distintas** (datos históricos nuevos con más diversidad de
tamaño/gramaje/color/presentación), no más pares del mismo puñado de variantes. En consecuencia, **toda
categoría opera por ahora en modo asistido**; la fusión automática queda bloqueada hasta reunir ese volumen.

## 5. Riesgos residuales y limitaciones conocidas

1. **FAMILIA_AMPLIA es hardcode=SI** → no discrimina familia; la separación la hace el blocker. Sin
   negativos cross-familia, FAM no está validado (precaución #4).
2. **Cobertura del extractor sin medir** salvo los primarios auditados. Atributos secundarios (gramaje,
   color, generación, interfaz, frecuencia) podrían tener fallos no cuantificados.
3. **Formatos no modelados** (continuo 9½×5½, "3×90", moto en pulgadas) → quedan INSUF; brecha de cobertura
   conocida, no error.
4. **Validación previa solo de papel** (53+22) y ahora degradada a regresión; **llanta, ram,
   almacenamiento, óptico y sobre no tienen validación independiente de esta versión.**
5. **INSUF menos conservador que un humano** en la frontera SI/INSUF (histórico de las discrepancias), pero
   0 confusiones SI↔NO. El riesgo vive en SI→fusión, no en separaciones falsas.
6. **Mecanismo de copia (químico/carbónico)** tratado SOFT→INSUF por terminología imprecisa de pliegos:
   preserva la diferencia sin afirmarla; puede dejar como candidatos pares que un experto resolvería.
7. **Ausencia multiplicada**: pocas descripciones incompletas generan muchos pares INSUF (4 continuo → 239
   pares). No es un fallo, pero sesga la lectura por par.

## 6. Condiciones de entrada a la Etapa 4 (agrupación + anti-transitividad)

Antes de escribir una sola asignación de `producto_canonico_id`:

1. Etapa 3 **cerrada** (§1) y criterios de este documento **aprobados por el usuario**.
2. Plan de validación (§3) **ejecutado** al menos en papel_bond, con precisión de fusión medida ≥ objetivo.
3. **Diseño de agrupación que NO fusione por transitividad**: unir solo pares con ESP=SI verificado
   directamente; A≡B, B≡C ⇒ A≡C solo si A≡C también da ESP=SI. Definir qué hacer con componentes conexos
   donde algún par interno es INSUF/NO (no colapsar todo el componente).
4. **Reversibilidad**: esquema con `parent_id`/`nivel`/`atributos jsonb` y log de asignaciones, para deshacer.
5. **Modo asistido por defecto** en toda categoría que no haya alcanzado el 98% validado.
6. Separación mantenida entre **veredicto de equivalencia** y **autorización a fusionar**, y entre fusión y
   la posterior **agregación de demanda** (que tendrá su propio control anti-doble-conteo).

---

### Resumen para decidir el cierre
- Cerrar Etapa 3 **como desarrollo experimental reproducible, con limitaciones conocidas, es viable hoy**:
  reglas documentadas, baseline congelada, regresión estable, límites explícitos.
- Autorizar fusiones automáticas **no es viable hoy en ninguna categoría**: ni papel_bond tiene volumen
  independiente suficiente (≈5 variantes / 9 clústeres / 67 descripciones, no 474 observaciones). Todas las
  categorías → **modo asistido** hasta reunir más descripciones distintas (datos históricos nuevos).
- La fusión automática **seguirá bloqueada** hasta completar la validación por unidades independientes.
- Siguiente paso propuesto (tras aprobar estos criterios): decidir cómo conseguir diversidad de descripciones
  por categoría. Sin tocar verificador/extractor ni generar muestras hasta esa decisión.
