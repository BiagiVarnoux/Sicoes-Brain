# Etapa 3 — Verificador por niveles (EXPERIMENTAL NO VALIDADO, solo lectura)

Universo: **5067 descripciones ÚNICAS** (NO los ~7.441 registros hist_items). Pares candidatos verificados: **9,828**. Capa correctiva aplicada (extractor congelado).

Tres veredictos SEPARADOS: FAMILIA_AMPLIA (equivalencia comercial) · SUBFAMILIA (misma familia de demanda) · PRODUCTO_ESPECIFICO (identidad exacta). Atributo ausente ≠ igual → INSUF.

## Distribución de veredictos por categoría (SUBFAMILIA × PRODUCTO_ESPECIFICO)
| categoría | pares | sub=SI·esp=SI | sub=SI·esp=INSUF | sub=SI·esp=NO | sub=NO | sub=INSUF |
|---|---|---|---|---|---|---|
| almacenamiento | 351 | 0 | 9 | 0 | 302 | 40 |
| llanta | 528 | 1 | 14 | 4 | 427 | 82 |
| optico | 561 | 22 | 51 | 64 | 200 | 224 |
| papel_bond | 5460 | 1108 | 717 | 886 | 2749 | 0 |
| papel_continuo | 1953 | 179 | 376 | 0 | 1159 | 239 |
| papel_impreso | 325 | 0 | 6 | 144 | 150 | 25 |
| ram | 325 | 0 | 71 | 0 | 189 | 65 |
| sobre_manila | 325 | 15 | 51 | 0 | 259 | 0 |
| **TOTAL** | **9828** | **1325** | **1295** | **1098** | **5435** | **675** |

> Son resultados del algoritmo, NO una medición de precisión. Que N pares den 'mismo específico' NO prueba que sean intercambiables: eso requiere validación independiente a 3 niveles con datos nuevos.

## Impacto de la capa correctiva (base → corregido; aísla sistémico vs aislado)
Pares cuyo veredicto CAMBIÓ: **1654** de 9,828.
| cambio (SUB/ESP base → corregido) | pares |
|---|---|
| papel_bond: INSUF/INSUF → SI/INSUF | 496 |
| papel_continuo: INSUF/INSUF → SI/INSUF | 334 |
| papel_bond: INSUF/NO → SI/NO | 184 |
| papel_impreso: SI/INSUF → SI/NO | 144 |
| papel_continuo: SI/NO → SI/SI | 84 |
| llanta: INSUF/INSUF → NO/NO | 68 |
| papel_bond: SI/INSUF → SI/NO | 55 |
| optico: SI/INSUF → SI/NO | 54 |
| papel_bond: SI/INSUF → SI/SI | 48 |
| papel_continuo: INSUF/NO → SI/INSUF | 42 |
| papel_bond: INSUF/NO → NO/NO | 31 |
| papel_continuo: INSUF/NO → INSUF/INSUF | 20 |
| papel_bond: INSUF/INSUF → SI/SI | 16 |
| optico: SI/SI → SI/INSUF | 15 |
| llanta: INSUF/INSUF → SI/INSUF | 14 |
| optico: SI/INSUF → SI/SI | 11 |
| sobre_manila: SI/NO → SI/INSUF | 11 |
| optico: SI/SI → SI/NO | 10 |
| papel_bond: INSUF/INSUF → SI/NO | 6 |
| papel_bond: INSUF/INSUF → NO/NO | 4 |
| llanta: INSUF/NO → SI/NO | 4 |
| almacenamiento: SI/NO → SI/INSUF | 1 |
| almacenamiento: INSUF/NO → INSUF/INSUF | 1 |
| llanta: INSUF/INSUF → SI/SI | 1 |

Ejemplos de cambios:
- [papel_bond: INSUF/INSUF → SI/INSUF] tamano: = "carta"; gramaje_gm2: falta en B; color: falta en B
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO CARTA»
- [papel_bond: INSUF/INSUF → SI/INSUF] tamano: = "carta"; gramaje_gm2: falta en B; color: falta en B
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO CARTA PAPEL ALCALINO»
- [papel_continuo: INSUF/INSUF → SI/INSUF] formato_continuo: = "9.5x11"; partes: = 4; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO 9 1/2X11X4»
- [papel_continuo: INSUF/INSUF → SI/INSUF] formato_continuo: = "9.5x11"; partes: = 4; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO AUTOCOPIATIVO 9.5 X 11 X 4»
- [papel_bond: INSUF/NO → SI/NO] tamano: = "oficio"; gramaje_gm2: falta en B; color: "blanco" ≠ "surtido"
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJA»
    - B: «PAPEL BOND OFICIO DE COLOR SURTIDO»
- [papel_bond: INSUF/NO → SI/NO] tamano: = "oficio"; gramaje_gm2: = 75; color: "blanco" ≠ "surtido"
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJA»
    - B: «PAPEL BOND TAMAÑO OFICIIO DIFERENTES COLORES DE 75 GR»
- [papel_impreso: SI/INSUF → SI/NO] tamano: = "oficio"; gramaje_gm2: = 75; color: falta en AB; membrete: "bond consejo magistratura material" ≠ "bond material plena sala"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJ»
    - B: «HOJA MEMBRETADA SALA PLENA TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IMPRESIÓN FULL»
- [papel_impreso: SI/INSUF → SI/NO] tamano: = "oficio"; gramaje_gm2: = 75; color: falta en AB; membrete: "bond consejo magistratura material" ≠ "bond material tdj"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJ»
    - B: «HOJA MEMBRETADA TDJ TAMAÑO OFICIO (21.5X33CM); PAQUETE DE 500 HOJAS IMPRESIÓN FULL COLOR A»
- [papel_continuo: SI/NO → SI/SI] formato_continuo: = "9.5x11"; partes: = 2; gramaje_gm2: = 56; tipo: = "autocopiativo"
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2 X11X2 PLG, GRAMAJE 56 GRS, PRESENTACION POR CAJAS X 1500 HOJ»
    - B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACION POR CAJAS X 150»
- [papel_continuo: SI/NO → SI/SI] formato_continuo: = "9.5x11"; partes: = 2; gramaje_gm2: = 56; tipo: = "autocopiativo"
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2 X11X2 PLG, GRAMAJE 56 GRS, PRESENTACION POR CAJAS X 1500 HOJ»
    - B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN CAJA DE 1.500 H»
- [llanta: INSUF/INSUF → NO/NO] medida: falta en B; aplicacion: "auto" ≠ "moto"; tipo_constr: falta en B; camara: falta en B; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 175/70 R13; HUELLA A; TIPO RADIAL; SIN CAMARA; SIN PONCHILL»
    - B: «Llantas Delanteras Moto Honda»
- [llanta: INSUF/INSUF → NO/NO] medida: falta en B; aplicacion: "auto" ≠ "moto"; tipo_constr: falta en B; camara: falta en B; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 175/70 R13; HUELLA A; TIPO RADIAL; SIN CAMARA; SIN PONCHILL»
    - B: «Llantas Delanteras Moto Serna»

## Ejemplos trazables (coincidencias y contradicciones)

### almacenamiento
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tecnologia: = "ssd"; capacidad_gb: = 250.0; interfaz: falta en AB; formato: falta en B
    - A: «: accesorio para computador; tipo disco solido interno ssd de 250 gb 2.5»
    - B: «ACCESORIO PARA COMPUTADOR; TIPO DISCO SOLIDO INTERNO SSD DE 2,5"; CAPACIDAD DE 250 GB»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tecnologia: = "ssd"; capacidad_gb: = 250.0; interfaz: falta en AB; formato: = "2.5"
    - A: «: accesorio para computador; tipo disco solido interno ssd de 250 gb 2.5»
    - B: «aAccesorio para computador; tipo disco solido interno ssd de 250 gb 2.5"»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tecnologia: = "ssd"; capacidad_gb: = 240.0; interfaz: falta en AB; formato: falta en A
    - A: «ACCESORIO PARA COMPUTADOR; TIPO DISCO SOLIDO INTERNO SSD DE 2,5"; CAPACIDAD DE 240 GB»
    - B: «Accesorio para computador; disco solido interno SSD de 2.5”, Capacidad de 240 GB.»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tecnologia: = "ssd"; capacidad_gb: = 240.0; interfaz: falta en AB; formato: falta en A
    - A: «ACCESORIO PARA COMPUTADOR; TIPO DISCO SOLIDO INTERNO SSD DE 2,5"; CAPACIDAD DE 240 GB»
    - B: «Accesorio para computador; disco solido interno ssd de 2.5”, capacidad de 240 gb.»
- ✗ DISTINTA SUBFAMILIA  ·  tecnologia: "ssd" ≠ "hdd"; capacidad_gb: 250.0 ≠ 10000.0
    - A: «: accesorio para computador; tipo disco solido interno ssd de 250 gb 2.5»
    - B: «ACCESORIO O REPUESTO DE COMPUTADORA; DISCO DURO PURPURA HDD 3,5"; CAPACIDAD 10 TB»
- ✗ DISTINTA SUBFAMILIA  ·  tecnologia: falta en B; capacidad_gb: 250.0 ≠ 1000.0
    - A: «: accesorio para computador; tipo disco solido interno ssd de 250 gb 2.5»
    - B: «ACCESORIO PARA COMPUTADOR; TIPO DISCO DURO INTERNO; CAPACIDAD 1 TB»
- ✗ DISTINTA SUBFAMILIA  ·  tecnologia: = "ssd"; capacidad_gb: 250.0 ≠ 240.0
    - A: «: accesorio para computador; tipo disco solido interno ssd de 250 gb 2.5»
    - B: «ACCESORIO PARA COMPUTADOR; TIPO DISCO SOLIDO INTERNO SSD DE 2,5"; CAPACIDAD DE 240 GB»
- ✗ DISTINTA SUBFAMILIA  ·  tecnologia: = "ssd"; capacidad_gb: 250.0 ≠ 512.0
    - A: «: accesorio para computador; tipo disco solido interno ssd de 250 gb 2.5»
    - B: «Accesorio para Computador; Tipo Disco Duro SATA SSD 512 GB»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tecnologia: = "ssd"; capacidad_gb: falta en B; interfaz: falta en A; formato: falta en B
    - A: «: accesorio para computador; tipo disco solido interno ssd de 250 gb 2.5»
    - B: «DISCOS DUROS SOLIDOS Capacidad: 500GB o superior Interfaz/Protocolo: SATA (SATA 6,0 Gb/s / AHCI»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tecnologia: falta en AB; capacidad_gb: = 1000.0; interfaz: falta en AB; formato: falta en AB
    - A: «ACCESORIO PARA COMPUTADOR; TIPO DISCO DURO INTERNO; CAPACIDAD 1 TB»
    - B: «Accesorio para computador; tipo disco duro interno; capacidad 1 tb»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tecnologia: falta en AB; capacidad_gb: = 1000.0; interfaz: falta en A; formato: falta en AB
    - A: «ACCESORIO PARA COMPUTADOR; TIPO DISCO DURO INTERNO; CAPACIDAD 1 TB»
    - B: «Accesorio para computador; tipo disco duro sata, capacidad 1tb; presentacion por unidad»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tecnologia: falta en A; capacidad_gb: = 1000.0; interfaz: falta en A; formato: falta en AB
    - A: «ACCESORIO PARA COMPUTADOR; TIPO DISCO DURO INTERNO; CAPACIDAD 1 TB»
    - B: «DISCOS DUROS HDD 1TB SATA»

### llanta
- ✅ MISMO ESPECÍFICO  ·  medida: = {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: = "auto"; tipo_constr: = "tubular"; camara: = "sin_camara"; pliegues: = 10; huella: = "semi pantanera"
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° DE PLIEGUES 10; SEMI PANTANERA; TIPO TUBULAR; SIN»
    - B: «LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° PLIEGUES 10; SEMI PANTANERA; TIPO TUBULAR; SIN CÁ»
- ≈ MISMA FAMILIA, distinto específico  ·  medida: = {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en B; huella: "semi pantanera" ≠ "autopista"
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° DE PLIEGUES 10; SEMI PANTANERA; TIPO TUBULAR; SIN»
    - B: «LLANTAS FIRESTONE ARGENTINA 205/70R15 TRILLA H/T»
- ≈ MISMA FAMILIA, distinto específico  ·  medida: = {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: = "auto"; tipo_constr: "tubular" ≠ "radial"; camara: falta en B; pliegues: falta en B; huella: falta en B
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° DE PLIEGUES 10; SEMI PANTANERA; TIPO TUBULAR; SIN»
    - B: «Llanta para Automotor; Medidas 205/70 R15; Tipo Radial»
- ≈ MISMA FAMILIA, distinto específico  ·  medida: = {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en B; huella: "semi pantanera" ≠ "autopista"
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° PLIEGUES 10; SEMI PANTANERA; TIPO TUBULAR; SIN CÁ»
    - B: «LLANTAS FIRESTONE ARGENTINA 205/70R15 TRILLA H/T»
- ≈ MISMA FAMILIA, distinto específico  ·  medida: = {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: = "auto"; tipo_constr: "tubular" ≠ "radial"; camara: falta en B; pliegues: falta en B; huella: falta en B
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 205/70 R15; N° PLIEGUES 10; SEMI PANTANERA; TIPO TUBULAR; SIN CÁ»
    - B: «Llanta para Automotor; Medidas 205/70 R15; Tipo Radial»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  medida: = {"ancho": 185, "perfil": 70, "rin": 13}; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R13; DE CONSTRUCCIÓN RADIAL Y TUBULAR; SIN CÁMARA; SIN PO»
    - B: «LLANTAS HABILEAD CHINA 185/70R13»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  medida: = {"ancho": 185, "perfil": 70, "rin": 14}; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R14; DE CONSTRUCCION RADIAL Y TUBULAR; SIN CAMARA; SIN PO»
    - B: «LLANTAS 185/70R14»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  medida: = {"ancho": 185, "perfil": 70, "rin": 14}; aplicacion: = "auto"; tipo_constr: = "radial"; camara: = "sin_camara"; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R14; DE CONSTRUCCION RADIAL Y TUBULAR; SIN CAMARA; SIN PO»
    - B: «Llanta para Automotor; Medidas 185/70 R14;De construcción radial y tubular; sin Cámara; sin pon»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  medida: = {"ancho": 205, "perfil": 55, "rin": 16}; aplicacion: = "auto"; tipo_constr: = "radial"; camara: falta en B; pliegues: falta en B; huella: falta en B
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 205/55 R16; N°. DE PLIEGUES 8; HUELLA SEMI PANTANERA; TIPO RADIA»
    - B: «Llanta para Automotor; Medidas 205/55 R16; Tipo Radial»
- ✗ DISTINTA SUBFAMILIA  ·  medida: {"ancho": 175, "perfil": 70, "rin": 13} ≠ {"ancho": 185, "perfil": 65, "rin": 14}; aplicacion: = "auto"
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 175/70 R13; HUELLA A; TIPO RADIAL; SIN CAMARA; SIN PONCHILLO»
    - B: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/65 R14 N° PLIEGUES 10; 87H; TIPO TUBULAR; SIN CÁMARA SIN PON»
- ✗ DISTINTA SUBFAMILIA  ·  medida: {"ancho": 175, "perfil": 70, "rin": 13} ≠ {"ancho": 185, "perfil": 70, "rin": 13}; aplicacion: = "auto"
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 175/70 R13; HUELLA A; TIPO RADIAL; SIN CAMARA; SIN PONCHILLO»
    - B: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R13; DE CONSTRUCCIÓN RADIAL Y TUBULAR; SIN CÁMARA; SIN PO»
- ✗ DISTINTA SUBFAMILIA  ·  medida: {"ancho": 175, "perfil": 70, "rin": 13} ≠ {"ancho": 185, "perfil": 70, "rin": 14}; aplicacion: = "auto"
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 175/70 R13; HUELLA A; TIPO RADIAL; SIN CAMARA; SIN PONCHILLO»
    - B: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R14; DE CONSTRUCCION RADIAL Y TUBULAR; SIN CAMARA; SIN PO»
- ✗ DISTINTA SUBFAMILIA  ·  medida: {"ancho": 175, "perfil": 70, "rin": 13} ≠ {"ancho": 195, "perfil": 65, "rin": 15}; aplicacion: = "auto"
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 175/70 R13; HUELLA A; TIPO RADIAL; SIN CAMARA; SIN PONCHILLO»
    - B: «LLANTA PARA AUTOMOTOR; MEDIDAS 195/65 R15; N°. DE PLIEGES 8; HUELLA AUTOPISTA; TIPO RADIAL; SIN»
- ? SUBFAMILIA INSUF (ambiguo)  ·  medida: falta en B; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 175/70 R13; HUELLA A; TIPO RADIAL; SIN CAMARA; SIN PONCHILLO»
    - B: «LLANTAS 2.75/18»
- ? SUBFAMILIA INSUF (ambiguo)  ·  medida: falta en B; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en B; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/65 R14 N° PLIEGUES 10; 87H; TIPO TUBULAR; SIN CÁMARA SIN PON»
    - B: «LLANTAS 2.75/18»
- ? SUBFAMILIA INSUF (ambiguo)  ·  medida: falta en B; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R13; DE CONSTRUCCIÓN RADIAL Y TUBULAR; SIN CÁMARA; SIN PO»
    - B: «LLANTAS 2.75/18»
- ? SUBFAMILIA INSUF (ambiguo)  ·  medida: falta en B; aplicacion: falta en B; tipo_constr: falta en B; camara: falta en B; pliegues: falta en AB; huella: falta en AB
    - A: «LLANTA PARA AUTOMOTOR; MEDIDAS 185/70 R14; DE CONSTRUCCION RADIAL Y TUBULAR; SIN CAMARA; SIN PO»
    - B: «LLANTAS 2.75/18»

### optico
- ✅ MISMO ESPECÍFICO  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: = "+r"; presentacion: = "con_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
- ✅ MISMO ESPECÍFICO  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: = "+r"; presentacion: = "con_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLÁSTICA»
- ✅ MISMO ESPECÍFICO  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: = "+r"; presentacion: = "con_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLÁSTICA.»
- ✅ MISMO ESPECÍFICO  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: = "+r"; presentacion: = "con_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DISCO COMPACTO;CAPACIDAD 4.7 GB; TIPO DVD+R8X; VIRGEN CON CAJA PLASTICA.»
- ≈ MISMA FAMILIA, distinto específico  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: "+r" ≠ "-r"; presentacion: "con_caja" ≠ "sin_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB: TIPO DVD - RX4-VIRGEN SIN CAJA»
- ≈ MISMA FAMILIA, distinto específico  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: "+r" ≠ "-r"; presentacion: "con_caja" ≠ "sin_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD - RX4- VIRGEN SIN CAJA»
- ≈ MISMA FAMILIA, distinto específico  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: = "+r"; presentacion: "con_caja" ≠ "sin_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN SIN CAJA»
- ≈ MISMA FAMILIA, distinto específico  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: "+r" ≠ "-r"; presentacion: "con_caja" ≠ "sin_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «Disco Compacto; Capacidad 4.7 Gb; Tipo Dvd - Rx4 Virgen Sin Caja- HP.»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: = "+r"; presentacion: falta en B
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «DVD+R 8X CAPACIDAD DE 4,7 GB. MAS FUNDA»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: = "r"; grabacion_pol: = "+r"; presentacion: falta en B
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «Disco Compacto; Capacidad 4.7 Gb;Tipo Dvd+r 8x.»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: falta en B; grabacion_pol: falta en B; presentacion: falta en B
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «Dvd de Grabacion; Capacidad 4.7 Gb; Present. Por Unidad»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tipo_medio: = "dvd"; capacidad_gb: = 4.7; tipo_grabacion: falta en B; grabacion_pol: falta en B; presentacion: = "con_caja"
    - A: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
    - B: «Dvd de Grabacion; Capacidad 4.7 Gb; Presentación Por Unidad con Tapa»
- ✗ DISTINTA SUBFAMILIA  ·  tipo_medio: "cd" ≠ "dvd"; capacidad_gb: falta en AB
    - A: «DISCO COMPACTO CD»
    - B: «DISCO COMPACTO DVD»
- ✗ DISTINTA SUBFAMILIA  ·  tipo_medio: "cd" ≠ "dvd"; capacidad_gb: falta en A
    - A: «DISCO COMPACTO CD»
    - B: «DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA»
- ✗ DISTINTA SUBFAMILIA  ·  tipo_medio: "cd" ≠ "dvd"; capacidad_gb: falta en A
    - A: «DISCO COMPACTO CD»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB: TIPO DVD - RX4-VIRGEN SIN CAJA»
- ✗ DISTINTA SUBFAMILIA  ·  tipo_medio: "cd" ≠ "dvd"; capacidad_gb: falta en A
    - A: «DISCO COMPACTO CD»
    - B: «DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD - RX4- VIRGEN SIN CAJA»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tipo_medio: falta en A; capacidad_gb: falta en AB; tipo_grabacion: falta en AB; grabacion_pol: falta en AB; presentacion: falta en AB
    - A: «DISCO COMPACTO»
    - B: «DISCO COMPACTO CD»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tipo_medio: falta en AB; capacidad_gb: falta en AB; tipo_grabacion: falta en AB; grabacion_pol: falta en AB; presentacion: falta en AB
    - A: «DISCO COMPACTO»
    - B: «DISCO COMPACTO DE GRABACION»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tipo_medio: falta en AB; capacidad_gb: falta en A; tipo_grabacion: falta en AB; grabacion_pol: falta en AB; presentacion: falta en AB
    - A: «DISCO COMPACTO»
    - B: «DISCO COMPACTO DE GRABACION CAPACIDAD 4.7 GB»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tipo_medio: falta en A; capacidad_gb: falta en AB; tipo_grabacion: falta en AB; grabacion_pol: falta en AB; presentacion: falta en AB
    - A: «DISCO COMPACTO»
    - B: «DISCO COMPACTO DVD»

### papel_bond
- ✅ MISMO ESPECÍFICO  ·  tamano: = "carta"; gramaje_gm2: = 75; color: = "blanco"
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND BLANCO: TAMAÑO CARTA GRAMAJE 75 GRS. COLOR BLANCO NITIDO; PRESENTACION PAQUETE DE 50»
- ✅ MISMO ESPECÍFICO  ·  tamano: = "carta"; gramaje_gm2: = 75; color: = "blanco"
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND COLOR BLANCO; TAMAÑO CARTA; PAQUETE DE PAPEL DE 500 HOJAS; GRAMAJE: 75 G/M².»
- ✅ MISMO ESPECÍFICO  ·  tamano: = "carta"; gramaje_gm2: = 75; color: = "blanco"
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMANO CARTA; GRAMAJE 75 GRS.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
- ✅ MISMO ESPECÍFICO  ·  tamano: = "carta"; gramaje_gm2: = 75; color: = "blanco"
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO CARTA BLANCO DE 75 GR»
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: falta en B; color: "blanco" ≠ "surtido"
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJAS»
    - B: «PAPEL BOND OFICIO DE COLOR SURTIDO»
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: = 75; color: "blanco" ≠ "surtido"
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO OFICIIO DIFERENTES COLORES DE 75 GR»
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: = 75; color: "blanco" ≠ "surtido"
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO OFICIO 215x330 MM; GRAMAJE 75 GR. DIFERENTE COLORES PRESENTACION EN PAQUETES »
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: = 75; color: "blanco" ≠ "negro"
    - A: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO OFICIO; GRAMAJE 75 GRS.; COLOR SURTIDO; PRESENTACIÓN POR HOJA (SIN NEGRO)»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "carta"; gramaje_gm2: falta en B; color: falta en B
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO CARTA»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "carta"; gramaje_gm2: falta en B; color: falta en B
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO CARTA PAPEL ALCALINO»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "carta"; gramaje_gm2: = 75; color: falta en B
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO CARTA PAPEL ALKALINO DE ALTA BLANCURA 75 G/M2 216 MM X 279 MM PAQUETE DE 500 »
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "carta"; gramaje_gm2: = 75; color: falta en B
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND TAMAÑO CARTA PAPEL ALKALINO DE ALTA BLANCURA 75 g/m2 216 mm x 279 mm pauqtes 500 hoj»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "carta" ≠ "oficio"; gramaje_gm2: = 75
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE 500 HOJAS»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "carta" ≠ "oficio"; gramaje_gm2: = 75
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND BLANCO: TAMAÑO OFICIO GRAMAJE 75 GRS. COLOR BLANCO NITIDO; PRESENTACION PAQUETE DE 5»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "carta" ≠ "oficio"; gramaje_gm2: = 75
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND COLOR BLANCO; TAMAÑO OFICIO; PAQUETE DE PAPEL DE 500 HOJAS; GRAMAJE: 75 G/M² TIPO: O»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "carta" ≠ "oficio"; gramaje_gm2: falta (secundario, no degrada)
    - A: «"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X 500 HOJAS»
    - B: «PAPEL BOND OFICIO DE COLOR SURTIDO»

### papel_continuo
- ✅ MISMO ESPECÍFICO  ·  formato_continuo: = "9.5x11"; partes: = 2; gramaje_gm2: = 56; tipo: = "autocopiativo"
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2 X11X2 PLG, GRAMAJE 56 GRS, PRESENTACION POR CAJAS X 1500 HOJA, TI»
    - B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACION POR CAJAS X 1500 HOJ»
- ✅ MISMO ESPECÍFICO  ·  formato_continuo: = "9.5x11"; partes: = 2; gramaje_gm2: = 56; tipo: = "autocopiativo"
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2 X11X2 PLG, GRAMAJE 56 GRS, PRESENTACION POR CAJAS X 1500 HOJA, TI»
    - B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN CAJA DE 1.500 HOJAS;»
- ✅ MISMO ESPECÍFICO  ·  formato_continuo: = "9.5x11"; partes: = 2; gramaje_gm2: = 56; tipo: = "autocopiativo"
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2 X11X2 PLG, GRAMAJE 56 GRS, PRESENTACION POR CAJAS X 1500 HOJA, TI»
    - B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN POR CAJAS X 1500 HOJ»
- ✅ MISMO ESPECÍFICO  ·  formato_continuo: = "9.5x11"; partes: = 2; gramaje_gm2: = 56; tipo: = "autocopiativo"
    - A: «PAPEL CONTINUO, MEDIDAS 9 1/2 X11X2 PLG, GRAMAJE 56 GRS, PRESENTACION POR CAJAS X 1500 HOJA, TI»
    - B: «PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN POR CAJAS X 1500 HOJ»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  formato_continuo: = "9.5x11"; partes: = 4; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO 9 1/2X11X4»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  formato_continuo: = "9.5x11"; partes: = 4; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO AUTOCOPIATIVO 9.5 X 11 X 4»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  formato_continuo: = "9.5x11"; partes: = 4; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO AUTOCOPIATIVO 9.5 X 11 X 4 TROQUELADO 5 X 5»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  formato_continuo: = "9.5x11"; partes: = 4; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO AUTOCOPIATIVO 9.5X11X4»
- ✗ DISTINTA SUBFAMILIA  ·  formato_continuo: = "9.5x11"; partes: 4 ≠ 3; gramaje_gm2: falta (secundario, no degrada)
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO QUIMICO 9 1/2 X 11 X 3. PRESENTACION CAJA DE 1000 HOJAS»
- ✗ DISTINTA SUBFAMILIA  ·  formato_continuo: = "9.5x11"; partes: 4 ≠ 3; gramaje_gm2: falta (secundario, no degrada)
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO QUIMICO 9 1/2 X 11 X 3; PRESENTACION CAJA DE 1000 HOJAS»
- ✗ DISTINTA SUBFAMILIA  ·  formato_continuo: = "9.5x11"; partes: 4 ≠ 2; gramaje_gm2: falta (secundario, no degrada)
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO QUIMICO 9 1/2 x 11 x 2; PRESENTACION CAJA DE 1500 HOJAS»
- ✗ DISTINTA SUBFAMILIA  ·  formato_continuo: = "9.5x11"; partes: 4 ≠ 3; gramaje_gm2: falta (secundario, no degrada)
    - A: «PAPEL CONTINUO 9 1/2 X 11 X 4»
    - B: «PAPEL CONTINUO QUIMICO 9 1/2 x 11 x 3 x 5.1/2, PRESENTACION CAJA DE 1000 HOJAS»
- ? SUBFAMILIA INSUF (ambiguo)  ·  formato_continuo: falta en A; partes: falta en A; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO»
    - B: «PAPEL CONTINUO 9 1/2 X 11 X 4»
- ? SUBFAMILIA INSUF (ambiguo)  ·  formato_continuo: falta en A; partes: falta en A; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO»
    - B: «PAPEL CONTINUO 9 1/2X11X4»
- ? SUBFAMILIA INSUF (ambiguo)  ·  formato_continuo: falta en A; partes: falta en A; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO»
    - B: «PAPEL CONTINUO AUTOCOPIATIVO 9.5 X 11 X 4»
- ? SUBFAMILIA INSUF (ambiguo)  ·  formato_continuo: falta en A; partes: falta en A; gramaje_gm2: falta en AB; tipo: falta en AB
    - A: «PAPEL CONTINUO»
    - B: «PAPEL CONTINUO AUTOCOPIATIVO 9.5 X 11 X 4 TROQUELADO 5 X 5»

### papel_impreso
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: = 75; color: falta en AB; membrete: "bond consejo magistratura material" ≠ "bond material plena sala"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «HOJA MEMBRETADA SALA PLENA TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IMPRESIÓN FULL COLO»
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: = 75; color: falta en AB; membrete: "bond consejo magistratura material" ≠ "bond material tdj"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «HOJA MEMBRETADA TDJ TAMAÑO OFICIO (21.5X33CM); PAQUETE DE 500 HOJAS IMPRESIÓN FULL COLOR ANVERS»
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: falta en B; color: falta en AB; membrete: "bond consejo magistratura material" ≠ "consejo magistratura"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «PAPEL MEMBRETADO CONSEJO DE LA MAGISTRATURA OFICIO»
- ≈ MISMA FAMILIA, distinto específico  ·  tamano: = "oficio"; gramaje_gm2: falta en B; color: falta en AB; membrete: "bond consejo magistratura material" ≠ "dep justicia tribunal"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «PAPEL MEMBRETADO TRIBUNAL DEP. DE JUSTICIA OFICIO»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "carta"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "presentacion presidencia"
    - A: «PAPEL MEMBRETADO, TAMAÑO CARTA, MEMBRETE PRESIDENCIA; PRESENTACION POR HOJAS»
    - B: «PAPEL MEMBRETADO, TAMAÑO CARTA; MEMBRETE PRESIDENCIA; PRESENTACION POR HOJA»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "oficio"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "departamental justicia presentacion tribunal"
    - A: «PAPEL MEMBRETADO, TAMAÑO OFICIO, MEMBRETE TRIBUNAL DEPARTAMENTAL DE JUSTICIA; PRESENTACION POR »
    - B: «PAPEL MEMBRETADO; TAMAÑO OFICIO; MEMBRETE TRIBUNAL DEPARTAMENTAL DE JUSTICIA; PRESENTACION PAQU»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "oficio"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "departamental justicia presentacion tribunal"
    - A: «PAPEL MEMBRETADO, TAMAÑO OFICIO, MEMBRETE TRIBUNAL DEPARTAMENTAL DE JUSTICIA; PRESENTACION POR »
    - B: «Papel Membretado; Tamaño Oficio; Membrete Tribunal Departamental de Justicia; Presentación paqu»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "carta"; gramaje_gm2: falta en AB; color: falta en AB; membrete: = "daf judicial organo presentacion"
    - A: «PAPEL MEMBRETADO; TAMAÑO CARTA; MEMBRETE ORGANO JUDICIAL - DAF PRESENTACION PAQUETE DE 500 HOJA»
    - B: «Papel Membretado; Tamaño Carta; Membrete Organo Judicial - DAF; Presentación paquete de 500 hoj»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "oficio" ≠ "carta"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «PAPEL MEMBRETADO CONSEJO DE LA MAGISTRATURA CARTA»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "oficio" ≠ "carta"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «PAPEL MEMBRETADO DAF; TAMAÑO CARTA (21.5X28 CM) PAQUETE DE 500 HOJAS IMPRESIÓN FULL COLOR ANVER»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "oficio" ≠ "carta"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «PAPEL MEMBRETADO TRIBUNAL DEP. DE JUSTICIA CARTA»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "oficio" ≠ "carta"
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «PAPEL MEMBRETADO, TAMAÑO CARTA, MEMBRETE PRESIDENCIA; PRESENTACION POR HOJAS»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tamano: falta en B; gramaje_gm2: falta en B; color: falta en AB; membrete: falta en B
    - A: «HOJA MEMBRETADA CONSEJO DE LA MAGISTRATURA, TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IM»
    - B: «Papel Membretado; Trabajo en Tamaño Memorándum»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tamano: falta en B; gramaje_gm2: falta en B; color: falta en AB; membrete: falta en B
    - A: «HOJA MEMBRETADA SALA PLENA TAMAÑO OFICIO (21. X 33CM); PAQUETE DE 500 HOJAS IMPRESIÓN FULL COLO»
    - B: «Papel Membretado; Trabajo en Tamaño Memorándum»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tamano: falta en B; gramaje_gm2: falta en B; color: falta en AB; membrete: falta en B
    - A: «HOJA MEMBRETADA TDJ TAMAÑO OFICIO (21.5X33CM); PAQUETE DE 500 HOJAS IMPRESIÓN FULL COLOR ANVERS»
    - B: «Papel Membretado; Trabajo en Tamaño Memorándum»
- ? SUBFAMILIA INSUF (ambiguo)  ·  tamano: falta en B; gramaje_gm2: falta en AB; color: falta en AB; membrete: falta en B
    - A: «PAPEL MEMBRETADO CONSEJO DE LA MAGISTRATURA CARTA»
    - B: «Papel Membretado; Trabajo en Tamaño Memorándum»

### ram
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  generacion: = "ddr3"; capacidad_gb: = 8.0; frecuencia_mhz: falta en B; formato: falta en AB
    - A: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM DDR3 DE 8GB /FREC 1600 P/»
    - B: «MEMORIA RAM; TIPO DE MEMORIA RAM DDR3; TIPO DE RAM 8 GB»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  generacion: = "ddr3"; capacidad_gb: = 8.0; frecuencia_mhz: falta en B; formato: falta en AB
    - A: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM DDR3 DE 8GB /FREC 1600 P/»
    - B: «MEMORIA RAM; TIPO DE MEMORIA RAM DDR3; TIPO DE RAM 8 GB (TIPO I - PARA PC)»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  generacion: = "ddr3"; capacidad_gb: = 8.0; frecuencia_mhz: falta en B; formato: falta en AB
    - A: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM DDR3 DE 8GB /FREC 1600 P/»
    - B: «MEMORIAS RAM DDR3 8GB»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  generacion: = "ddr3"; capacidad_gb: = 8.0; frecuencia_mhz: falta en B; formato: falta en AB
    - A: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM DDR3 DE 8GB /FREC 1600 P/»
    - B: «Memoria RAM; Tipo de Memoria RAM Ddr3; Capacidad 8 Gb.»
- ✗ DISTINTA SUBFAMILIA  ·  generacion: falta en A; capacidad_gb: 8.0 ≠ 2.0
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM DDR2 DE 2GB / FREC 800 P/»
- ✗ DISTINTA SUBFAMILIA  ·  generacion: falta en A; capacidad_gb: 8.0 ≠ 16.0
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «MEMORIA RAM 16 GB PC3»
- ✗ DISTINTA SUBFAMILIA  ·  generacion: falta en A; capacidad_gb: 8.0 ≠ 4.0
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «MEMORIA RAM DDR3 4GB 1333 MHZ PARA PC»
- ✗ DISTINTA SUBFAMILIA  ·  generacion: falta en A; capacidad_gb: 8.0 ≠ 4.0
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «MEMORIAS RAM DDR3 4GB»
- ? SUBFAMILIA INSUF (ambiguo)  ·  generacion: falta en A; capacidad_gb: = 8.0; frecuencia_mhz: falta en A; formato: falta en AB
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM DDR3 DE 8GB /FREC 1600 P/»
- ? SUBFAMILIA INSUF (ambiguo)  ·  generacion: falta en A; capacidad_gb: = 8.0; frecuencia_mhz: falta en A; formato: falta en AB
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «ACCESORIO PARA EQUIPO DE COMPUTACIÓN; TIPO MEMORIA RAM. - MEMORIA RAM DDR4 DE 8GB /FREC 3200 P/»
- ? SUBFAMILIA INSUF (ambiguo)  ·  generacion: falta en A; capacidad_gb: = 8.0; frecuencia_mhz: falta en AB; formato: falta en AB
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «Accesorio para Computador Memoria Ram DDR4 PC4 3200 Capacidad 8 GB»
- ? SUBFAMILIA INSUF (ambiguo)  ·  generacion: falta en A; capacidad_gb: = 8.0; frecuencia_mhz: falta en A; formato: falta en AB
    - A: «? Memoria RAM: 8 GB, instalado en un solo slot. Expandible hasta 16 GB como mínimo»
    - B: «MEMORIA RAM DDR4 8 GB 3200 MHZ PARA PC»

### sobre_manila
- ✅ MISMO ESPECÍFICO  ·  tamano: = "medio oficio"; gramaje_gm2: = 90; color: = "cafe"
    - A: «SOBRE MANILA; TAMAÑO 1/2 OFICIO FORMATO COLOR CAFE 90 GRS»
    - B: «SOBRE MANILA; TAMAÑO 1/2 OFICIO; FORMATO COLOR CAFE 90 GRS.»
- ✅ MISMO ESPECÍFICO  ·  tamano: = "carta"; gramaje_gm2: = 90; color: = "cafe"
    - A: «SOBRE MANILA; TAMAÑO CARTA FORMATO COLOR CAFE 90 GRS COLOR MADERA»
    - B: «SOBRE MANILA;TAMAÑO CARTA FORMATO COLOR CAFE 90GRS.»
- ✅ MISMO ESPECÍFICO  ·  tamano: = "doble carta"; gramaje_gm2: = 90; color: = "cafe"
    - A: «SOBRE MANILA; TAMAÑO DOBLE CARTA FORMATO COLOR CAFE 90 GRS COLOR MADERA»
    - B: «SOBRE MANILA; TAMAÑO DOBLE CARTA; FORMATO COLOR CAFE 90 GRS. COLOR MADERA.»
- ✅ MISMO ESPECÍFICO  ·  tamano: = "doble oficio"; gramaje_gm2: = 90; color: = "cafe"
    - A: «SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90 GRS.»
    - B: «SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90 GRS. COLOR MADERA.»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "doble oficio"; gramaje_gm2: falta en AB; color: falta en AB
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA DOBLE OFICIO»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "doble oficio"; gramaje_gm2: falta en A; color: falta en A
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90 GRS.»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "doble oficio"; gramaje_gm2: falta en A; color: falta en A
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90 GRS. COLOR MADERA.»
- ≈ MISMA SUBFAMILIA, específico INSUF  ·  tamano: = "doble oficio"; gramaje_gm2: falta en A; color: falta en A
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90GRS»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "doble oficio" ≠ "oficio"
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA / OFICIO»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "doble oficio" ≠ "carta"
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA CARTA»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "doble oficio" ≠ "oficio"
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA OFICIO»
- ✗ DISTINTA SUBFAMILIA  ·  tamano: "doble oficio" ≠ "medio carta"
    - A: «SOBRE MANILA / DOBLE OFICIO»
    - B: «SOBRE MANILA; TAMAÑO 1/2 CARTA FORMATO COLOR CAFE 90 GRS»

## Validación cruzada sobre la muestra v2 CONGELADA (ilustrativa, no ajuste)

Pares capturados: 19. (MISMA_FAMILIA humano ↔ FAMILIA_AMPLIA=SI; SUBFAMILIA es corte más fino.)
| par | cat | humano (v2) | AMPLIA | SUBFAMILIA | ESPECÍFICO | razón subfamilia |
|---|---|---|---|---|---|---|
| X002 | ram | MISMA_FAMILIA | SI | SI | INSUF | generacion: = "ddr4"; capacidad_gb: = 8.0 |
| X003 | llanta | MISMA_FAMILIA | SI | NO | NO | medida: {"ancho": 195, "perfil": 65, "rin": 15} ≠ {"ancho": 265, "perfil": 75, "rin": 16}; aplicacion: = "auto" |
| X005 | almacenamiento | MISMO_ESPECIFICO | SI | SI | INSUF | tecnologia: = "ssd"; capacidad_gb: = 512.0 |
| X006 | almacenamiento | MISMA_FAMILIA | SI | NO | NO | tecnologia: = "ssd"; capacidad_gb: 512.0 ≠ 480.0 |
| X007 | sobre_manila | MISMA_FAMILIA | SI | NO | NO | tamano: "doble oficio" ≠ "carta" |
| X008 | llanta | MISMA_FAMILIA | SI | NO | NO | medida: {"ancho": 215, "perfil": 65, "rin": 16} ≠ {"ancho": 265, "perfil": 75, "rin": 16}; aplicacion: = "auto" |
| X010 | papel_continuo | MISMO_ESPECIFICO | SI | SI | SI | formato_continuo: = "9.5x11"; partes: = 3; gramaje_gm2: = 56 |
| X013 | papel_bond | MISMA_FAMILIA | SI | NO | NO | tamano: "oficio" ≠ "carta"; gramaje_gm2: = 75 |
| X016 | llanta | MISMA_FAMILIA | SI | NO | NO | medida: {"ancho": 185, "perfil": 70, "rin": 14} ≠ {"ancho": 195, "perfil": 65, "rin": 15}; aplicacion: = "auto" |
| X017 | llanta | MISMA_FAMILIA | SI | NO | NO | medida: {"ancho": 215, "perfil": 65, "rin": 16} ≠ {"ancho": 205, "perfil": 70, "rin": 15}; aplicacion: = "auto" |
| X018 | sobre_manila | MISMO_ESPECIFICO | SI | SI | INSUF | tamano: = "oficio" |
| X020 | ram | MISMO_ESPECIFICO | SI | SI | INSUF | generacion: = "ddr4"; capacidad_gb: = 8.0 |
| X023 | ram | MISMA_FAMILIA | SI | SI | INSUF | generacion: = "ddr3"; capacidad_gb: = 4.0 |
| X025 | llanta | MISMA_FAMILIA | SI | NO | NO | medida: {"ancho": 205, "perfil": 55, "rin": 16} ≠ {"ancho": 265, "perfil": 75, "rin": 16}; aplicacion: = "auto" |
| X031 | ram | MISMA_FAMILIA | SI | NO | NO | generacion: "ddr4" ≠ "ddr3"; capacidad_gb: = 8.0 |
| X034 | almacenamiento | MISMO_ESPECIFICO | SI | INSUF | INSUF | tecnologia: falta en AB; capacidad_gb: = 1000.0 |
| X035 | llanta | MISMA_FAMILIA | SI | NO | NO | medida: {"ancho": 205, "perfil": 55, "rin": 16} ≠ {"ancho": 265, "perfil": 75, "rin": 16}; aplicacion: = "auto" |
| X036 | ram | MISMA_FAMILIA | SI | INSUF | INSUF | generacion: = "ddr4"; capacidad_gb: falta en B |
| X039 | sobre_manila | MISMA_FAMILIA | SI | NO | NO | tamano: "carta" ≠ "doble oficio" |

## Pendientes documentados (no resueltos aquí)
- **RAM instalada en equipo** («? Memoria RAM 8GB instalado en un solo slot, expandible…»): 1 sola descripción en el corpus (AISLADO) → no se toca el extractor congelado por un caso; una regla general podría descartar módulos reales. Pendiente de refinamiento del extractor.
- La firma de membrete es heurística (tokens institucionales); puede marcar NO entre fraseos distintos de la misma institución. Conservador (evita fusión falsa), a validar con humano.
- Precisión real del verificador: PENDIENTE de muestra NUEVA estratificada por categoría Y veredicto, etiquetada por separado a los 3 niveles, con falsos+/falsos−/INSUF separando error de extractor / blocker / verificador. NO implementar agrupación ni agregación hasta entonces.