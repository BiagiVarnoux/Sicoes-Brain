# Auditoría de conteos — papel_bond ESP=SI (SOLO LECTURA)

Pedida para establecer el volumen REAL de observaciones independientes detrás de los 474 pares ESP=SI de
papel_bond. No cambia reglas, extractor ni muestras. Verificador congelado.

## Resultado
- **Pares ESP=SI (papel_bond): 474**
- **Descripciones únicas que participan: 67** (cada par usa 2; muchas descripciones se repiten en muchos pares)
- **Variantes distintas (tamaño, gramaje, color, empaque): 5**
- **Componentes conexos (clústeres implícitos de equivalencia): 9**; tamaños: 22, 21, 5, 4, 4, 4, 3, 2, 2 descripciones.
  - El mayor componente concentra **231 de los 474 pares** sobre solo **22 descripciones**.

### Distribución por variante
| tamaño | gramaje | color | descripciones |
|---|---|---|---|
| oficio | 75 | blanco | 31 |
| carta | 75 | blanco | 27 |
| oficio | 75 | surtido | 4 |
| oficio | 75-80 | surtido | 3 |
| carta | 75-80 | surtido | 2 |

## Lectura (confirma la precaución estadística)
- Los 474 pares **NO son 474 observaciones independientes.** Se reducen a ~67 descripciones, ~9 clústeres
  y apenas **5 variantes reales**, dominadas por "oficio/carta 75g blanco" (58 de 67 descripciones).
- Los errores estarían **correlacionados**: un acierto/error sobre "oficio 75 blanco" se repite en decenas
  de pares del mismo clúster. Contar pares infla artificialmente el tamaño muestral.
- **Conclusión:** el volumen efectivo de papel_bond para una validación estadística defendible es **pequeño**
  (≈5 variantes / 9 clústeres / 67 descripciones), no 474. Ni siquiera papel_bond alcanza hoy un n
  independiente cercano a 150. La unidad de validación debe ser la **descripción única / variante / clúster**,
  no el par.
- Implicación de diseño: para sostener un 98% defendible harían falta **más descripciones distintas** (datos
  históricos nuevos con mayor diversidad de tamaño/gramaje/color/presentación), no más pares del mismo puñado
  de variantes. Esto se traslada a los criterios de aceptación.
