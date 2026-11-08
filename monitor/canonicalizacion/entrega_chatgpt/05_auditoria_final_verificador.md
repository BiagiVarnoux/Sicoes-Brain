# Auditoría final de calidad — verificador tras fase de corrección (SOLO ANÁLISIS)

No modifica reglas ni muestras. Reejecuta el verificador congelado. Los 22/22/22 previos son REGRESIÓN, no validación independiente de esta versión.

Universo: 5067 descripciones únicas, 9,828 pares candidatos. Recordatorio: son pares, no productos independientes; un error de extracción afecta muchos pares.

## 1. Transiciones no-conservadoras de la corrección #1 (etapa 2 → etapa 3)

**ESP INSUF→SI: 7 pares.** ESP NO→INSUF: 2 pares. (Toda nueva confirmación o descontradicción se examina individualmente.)

### 1a. INSUF→SI (nuevas confirmaciones — ¿sustentadas?)
- **[papel_impreso]** A=`PAPEL MEMBRETADO, TAMAÑO CARTA, MEMBRETE PRESIDENCIA; PRESENTACION P…` | B=`PAPEL MEMBRETADO, TAMAÑO CARTA; MEMBRETE PRESIDENCIA; PRESENTACION P…`
    - etapa2(INSUF): tamano: = "carta"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "presentacion presidencia"  →  etapa3(SI): tamano: = "carta"; membrete: = "presentacion presidencia"
- **[papel_impreso]** A=`PAPEL MEMBRETADO, TAMAÑO OFICIO, MEMBRETE TRIBUNAL DEPARTAMENTAL DE …` | B=`PAPEL MEMBRETADO; TAMAÑO OFICIO; MEMBRETE TRIBUNAL DEPARTAMENTAL DE …`
    - etapa2(INSUF): tamano: = "oficio"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "departamental justicia presentacion tribunal"  →  etapa3(SI): tamano: = "oficio"; membrete: = "departamental justicia presentacion tribunal"
- **[papel_impreso]** A=`PAPEL MEMBRETADO, TAMAÑO OFICIO, MEMBRETE TRIBUNAL DEPARTAMENTAL DE …` | B=`Papel Membretado; Tamaño Oficio; Membrete Tribunal Departamental de …`
    - etapa2(INSUF): tamano: = "oficio"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "departamental justicia presentacion tribunal"  →  etapa3(SI): tamano: = "oficio"; membrete: = "departamental justicia presentacion tribunal"
- **[papel_impreso]** A=`PAPEL MEMBRETADO; TAMAÑO CARTA; MEMBRETE ORGANO JUDICIAL - DAF PRESE…` | B=`Papel Membretado; Tamaño Carta; Membrete Organo Judicial - DAF; Pres…`
    - etapa2(INSUF): tamano: = "carta"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "daf judicial organo presentacion"  →  etapa3(SI): tamano: = "carta"; membrete: = "daf judicial organo presentacion"
- **[papel_impreso]** A=`PAPEL MEMBRETADO; TAMAÑO OFICIO; MEMBRETE TRIBUNAL DEPARTAMENTAL DE …` | B=`Papel Membretado; Tamaño Oficio; Membrete Tribunal Departamental de …`
    - etapa2(INSUF): tamano: = "oficio"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "departamental justicia presentacion tribunal"  →  etapa3(SI): tamano: = "oficio"; membrete: = "departamental justicia presentacion tribunal"
- **[papel_impreso]** A=`Papel Membretado; Tamaño Oficio; Membrete Consejo de la Magistratura…` | B=`Papel Membretado; Tamaño oficio; Membrete Consejo de la Magistratura…`
    - etapa2(INSUF): tamano: = "oficio"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "consejo magistratura presentacion"  →  etapa3(SI): tamano: = "oficio"; membrete: = "consejo magistratura presentacion"
- **[llanta]** A=`LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R14; DE CONSTRUCCION RADIAL Y …` | B=`Llanta para Automotor; Medidas 185/70 R14;De construcción radial y t…`
    - etapa2(INSUF): medida: = {"ancho": 185, "perfil": 70, "rin": 14}; aplicacion: = "auto"; tipo_constr: = "radial"; camara: = "sin_camara"; pliegues: falta en AB; huella: falta en AB  →  etapa3(SI): medida: = {"ancho": 185, "perfil": 70, "rin": 14}; tipo_constr: = "radial"; camara: = "sin_camara"

### 1b. NO→INSUF (contradicciones que dejaron de serlo — ¿válido?)
- **[llanta]** A=`LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° DE PLIEGUES 10; SEMI P…` | B=`LLANTAS FIRESTONE ARGENTINA 205/70R15 TRILLA H/T`
    - etapa2(NO): medida: = {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en B; huella: "semi pantanera" ≠ "autopista"  →  etapa3(INSUF): medida: = {"ancho": 205, "perfil": 70, "rin": 15}; tipo_constr: falta en B; camara: falta en B
- **[llanta]** A=`LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° PLIEGUES 10; SEMI PANT…` | B=`LLANTAS FIRESTONE ARGENTINA 205/70R15 TRILLA H/T`
    - etapa2(NO): medida: = {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en B; huella: "semi pantanera" ≠ "autopista"  →  etapa3(INSUF): medida: = {"ancho": 205, "perfil": 70, "rin": 15}; tipo_constr: falta en B; camara: falta en B

## 2. Distribución de los 595 pares ESP=SI por categoría

| categoría | ESP=SI |
|---|---|
| papel_bond | 474 |
| papel_continuo | 76 |
| optico | 22 |
| sobre_manila | 15 |
| papel_impreso | 6 |
| llanta | 2 |

### Ejemplos representativos (hasta 2 por categoría)
- **[papel_bond]** `"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACI…` ≡ `PAPEL BOND BLANCO: TAMAÑO CARTA GRAMAJE 75 GRS. COLOR BLANCO NITIDO;…`
- **[papel_bond]** `"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACI…` ≡ `PAPEL BOND COLOR BLANCO; TAMAÑO CARTA; PAQUETE DE PAPEL DE 500 HOJAS…`
- **[optico]** `DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLA…` ≡ `DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLA…`
- **[optico]** `DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLA…` ≡ `DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLÁ…`
- **[papel_impreso]** `PAPEL MEMBRETADO, TAMAÑO CARTA, MEMBRETE PRESIDENCIA; PRESENTACION P…` ≡ `PAPEL MEMBRETADO, TAMAÑO CARTA; MEMBRETE PRESIDENCIA; PRESENTACION P…`
- **[papel_impreso]** `PAPEL MEMBRETADO, TAMAÑO OFICIO, MEMBRETE TRIBUNAL DEPARTAMENTAL DE …` ≡ `PAPEL MEMBRETADO; TAMAÑO OFICIO; MEMBRETE TRIBUNAL DEPARTAMENTAL DE …`
- **[llanta]** `LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R14; DE CONSTRUCCION RADIAL Y …` ≡ `Llanta para Automotor; Medidas 185/70 R14;De construcción radial y t…`
- **[llanta]** `LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° DE PLIEGUES 10; SEMI P…` ≡ `LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° PLIEGUES 10; SEMI PANT…`
- **[papel_continuo]** `PAPEL CONTINUO, MEDIDAS 9 1/2 X11X2 PLG, GRAMAJE 56 GRS, PRESENTACIO…` ≡ `Papel continuo; medidas 9 1/2 x 11 x 2 plg.; Gramaje 56 Grs.; presen…`
- **[papel_continuo]** `PAPEL CONTINUO, MEDIDAS 9 1/2X11X4X5.5, GRAMAJE 56 GRS, PRESENTACION…` ≡ `PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 4 X 5.5 PLG.; GRAMAJE 56 GRS.; …`
- **[sobre_manila]** `SOBRE MANILA; TAMAÑO 1/2 OFICIO FORMATO COLOR CAFE 90 GRS` ≡ `SOBRE MANILA; TAMAÑO 1/2 OFICIO; FORMATO COLOR CAFE 90 GRS.`
- **[sobre_manila]** `SOBRE MANILA; TAMAÑO CARTA FORMATO COLOR CAFE 90 GRS COLOR MADERA` ≡ `SOBRE MANILA;TAMAÑO CARTA FORMATO COLOR CAFE 90GRS.`

## 6. Consistencia jerárquica de los 595 ESP=SI
- **OK: los 595 ESP=SI tienen SUBFAMILIA=SI y FAMILIA_AMPLIA=SI.** Jerarquía respetada (ESP=SI ⟹ SUB=SI ⟹ FAM=SI).

## 4. Los 2699 pares ESP=INSUF por categoría y motivo

| categoría | ESP=INSUF |
|---|---|
| papel_bond | 1351 |
| papel_continuo | 718 |
| optico | 275 |
| ram | 136 |
| llanta | 97 |
| sobre_manila | 51 |
| almacenamiento | 46 |
| papel_impreso | 25 |

### Motivo de insuficiencia (agregado)
| motivo | pares |
|---|---|
| ausencia en UN lado (atributo de identidad no declarado) | 821 |
| requisito/residuo no acreditado | 815 |
| ausencia en AMBOS lados (candidato débil) | 665 |
| mecanismo de copia no confirmado (soft) | 347 |
| empaque (juegos vs hojas) | 51 |

### Motivo × categoría
| categoría | motivo | pares |
|---|---|---|
| papel_bond | requisito/residuo no acreditado | 815 |
| papel_bond | ausencia en UN lado (atributo de identidad no declarado) | 367 |
| papel_continuo | mecanismo de copia no confirmado (soft) | 347 |
| papel_continuo | ausencia en UN lado (atributo de identidad no declarado) | 233 |
| papel_bond | ausencia en AMBOS lados (candidato débil) | 169 |
| optico | ausencia en AMBOS lados (candidato débil) | 147 |
| ram | ausencia en AMBOS lados (candidato débil) | 136 |
| optico | ausencia en UN lado (atributo de identidad no declarado) | 128 |
| papel_continuo | ausencia en AMBOS lados (candidato débil) | 87 |
| llanta | ausencia en AMBOS lados (candidato débil) | 77 |
| papel_continuo | empaque (juegos vs hojas) | 51 |
| sobre_manila | ausencia en UN lado (atributo de identidad no declarado) | 38 |
| almacenamiento | ausencia en AMBOS lados (candidato débil) | 36 |
| papel_impreso | ausencia en UN lado (atributo de identidad no declarado) | 25 |
| llanta | ausencia en UN lado (atributo de identidad no declarado) | 20 |
| sobre_manila | ausencia en AMBOS lados (candidato débil) | 13 |
| almacenamiento | ausencia en UN lado (atributo de identidad no declarado) | 10 |

## 3. Conjuntos IDENT por categoría (obligatorio para ESP=SI)

Para cada categoría: SEGMENTO (discrimina subfamilia) ⊆ IDENT (identidad). Lo que está en IDENT y NO en SEGMENTO es un discriminante de PRODUCTO ESPECÍFICO (complementario a nivel de demanda, determinante a nivel de identidad).

| categoría | SEGMENTO (subfamilia) | IDENT∖SEGMENTO (específico) |
|---|---|---|
| almacenamiento | tecnologia, capacidad_gb | interfaz, formato |
| llanta | medida, aplicacion | tipo_constr, camara |
| optico | tipo_medio, capacidad_gb | grabacion_pol, presentacion |
| papel_bond | tamano, gramaje_gm2 | color, hojas |
| papel_continuo | formato_continuo, partes, gramaje_gm2 | — |
| papel_impreso | tamano | membrete |
| ram | generacion, capacidad_gb | frecuencia_mhz, formato |
| sobre_manila | tamano | gramaje_gm2, color |

## 5. (Análisis en prosa, ver más abajo en el reporte redactado a mano.)
---

## Análisis redactado (IDENT, estrictez, hallazgos) — SOLO diagnóstico

### Veredicto ESP por categoría (universo completo)
| categoría | pares | SI | INSUF | NO |
|---|---|---|---|---|
| papel_bond | 5460 | 474 | 1351 | 3635 |
| papel_continuo | 1953 | 76 | 718 | 1159 |
| optico | 561 | 22 | 275 | 264 |
| llanta | 528 | 2 | 97 | 429 |
| almacenamiento | 351 | 0 | 46 | 305 |
| ram | 325 | 0 | 136 | 189 |
| papel_impreso | 325 | 6 | 25 | 294 |
| sobre_manila | 325 | 15 | 51 | 259 |

### 1 — Veredicto sobre las 9 transiciones de #1
**Las 7 INSUF→SI son defendibles.** Seis son papel membretado con el MISMO membrete y tamaño; el #1
quitó `gramaje`/`color` del IDENT de `papel_impreso` (rara vez se declaran en membretados y no son el
discriminante: la identidad de un membretado ES el membrete + tamaño). El séptimo es una llanta
185/70 R14 radial sin cámara idéntica; el #1 dejó el IDENT de llanta en medida+construcción+cámara.
En los 7, los atributos de identidad vigentes coinciden exactamente → SI sustentado, no accidental.

**Las 2 NO→INSUF son un HALLAZGO, no un acierto.** Ambas son la misma llanta 205/70 R15:
A = "SEMI PANTANERA" (pliegues 10) vs B = Firestone "TRILLA H/T" (huella de autopista). En etapa 2 el
verificador daba NO correcto porque `huella` "semi pantanera" ≠ "autopista" es una **contradicción real
y determinante para un DBC** (barro vs carretera son llantas distintas). Al quitar `huella` del IDENT, el
#1 **borró una contradicción válida** y la degradó a INSUF. Esto NO es ser más conservador: en estos 2
pares el verificador quedó MENOS correcto. Es exactamente la clase de diferencia que se pidió preservar.

> **Recomendación (sin implementar):** `huella` y `pliegues` de llanta no deben quitarse del todo del
> juicio de identidad; deben ser **discriminantes solo-contradicción** (ausencia no degrada, pero
> `huella_A ≠ huella_B` → NO). Así se conservan las 7 confirmaciones legítimas y se recupera el NO de
> estos 2 pares. Es un ajuste de curaduría del IDENT, no una relajación.

### 3 — Auditoría de IDENT por categoría
- **SEGMENTO ⊆ IDENT en todas las categorías** → la jerarquía se respeta por construcción (verificado:
  0 violaciones; los 595 ESP=SI tienen SUB=SI y FAM=SI).
- **RAM** IDENT = generacion, capacidad_gb, frecuencia_mhz, formato. `frecuencia_mhz` y `formato` casi
  nunca se declaran → **0 ESP=SI** en 325 pares (136 INSUF, 189 NO). No es un error: capacidad y
  generación bastan para separar (NO), pero confirmar identidad exige lo que la descripción no trae.
- **almacenamiento** IDENT = tecnologia, capacidad_gb, interfaz, formato. Igual: **0 SI** (46 INSUF, 305 NO).
- **papel_continuo** IDENT = formato_continuo, partes, gramaje_gm2 (+ mecanismo_copia SOFT). El mecanismo
  nunca baja a NO (terminología imprecisa); 347 pares quedan INSUF por mecanismo ausente/distinto.
- **llanta** IDENT actual = medida, tipo_constr, camara. **Falta huella/pliegues como solo-contradicción**
  (ver hallazgo arriba).

### 5 — ¿Reglas demasiado estrictas? (sin relajar)
- **RAM/almacenamiento (0 SI):** es estrictez POR DISEÑO y alineada con tu instrucción de no relajar
  capacidad/generación/interfaz/formato por ser determinantes. Los 182 INSUF son **candidatos legítimos**,
  no falsos negativos. Decisión de curaduría tuya: si `frecuencia_mhz`/`formato` deben pasar a
  "complementario solo-contradicción" (ausencia no bloquea, contradicción sí) — igual que propongo para huella.
- **requisito/residuo no acreditado (815 pares INSUF):** es el detector de residuo (ISO/norma/alcalino/
  "o equivalente"). Mantenerlos INSUF es conservador-correcto: son requisitos potencialmente de DBC. NO es
  estrictez indebida; sí conviene revisar que la exención "o equivalente" no esté dejando pasar de más.
- **La única regla que resultó demasiado PERMISIVA** (no estricta) es la que generó las 2 NO→INSUF de llanta.

### 4 — Motivo de los 2.699 ESP=INSUF
| motivo | pares | interpretación |
|---|---|---|
| ausencia en UN lado | 821 | atributo de identidad declarado en un lado, ausente en el otro → se asume nada |
| requisito/residuo no acreditado | 815 | ISO/norma/alcalino/"o equiv." presente en un lado |
| ausencia en AMBOS lados | 665 | candidato débil (ninguno declara el atributo) |
| mecanismo de copia (soft) | 347 | continuo: químico/carbónico ausente o distinto → no confirmado |
| empaque (juegos vs hojas) | 51 | unidades no equiparables |

**Ausencia real vs fallo de extracción:** gramaje, color, hojas, frecuencia y formato son campos que el
SICOES **genuinamente omite** con frecuencia (ausencia real, no fallo). En cambio, la ausencia de
`formato_continuo` o `medida` (atributos casi siempre presentes en el texto) es **sospechosa de fallo de
extracción** y merece una revisión dirigida del extractor en esos pares. No cuantificado aún por par;
recomiendo una sub-auditoría del extractor solo sobre los "ausencia de atributo primario".

### 6 — Consistencia jerárquica
Verificado programáticamente: los **595 ESP=SI tienen SUBFAMILIA=SI y FAMILIA_AMPLIA=SI** (0 violaciones).
Nota: FAMILIA_AMPLIA sigue siendo SI por construcción (no mide discriminación — precaución #4 pendiente).

### Conclusión de la auditoría
1. La fase de corrección es mayormente sólida: 595 ESP=SI jerárquicamente consistentes, 7 nuevas
   confirmaciones sustentadas.
2. **Un defecto concreto:** el #1 quitó `huella`/`pliegues` del IDENT de llanta y borró 2 contradicciones
   válidas (NO→INSUF). Es el único movimiento que empeoró la correctitud. Fix propuesto: huella/pliegues
   como solo-contradicción.
3. RAM/almacenamiento con 0 confirmados es esperado y correcto; no relajar.
4. Pendiente genuino: validación independiente de esta versión (los 22/22/22 son regresión), negativos
   cross-familia (#4), y una sub-auditoría del extractor sobre ausencias de atributo primario.
