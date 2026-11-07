# Scoring INDEPENDIENTE — muestra v2 (22 pares, solo papel) vs línea base congelada (df9535a)

Evaluación independiente: esta muestra NO se usó para ajustar el verificador. Línea base intacta.
Etiquetas asistidas (ChatGPT), NO verdad certificada. Solo categorías de papel (bond/continuo/impreso):
no valida llanta/ram/disco/óptico/sobre. Registro del scoring ANTES de proponer cualquier corrección.

## Concordancia (NO precisión certificada)
FAMILIA_AMPLIA 22/22 · SUBFAMILIA 17/22 · PRODUCTO_ESPECIFICO 19/22.

## Matrices de confusión (filas=humano, cols=propuesta)
**FAMILIA_AMPLIA** — SI 22/22. (Tautológico: el verificador devuelve SI por construcción; no mide
discriminación — ver precaución #4. No interpretar como precisión validada.)

**SUBFAMILIA**
| humano\propuesta | SI | NO | INSUF |
|---|---|---|---|
| SI | 9 | 0 | 0 |
| NO | 0 | 6 | 0 |
| INSUF | **5** | 0 | 2 |

**PRODUCTO_ESPECIFICO**
| humano\propuesta | SI | NO | INSUF |
|---|---|---|---|
| SI | 3 | 0 | 0 |
| NO | 0 | 10 | 0 |
| INSUF | **3** | 0 | 6 |

## Perfil de riesgo (lo más importante)
Las 8 discrepancias son TODAS **humano=INSUF → propuesta=SI**. **0 confusiones SI↔NO** y **0 NO↔SI** en
los tres niveles: el verificador nunca declara "distinto" donde el humano dice "igual" ni viceversa; solo
es MENOS conservador en la frontera SI/INSUF. No hay fusiones que contradigan un NO ni separaciones falsas.

## Análisis individual de las 8 discrepancias (causa raíz; no se asume infalible la etiqueta)
Todas caen en UNA de las tres correcciones YA propuestas (precauciones #1/#2/#3). Ninguna es un modo de
fallo nuevo — y como se diseñaron desde OTRA muestra (las 53), su poder predictivo sobre esta es señal
de que son generales, no ajustes a una muestra.

**Grupo A — regla de SECUNDARIOS (gramaje ausente → hoy SI; debería ser INSUF). Precaución #3.**
- **V002** SUB SI→INSUF: B omite gramaje ("blanco ultra alcalino", sin g/m²). Extractor correcto (no hay
  dato). Causa = REGLA de secundarios (ausencia no debería confirmar subfamilia).
- **V016** SUB SI→INSUF: igual, B omite gramaje.
- **V011** SUB SI→INSUF: AMBOS omiten gramaje (continuo 9.5x11x4 autocopiativo). Formato+partes coinciden;
  gramaje ausente en ambos → candidato, no confirmado.
- **V017** SUB SI→INSUF: igual (uno omite gramaje; mecanismos autocopiativo/químico coinciden).
- **V021** SUB SI→INSUF: A es escueto ("papel bond oficio"); B completo. Solo coincide tamaño → INSUF.
  → Causa de grupo A: la regla "ausencia de secundario no degrada" convierte INSUF en SI. Fix propuesto
    (#3): la ausencia MANTIENE INSUF; solo una CONTRADICCIÓN baja a NO. Los 5 pasarían a INSUF = humano.

**Grupo B — identidad específica con requisito/empaque no modelado (ESP SI→INSUF). Precaución #1.**
- **V008** ESP SI→INSUF: "750 Jgs" (juegos) vs "750 HOJAS" — unidades de empaque NO equiparables, y A no
  explicita mecanismo. Causa = EXTRACTOR no modela juegos≠hojas + CRITERIO de identidad (completitud).
- **V020** ESP SI→INSUF: A "paquete de 500", B sin presentación/cantidad. Causa = CRITERIO de identidad
  (falta un atributo de identidad → candidato, no confirmado).
  → Fix propuesto (#1): ESP=SI = identidad CONFIRMADA (atributos de identidad completos y sin residuo sin
    explicar); si falta → INSUF (candidato). Los 2 pasarían a INSUF = humano.

**Grupo C — mecanismo de copia vs desglose (ESP SI→INSUF). Precaución #2.**
- **V013** ESP SI→INSUF: A dice "Con Desglose" (presentación), B "Con Desglose QUIMICO" (mecanismo). Mi
  colapso v2 los igualó → SI. Correcto: A NO declara mecanismo → mecanismo INSUF, no confirmado igual.
  Causa = CRITERIO (#2): separar mecanismo (químico/carbónico) de desglose (presentación); ausencia de
  mecanismo en un lado → INSUF. Pasaría a INSUF = humano. (Confirma que mi colapso v2 fue demasiado grueso.)

## Correcciones propuestas e IMPACTO ESTIMADO en el corpus (NO implementadas)
1. **#3 Ausencia de secundario → INSUF (no SI).** Impacto medido en la auditoría: ~**1.035 pares**
   SUBFAMILIA=SI pasarían a INSUF (los que hoy suben por ausencia de gramaje/aplicación). No crea NO
   nuevos. Resuelve V002/V011/V016/V017/V021.
2. **#1 ESP=SI = identidad confirmada; si falta un atributo de identidad o hay residuo sin explicar →
   INSUF.** Impacto estimado: un subconjunto de los 1.325 pares ESP=SI actuales (los que omiten un atributo
   de identidad o traen requisito no acreditado: ISO/alcalino, empaque juegos/hojas). Cuantificable si se
   desea (simulación read-only). Resuelve V008/V020.
3. **#2 Separar mecanismo_copia (químico/autocopiativo vs carbónico) de desglose; ausencia de mecanismo →
   INSUF; NO presuponer químico≡carbónico intercambiables (preservar diferencias determinantes para DBC).**
   Impacto estimado: revierte el colapso que hoy iguala ~84+ pares de continuo; moverá ESP de SI→INSUF/NO
   donde el mecanismo no esté confirmado. Resuelve V013.

Todas las correcciones empujan en la MISMA dirección: ser más conservador en la frontera SI→INSUF, que es
exactamente donde están las 8 discrepancias. Ninguna toca los veredictos NO ni SI↔NO (el perfil de riesgo
ya es limpio). Separado del veredicto: la AUTORIZACIÓN a fusionar debe exigir ESP=SI confirmado (nunca
fusionar sobre INSUF).

## Límites y pendientes
- Muestra pequeña (22) y solo papel: no mide llanta/ram/disco/óptico/sobre (requieren datos nuevos).
- FAMILIA_AMPLIA sigue sin validación de discriminación (faltan negativos difíciles y errores de
  categorización — precaución #4).
- NO implementar aún; NO avanzar a agrupación ni agregación. Decidir correcciones en conjunto.
