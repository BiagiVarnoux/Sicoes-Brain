# Subauditoría de extracción — atributos primarios ausentes (SOLO LECTURA)

No modifica extractor ni verificador. Cuenta DESCRIPCIONES ÚNICAS (no pares) sin el atributo primario, y revisa el texto crudo para separar ausencia real de fallo de extracción.

## papel_continuo — falta `formato_continuo` en 4 descripciones únicas
- AUSENCIA_REAL (texto no trae el patrón): **2**
- FALLO_EXTRACTOR (forma canónica presente, no extraída): **0**  ← bug si >0
- NO_MODELADO (trae medida en formato no soportado): **2**  ← brecha de cobertura

  Ejemplos de NO_MODELADO (trazables, hasta 12):
  - `PAPEL CONTINUO TROQUELADO QUIMICO CORTE MICROLATERAL 3 x 90`
  - `Papel Continuo; 9 1/2 x 5 1/2 4; Gramaje 56 Grs.; Caja x 1000 Hojas; Tipo de Papel Químico`

  Ejemplos de AUSENCIA_REAL (hasta 6):
  - `PAPEL CONTINUO`
  - `PAPEL CONTINUO TROQUELADO`

## llanta — falta `medida` en 5 descripciones únicas
- AUSENCIA_REAL (texto no trae el patrón): **4**
- FALLO_EXTRACTOR (forma canónica presente, no extraída): **0**  ← bug si >0
- NO_MODELADO (trae medida en formato no soportado): **1**  ← brecha de cobertura

  Ejemplos de NO_MODELADO (trazables, hasta 12):
  - `LLANTAS 2.75/18`

  Ejemplos de AUSENCIA_REAL (hasta 6):
  - `Llantas Delanteras Moto Honda`
  - `Llantas Delanteras Moto Serna`
  - `Llantas Traseras Moto Honda`
  - `Llantas Traseras Moto Serna`

## Conclusión
- **0 FALLO_EXTRACTOR**: no hay pérdida silenciosa de `formato_continuo` ni `medida` en su forma modelada.
  La insuficiencia NO proviene de un bug del extractor sobre atributos primarios.
- **3 descripciones NO_MODELADO** (brecha de cobertura, no error): continuo 9½×**5½** y "3×90"
  (microlateral/troquelado); llanta de **moto en pulgadas** `2.75/18`. El extractor modela continuo 9½×11
  y medida métrica de auto; estos formatos quedan fuera. Son casos raros y de otra sub-familia física.
- **Ausencia real**: `PAPEL CONTINUO` a secas, y motos descritas por posición ("Llantas Delanteras Moto
  Honda") sin medida. El verificador acierta al dejarlas INSUF (no hay evidencia para confirmar identidad).
- **Efecto multiplicador (lo que advirtió ChatGPT):** esas 4 descripciones de continuo sin `formato`
  tocan **239 pares** que quedan INSUF. Pocas descripciones incompletas generan muchos pares INSUF — por eso
  los 2.699 ESP=INSUF NO son 2.699 problemas independientes. La métrica correcta es por descripción, no por par.

### Recomendación (sin implementar)
Opcional y de bajo impacto: modelar el continuo 9½×5½ y la medida de moto en pulgadas (2.75/18) ampliaría
cobertura en ~3 descripciones. No es prioritario ni afecta la correctitud actual (hoy quedan INSUF, que es
el veredicto conservador correcto). No tocar el extractor por ahora, conforme a la instrucción.
