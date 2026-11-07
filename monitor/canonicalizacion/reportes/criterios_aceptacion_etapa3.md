# Criterios de aceptación — Etapa 3 (verificador por niveles)

**Estado:** documento de decisión. NO modifica código, reglas ni muestras. El verificador queda
**congelado como versión experimental candidata a cierre** (último commit de la fase de corrección;
baselines en `congelado/`). Este documento define qué debe cumplirse para (a) cerrar formalmente la
Etapa 3 y (b) autorizar fusiones automáticas en la Etapa 4. Lo revisa el usuario antes de decidir.

## Precisiones registradas (de la última revisión)
- **La ausencia de `huella` o `pliegues` no acredita igualdad**, aunque no produzca contradicción.
  En el verificador eso ya se cumple: la ausencia deja el veredicto en INSUF (candidato), nunca en SI.
- **Los "0 fallos de extracción" valen solo para los atributos primarios auditados** (`formato_continuo`,
  `medida`) y los casos examinados. **No validan todo el extractor.** La cobertura del extractor en los
  demás atributos (gramaje, color, generación, interfaz, etc.) no está medida y es una limitación conocida.
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

### Objetivo provisional: precisión de fusión ≥ 98%

Marco estadístico (proporción binomial, una cola, para **afirmar un piso** de precisión):

- **Con 0 errores observados** (regla de tres): el límite superior 95% de la tasa de error es ≈ 3/n.
  Para que ese límite sea ≤ 2% (precisión ≥ 98%): **n ≈ 150 pares ESP=SI por categoría, 0 errores → 95%
  de confianza en que la precisión ≥ 98%.**
  - A **99% de confianza** (regla ≈ 4.6/n ≤ 0.02): **n ≈ 230**, 0 errores.
- **Si se tolera 1 error** en la muestra, el n sube: para mantener el límite 95% ≤ 2% hace falta **n ≈ 240**
  (límite superior de Clopper–Pearson con 1/240 ≈ 2%). Con 2 errores, n ≈ 330. Regla práctica: por cada
  error admitido, sumar ~90–100 pares.
- **Estimación puntual (no piso)** con intervalo de Wilson a ±2% y 95%, cerca de p=0.98: **n ≈ 190**.

**Recomendación:** fijar **n = 150 por categoría con criterio de 0 errores** como condición mínima de
fusión automática a 95% de confianza; subir a 230 para 95%→99% o si se quiere margen para 1 error. Para
categorías de bajo volumen de ESP=SI (impreso 6, sobre 15, óptico 22) es imposible reunir 150 positivos:
esas **permanecen en modo asistido** hasta acumular datos históricos nuevos. Medir a nivel de **descripción
única**, no de par, para no inflar n con pares redundantes del mismo par de descripciones.

Universo actual de referencia (post-corrección, 9.828 pares / 5.067 descripciones únicas):

| categoría | ESP=SI (pares) | ¿alcanza n=150? |
|---|---|---|
| papel_bond | 474 | sí |
| papel_continuo | 76 | no (asistido o más datos) |
| optico | 22 | no |
| sobre_manila | 15 | no |
| papel_impreso | 6 | no |
| llanta | 2 | no |
| ram / almacenamiento | 0 | sin confirmaciones: no aplica |

Lectura: **solo papel_bond** tiene hoy volumen para pretender fusión automática validada al 98%; el resto
entra en modo asistido o requiere datos históricos nuevos. Esto es un resultado importante para la decisión.

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
- Cerrar Etapa 3 (documental/reproducible) **es viable hoy**: reglas, baseline, regresión y límites están.
- Autorizar fusiones automáticas **no es viable hoy** salvo, potencialmente, en papel_bond tras validar
  150 positivos independientes con 0 errores. El resto de categorías → modo asistido.
- Siguiente paso propuesto: aprobar estos criterios y, si se aceptan, planificar la validación independiente
  de papel_bond como primer caso. Sin tocar verificador ni generar muestras hasta esa decisión.
