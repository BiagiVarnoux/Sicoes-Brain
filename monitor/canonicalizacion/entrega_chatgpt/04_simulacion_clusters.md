# Etapa 4 — Simulación de agrupación (READ-ONLY, NO escribe en BD)

Clústeres = clique completo de ESP=SI sin NO interno; ambiguos/no-clique → revisión; INSUF/NO_EVALUADO → candidato. No asigna producto_canonico_id, no agrega montos.

Universo: 5067 descripciones únicas; 340 participan en pares candidatos; 9,828 pares.

## Resultado global
- **Clústeres confirmados (clique único): 28**, cubren 129 descripciones.
- **Componentes en revisión (no-clique / ambiguos): 1**, cubren 8 descripciones.
- **Descripciones candidatas (singleton / INSUF / NO_EVALUADO): 203**.
- Tamaños de clúster confirmados (mayores): [22, 21, 9, 6, 5, 5, 5, 4, 4, 4, 4, 4, 4, 3, 3]

## Clústeres confirmados por categoría
| categoría | clústeres | descripciones |
|---|---|---|
| papel_bond | 9 | 67 |
| sobre_manila | 5 | 14 |
| papel_continuo | 5 | 23 |
| papel_impreso | 4 | 9 |
| optico | 3 | 12 |
| llanta | 2 | 4 |

## Invariantes verificables
| # | invariante | resultado |
|---|---|---|
| 1_sin_NO_interno | | ✅ OK |
| 2_clique_completo | | ✅ OK |
| 3_anti_transitividad | | ✅ OK |
| 4_unicidad | | ✅ OK |
| 5_insuf_noeval_no_fusionan | | ✅ OK |
| 6_conservacion | | ✅ OK |
| 7_sin_escritura | | ✅ OK |
| 8_reproducible | | ✅ OK |

## Ejemplos de clústeres confirmados (hasta 8)
- **[papel_bond] clúster de 22** — exemplar: `PAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75 GRS M2.; COLOR BLANCO; PRESENTACIÓN PAQUET`
    - `PAPEL BOND ; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE D`
    - `PAPEL BOND BLANCO: TAMAÑO OFICIO GRAMAJE 75 GRS. COLOR BLANCO NITIDO; PRESENTACI`
    - `PAPEL BOND COLOR BLANCO; TAMAÑO OFICIO; PAQUETE DE PAPEL DE 500 HOJAS; GRAMAJE: `
    - `PAPEL BOND TAMANO OFICIO; GRAMAJE 75 GRS.; COLOR BLANCO; PRESENTACION PAQUETE DE`
    - … (+17 más)
- **[papel_bond] clúster de 21** — exemplar: `PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 GRS M2.; COLOR BLANCO; PRESENTACIÓN PAQUETE`
    - `"PAPEL BOND; TAMAÑO CARTA; GRAMAJE 75 Grs.; COLOR BLANCO; PRESENTACION PAQUETE X`
    - `PAPEL BOND BLANCO: TAMAÑO CARTA GRAMAJE 75 GRS. COLOR BLANCO NITIDO; PRESENTACIO`
    - `PAPEL BOND COLOR BLANCO; TAMAÑO CARTA; PAQUETE DE PAPEL DE 500 HOJAS; GRAMAJE: 7`
    - `PAPEL BOND TAMANO CARTA; GRAMAJE 75 GRS.; COLOR BLANCO; PRESENTACION PAQUETE X 5`
    - … (+16 más)
- **[papel_continuo] clúster de 9** — exemplar: `PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN CAJA `
    - `PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACION POR C`
    - `PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 2 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN POR C`
    - `PAPEL CONTINUO; MEDIDAS 9 1/2*11*2 PLG.; GRAMAJE 56 GRS.; PRESENTACION CAJA DE 1`
    - … (+4 más)
- **[optico] clúster de 6** — exemplar: `DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLÁSTICA.`
    - `DISCO COMPACTO: CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA`
    - `DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLASTICA`
    - `DISCO COMPACTO; CAPACIDAD 4.7 GB; TIPO DVD+R 8X; VIRGEN CON CAJA PLÁSTICA`
    - … (+1 más)
- **[papel_bond] clúster de 5** — exemplar: `PAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75 GRS; COLOR BLANCO; PRESENTACION PAQUETE DE`
    - `PAPEL BOND; TAMAÑO OFICIO; GRAMAJE 75G/M-20 LB .; COLOR BLANCO; ISO 9706 PRESENT`
    - `Papel Bond; Tamaño Oficio; Gramaje 75 Grs.; Color Blanco; Presentación Paquete d`
    - `Papel bond, tamaño oficio, gramaje 75 grs, color blanco, presentación paquete de`
- **[papel_continuo] clúster de 5** — exemplar: `Papel Continuo; Medidas 9 1/2 x 11 x 3 Plg.; Gramaje 56 Grs.; Presentación caja `
    - `PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 3 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN CAJA `
    - `PAPEL CONTINUO; MEDIDAS 9 1/2*11*3 PLG.; GRAMAJE 56 GRS.; PRESENTACION CAJA * 10`
    - `PAPEL CONTINUO; MEDIDAS 9 1/2*11*3 PLG.; GRAMAJE 56 GRS.; PRESENTACION CAJA DE 1`
- **[papel_continuo] clúster de 5** — exemplar: `PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 4 X 5.5; GRAMAJE 56 GRS; PRESENTACION CAJA `
    - `PAPEL CONTINUO, MEDIDAS 9 1/2X11X4X5.5, GRAMAJE 56 GRS, PRESENTACION CAJA X 750 `
    - `PAPEL CONTINUO; MEDIDAS 9 1/2 X 11 X 4 X 5.5 PLG.; GRAMAJE 56 GRS.; PRESENTACIÓN`
    - `Papel Continuo; Medidas 9 1/2 X11x4x5.5; Gramaje 56 Grs.; Presentación Caja x 75`
- **[sobre_manila] clúster de 4** — exemplar: `SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90 GRS. COLOR MADERA.`
    - `SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90 GRS.`
    - `SOBRE MANILA; TAMAÑO DOBLE OFICIO; FORMATO COLOR CAFE 90GRS`
    - `SOBRE MANILA; TAMAÑO DOBLE OFICIO;FORMATO COLOR CAFE 90 GRS`

## Componentes en REVISIÓN (no se auto-asignan) — hasta 10
- **[papel_continuo] componente de 8 — AMBIGUO (nodo en >1 clique)**; 2 cliques maximales alternativos, tamaños [6, 3]