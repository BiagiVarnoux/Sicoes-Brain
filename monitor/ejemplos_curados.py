"""
Ejemplos curados de entrenamiento (few-shot) — camino 1
=======================================================
Casos reales que el usuario SÍ quiere que entren, elegidos a mano. Se suman a
los ejemplos que `db.ejemplos_entrenamiento()` saca de la tabla
`convocatorias_radar` (sus decisiones en vivo), y van PRIMERO porque son "gold".

El clasificador IA solo muestra los primeros ~8 positivos en el prompt, así que
el ORDEN importa: arriba van los de TÍTULO GENÉRICO ("Adquisición de Papel",
"Papel (Varios)", "Material de Escritorio"), que son los que el diccionario NO
puede cazar y donde la IA de verdad necesita el criterio. Los de etiqueta /
Brother / tóner explícitos ya los resuelve el diccionario; van al final solo
como refuerzo.

Contexto del rubro: el usuario provee etiquetas autoadhesivas / rollos de papel
térmico continuo (Brother DK-2205, 62 mm) e insumos de impresión. Las entidades
judiciales (TDJ / Órgano Judicial / Tribunal Departamental) y fiscalías compran
ese material muchas veces bajo el título genérico "Papel" o "Material de
Escritorio", con el producto real dentro del lote.

OJO (precisión): enseñarle a la IA que "Adquisición de Papel" puede ser
relevante sube la cobertura pero también deja pasar compras de papel bond de
oficina ajenas. Es el costo esperado del camino 1; se compensa descartando en el
dashboard (eso alimenta los negativos de `db.ejemplos_entrenamiento`).
"""

# Positivos curados (orden = prioridad en el few-shot).
POSITIVOS: list[str] = [
    # --- Título genérico "Papel" (solo la IA puede cazarlos) ---
    "Adquisición de Papel para el Órgano Judicial de Tarija, Primer Cuatrimestre Gestión 2026",
    "Adquisición de Papel (Papel Continuo Químico Blanco 9.5x11x3 y Papel Autoadhesivo 62mm x 30.48 m) para Stock de Almacén del TDJ de Chuquisaca",
    "1ra Adquisición de Papel Bond y Papel (Varios) para Stock de Almacén del TDJ de Chuquisaca",
    "1ra Adquisición de Papel (Varios), para Stock de Almacén del TDJ de Chuquisaca",
    "Adquisición Papel, Primer Cuatrimestre",
    # --- Material de escritorio / artes gráficas con etiquetas en el lote ---
    "Compra de Etiquetas Continuas Autoadhesivas y Material de Escritorio para el Órgano Judicial – Distrito Potosí",
    "Adquisición de Materiales de Escritorio, Limpieza y Productos de Artes Gráficas para el Órgano Judicial de Potosí",
    # --- Insumos / impresoras Brother (refuerzo; el diccionario ya ayuda) ---
    "Adquisición de Insumos para Impresoras Brother del Órgano Judicial de Tarija",
    "Adquisición de Tóners HP, Brother y Lexmark para las Impresoras del Órgano Judicial de Potosí Gestión 2025",
    # --- Etiqueta continua / DK-2205 explícito (refuerzo) ---
    "Adquisición de Etiqueta Continua Autoadhesiva para Impresora Brother a DK 2205:62 mm x 30.4 mts",
    "Adquisición de Rollos de Papel Térmico Continuo de Medida 62x8mm Dk-2205 para Stock de Almacén de la Fiscalía Departamental de La Paz",
    "Adquisición de Etiqueta Continua Autoadhesiva para el Órgano Judicial Gestión 2025",
]

# Negativos curados: por ahora vacío — los negativos salen de los descartes
# reales del usuario en el dashboard (motivo 'producto').
NEGATIVOS: list[str] = []
