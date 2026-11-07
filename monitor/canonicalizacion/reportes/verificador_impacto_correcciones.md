# Etapa 3 — Impacto de la fase de corrección controlada (#3→#2→#1) sobre 9.828 pares

Universo: 5067 descripciones únicas; 9,828 pares candidatos. Línea base = commit 2ff01aa (congelada). Cada etapa añade UNA corrección sobre la anterior (aislamiento acumulativo).

## Distribución por etapa
| etapa | SUB SI | SUB NO | SUB INSUF | ESP SI | ESP NO | ESP INSUF |
|---|---|---|---|---|---|---|
| 0 baseline | 3718 | 5435 | 675 | 1325 | 6536 | 1967 |
| 1 +#3 secundarios | 2696 | 5435 | 1697 | 1325 | 6536 | 1967 |
| 2 +#2 mecanismo | 2696 | 5435 | 1697 | 1232 | 6536 | 2060 |
| 3 +#1 identidad | 2696 | 5435 | 1697 | 595 | 6534 | 2699 |

## Transiciones entre etapas consecutivas (estado = SUBFAMILIA/PRODUCTO_ESPECIFICO)

### 0 baseline → 1 +#3 secundarios: 1022 pares cambian · **hacia NO nuevo: 0**
| de (SUB/ESP) | a (SUB/ESP) | pares |
|---|---|---|
| SI/INSUF | INSUF/INSUF | 869 |
| SI/NO | INSUF/NO | 153 |

### 1 +#3 secundarios → 2 +#2 mecanismo: 93 pares cambian · **hacia NO nuevo: 0**
| de (SUB/ESP) | a (SUB/ESP) | pares |
|---|---|---|
| SI/SI | SI/INSUF | 93 |

### 2 +#2 mecanismo → 3 +#1 identidad: 653 pares cambian · **hacia NO nuevo: 0**
| de (SUB/ESP) | a (SUB/ESP) | pares |
|---|---|---|
| SI/SI | SI/INSUF | 644 |
| SI/INSUF | SI/SI | 7 |
| SI/NO | SI/INSUF | 2 |
## Regresión sobre muestras previas (ahora pruebas de regresión, NO validación)
- **Muestra v2 (22, independiente, motivó las correcciones): 22/22/22, 0 discrepancias.** Las 8 se resuelven
  por mecanismos generales (#3/#2/#1), no por reglas ad-hoc.
- **Muestra 53 (previa): FAM 53/53, SUB 49/53, ESP 51/53 (6 discrepancias).** Todas son la tensión conocida,
  NO contradicciones nuevas (0 casos "propuesta SI vs humano NO" o "propuesta NO vs humano SI"):
  - V011/V027/V035/V051: SUB propuesta INSUF vs 53-humano SI (gramaje ausente). El MISMO etiquetador marcó
    estos casos como INSUF en la muestra v2 independiente → el #3 coincide con su criterio más reciente; las
    etiquetas 53 eran menos conservadoras. Esperado al congelar las 53 como regresión.
  - V023: etiqueta 53 internamente inconsistente (decía "B sin gramaje" pero B lo tiene) → SI defendible.
  - V045: ESP INSUF vs humano NO (empaque juegos/hojas + formato sin "11"); INSUF conservador (no fusiona).
- **Extractor: regresión 11/11 (congelado, sin cambios).**

## Semántica de los 3 niveles (sin cambios silenciosos) y separación veredicto/fusión
- FAMILIA_AMPLIA = mismo tipo; SUBFAMILIA = misma familia de demanda (todos los atributos de segmento
  presentes e iguales; ausencia→INSUF, contradicción→NO; 'aplicacion' solo-contradicción); PRODUCTO_ESPECIFICO
  = identidad CONFIRMADA (IDENT completo + sin requisito no acreditado); INSUF = candidato no confirmado.
- El veredicto NO autoriza fusión: fusionar exigirá ESP=SI; nunca sobre INSUF. (Etapa posterior, no aquí.)
