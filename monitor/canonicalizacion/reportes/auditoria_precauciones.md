# Auditoría de precauciones (#3 secundarios, #4 familia amplia) — SOLO LECTURA

## #3 — Efecto AISLADO de la regla de atributos SECUNDARIOS sobre SUBFAMILIA
Comparación usar_sec=True vs usar_sec=False con LOS MISMOS atributos enriquecidos (aísla la regla, no mezcla con la extracción tolerante). Solo categorías con secundarios: papel_bond, papel_continuo, llanta.

| transición SUBFAMILIA (sin regla → con regla) | pares |
|---|---|
| INSUF → SI | 1035 |

**INSUF→SI por la regla: 1035.** De ellos, riesgo de falso positivo:
- **901**: UN lado declara el secundario (gramaje/aplicación) y el otro NO → se asume que coincide (riesgo real).
- **134**: NINGÚN lado lo declara → no hay valor que contradecir (riesgo bajo).
- INSUF→NO por la regla (secundario que CONTRADICE → detecta diferencia): 0.

Ejemplos INSUF→SI (revisar si el secundario ausente oculta una diferencia real):
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 »
    - B: «PAPEL BOND TAMAÑO CARTA»
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 »
    - B: «PAPEL BOND TAMAÑO CARTA PAPEL ALCALINO»
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 »
    - B: «PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 GRMS; COLOR BLANCO; PRESENTACION POR PAQUETE DE »
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 »
    - B: «Papel Bond color blanco: • Tamaño Carta, 216 x 279 mm, • Paquete de Papel de 500 hoja»
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500»
    - B: «PAPEL BOND OFICIO DE COLOR SURTIDO»
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500»
    - B: «PAPEL BOND TAMANO OFICIO»
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500»
    - B: «PAPEL BOND TAMAÑO OFICIO»
- [papel_bond] secundario=['gramaje_gm2']  A={"gramaje_gm2": 75} B={"gramaje_gm2": null}
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500»
    - B: «PAPEL BOND TAMAÑO OFICIO PAPEL ALCALINO»

Ejemplos INSUF→NO (la regla detectó una diferencia de secundario):

## #4 — Discriminación de FAMILIA_AMPLIA (necesita negativos de distintas familias)
Categorías (familias amplias) en alcance: 8 → almacenamiento, llanta, optico, papel_bond, papel_continuo, papel_impreso, ram, sobre_manila.
Pares cross-categoría probados: 28; el pipeline los separa por categoría en **28/28**.
**ADVERTENCIA:** el 53/53 de FAMILIA_AMPLIA NO mide discriminación: el blocker solo empareja dentro de la misma categoría, y el verificador DEVUELVE FAM=SI por construcción (hardcode). Nunca se le presentan pares de distinta familia, así que no hay oportunidad de equivocarse → 53/53 es tautológico.
La separación de familias ocurre en el BLOCKER (regla dura de tipo), no en el verificador. Ejemplos de negativos cross-familia (deberían ser FAMILIA_AMPLIA=NO; el blocker nunca los genera):
- almacenamiento ≠ llanta (separados por categoría: True)
    - A: «Accesorio para computador; tipo disco duro sata, capacidad 1tb; presen» · B: «LLANTA PARA AUTOMOTOR; MEDIDAS 195/65 R15; N°. DE PLIEGES 8; HUELLA AU»
- almacenamiento ≠ optico (separados por categoría: True)
    - A: «DISCO DURO 500 GB INTERNO SATA» · B: «Disco Compacto; Capacidad 4.7 Gb; Tipo Dvd - Rx4 Virgen Sin Caja- HP.»
- almacenamiento ≠ papel_bond (separados por categoría: True)
    - A: «ACCESORIO O REPUESTO DE COMPUTADORA; DISCO DURO PURPURA HDD 3,5"; CAPA» · B: «PAPEL BOND BLANCO: TAMAÑO CARTA GRAMAJE 75 GRS. COLOR BLANCO NITIDO; P»
- almacenamiento ≠ papel_continuo (separados por categoría: True)
    - A: «aAccesorio para computador; tipo disco solido interno ssd de 250 gb 2.» · B: «PAPEL CONTINUO QUIMICO; 9 1/2 X 11 X 3, PRESENTACION POR CAJA DE 1000 »
- almacenamiento ≠ papel_impreso (separados por categoría: True)
    - A: «ACCESORIO PARA COMPUTADOR; TIPO DISCO SOLIDO INTERNO SSD DE 2,5"; CAPA» · B: «PAPEL MEMBRETADO,TAMAÑO OFICIO;MEMBRETE TRIBUNAL DEPARTAMENTAL DE JUST»
- almacenamiento ≠ ram (separados por categoría: True)
    - A: «DISCO DURO SSD 512 GB interfaz de host: sata 3.0» · B: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM »
- almacenamiento ≠ sobre_manila (separados por categoría: True)
    - A: «DISCO DURO EXTERNO DE 2TB USB 3.0» · B: «SOBRE MANILA; TAMAÑO 1/2 OFICIO FORMATO COLOR CAFE 90 GRS»
- llanta ≠ optico (separados por categoría: True)
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/65 R14 N° PLIEGUES 10; 87H; TIPO TU» · B: «DISCO COMPACTO DE GRABACION»
- llanta ≠ papel_bond (separados por categoría: True)
    - A: «LLANTA PARA MOTOCICLETA; MEDIDAS 90-90-18; TIPO TRASERA» · B: «PAPEL BOND TAMAÑO CARTA PAPEL ALKALINO DE ALTA BLANCURA 75 G/M2 216 MM»
- llanta ≠ papel_continuo (separados por categoría: True)
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R13; DE CONSTRUCCIÓN RADIAL Y TU» · B: «PAPEL CONTINUO BLANCO QUÍMICO (O AUTO COPIANTE TÉRMICO) 9 1/2*11*4 ORI»