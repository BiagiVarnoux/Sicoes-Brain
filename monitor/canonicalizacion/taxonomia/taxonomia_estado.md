# Frente 1 — Estado y consolidación de la taxonomía LLM

_Generado 2026-11-07T23:09:31. Solo lectura, sin API._

## Cobertura (corpus vivo vs checkpoint)
- Corpus: **5067** descripciones `cuerpo` distintas (4423 normalizadas).
- Etiquetas válidas (con `desc`): **4896** · sin `desc`: 0 · duplicadas colapsadas: 473.
- Descripciones únicas etiquetadas: **4423**.
- Cobertura del corpus: **4423/4423 (100%)**.
- Pendientes (sin etiqueta): **0** → `taxonomia_pendientes.json`.
- Etiquetas huérfanas (ya no en el corpus): 0.

## Consolidación de categorías (determinista)
- Categorías crudas: **585** → consolidadas: **572** (reducción 3%).
- Método: normalización de mayúsculas/tildes + plurales inequívocos + mapa curado. **No** se fusionaron hojas (productos) por parecido de nombre.

## Top 25 categorías consolidadas (por nº de hojas distintas)
| categoría | subcategorías | hojas | descripciones |
|---|---|---|---|
| Tóner | 8 | 209 | 429 |
| Tóner y cartuchos | 15 | 191 | 303 |
| Fusores | 2 | 52 | 69 |
| Cartuchos de tinta | 2 | 47 | 135 |
| Repuestos automotrices | 1 | 40 | 40 |
| Marcadores | 9 | 40 | 72 |
| Tambores | 5 | 39 | 76 |
| Bolígrafos | 6 | 38 | 62 |
| Escritorios | 2 | 35 | 35 |
| Muebles de oficina | 4 | 32 | 32 |
| Tinta para impresora | 8 | 32 | 35 |
| Papel continuo | 10 | 29 | 60 |
| Silla de oficina | 1 | 29 | 44 |
| Aire acondicionado - Repuestos | 7 | 25 | 40 |
| Llantas para automóviles o camionetas | 1 | 25 | 29 |
| Discos ópticos | 17 | 22 | 28 |
| Tijeras | 3 | 20 | 29 |
| Folders | 8 | 19 | 52 |
| Papel | 9 | 19 | 69 |
| Consumibles para impresoras | 5 | 19 | 23 |
| Escáneres | 5 | 18 | 19 |
| Luminaria LED | 4 | 18 | 19 |
| Ambientadores | 14 | 17 | 27 |
| Impresoras láser | 10 | 17 | 23 |
| Mesas | 10 | 17 | 18 |

## Nota
Los pendientes son, en su mayoría, consumibles de impresión que YA están modelados por el motor por código (canonicalizacion/impresion). La taxonomía LLM es un MAPA DE PRIORIZACIÓN, no una fuente de fusiones confirmadas.