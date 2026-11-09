# Plan de inteligencia de mercado SICOES-BRAIN

## Objetivo y principios

Producir inteligencia de mercado sobre demanda por producto, cantidades, precios,
recurrencia, entidades, proveedores y oportunidades de abastecimiento.

Conservar originales inmutables, observaciones y resultados inferidos por
separado. Registrar fuente, hash, posición, regla/modelo y versión. Una asociación
DBC no es equivalencia de productos. Un grupo provisional no es una asignación
confirmada. No usar 2022 para ajustar los algoritmos de canonicalización.

## 1. Extracción documental

Capturar formularios, DBC y adjuntos con versiones, intentos, hashes e inventario
de cobertura. Distinguir ausencia local, no publicación, captura fallida y vacío
explícito. Conservar navegación y recuperación de sesión, así como la descarga
sin ventana. Sin OCR de ofertas en el alcance actual.

Publicación progresiva: cobertura y disponibilidad documental por entidad,
gestión y CUCE; sin métricas comerciales inferidas de documentos no interpretados.

## 2. Estructuración de observaciones

Extraer por documento, sección, tabla, fila y etapa. Conservar originales,
normalizaciones y cálculos separados. Auditar filas omitidas y encabezados
desconocidos. FORM 600 solo inventariado y 100-E excluido hasta alcance aprobado.

Publicación progresiva: observaciones y cantidades/precios por etapa, con calidad
y procedencia. Nunca sumar requerimiento, adjudicación, contratación y recepción
como demanda adicional. La demanda original no se presenta como demanda neta.

## 3. Extracción de atributos y enriquecimiento documental

Extraer atributos con evidencia literal y operadores: exacto, mínimo, máximo,
rango, alternativa, prohibido y desconocido. Vincular DBC bajo reglas auditables;
los ambiguos no completan hechos confirmados. Distinguir requisitos publicados
de características comprobadas de lo adjudicado o recibido.

Publicación progresiva: filtros técnicos y fichas enriquecidas, señalando origen
y estado documental. No aumentar cantidades por añadir atributos DBC.

## 4. Generación de candidatos

Proponer pares por familia, códigos, atributos y texto. Registrar por qué se
propone cada par. Igual UNSPSC o compatibilidad con una impresora no prueba
identidad. Evaluar omisiones fuera del generador y separar regresión de prueba
independiente.

Publicación progresiva: candidatos para revisión; no agregarlos como productos
confirmados ni reemplazar métricas vigentes con ellos.

## 5. Evaluación de equivalencia mediante reglas y LLM

Evaluar familia, subfamilia e identidad específica separadamente. Permitir SI,
NO e INSUFICIENTE con evidencia. Usar LLM solo bajo contrato, presupuesto y
autorización; registrar prompt, modelo, respuesta y consumo reales. No completar
ausencias por supuestos ni usar las respuestas del modelo como verdad de prueba.

Publicación progresiva: veredictos y pendientes con evidencia, revisión y versión.
No convertir una recomendación LLM en asignación confirmada automáticamente.

## 6. Agrupación canónica

Construir grupos respaldados, conservando miembros, conflictos y versión.
No asumir transitividad por una cadena de pares positivos. Separar provisional,
confirmado y pendiente; las asignaciones deben ser reversibles y nunca reemplazar
las observaciones originales.

Publicación progresiva: demanda y recurrencia por producto canónico, entidades,
proveedores y oportunidades inferidas. Agregar solo unidades y monedas
compatibles. Los desconocidos permanecen desconocidos, no cero.

## Publicación y prevención de doble conteo

El dashboard actual usa hist_* y un overlay de canónicos provisionales; no tiene
un importador validado para las nuevas observaciones. Su colapso actual por
(CUCE,nro_item,lote) no prueba correspondencia entre las fases del corpus nuevo.

La publicación futura requiere una entrega separada: dataset de preparación,
asociaciones entre fases con evidencia o abstención, comparación con la versión
vigente y cambio reversible de la versión consultada. Nunca insertar las cuatro
etapas en hist_items esperando que las vistas actuales eviten el doble conteo.

Separar métricas referenciales, adjudicadas, contratadas y recibidas. Definir qué
etapa alimenta cada indicador y mantener su fecha/semántica. No estimar demanda
neta sin interpretar anulaciones. Identificar oportunidades y proyecciones como
inferencias con cobertura y limitaciones, no hechos originales.


## Estado de integración

La incorporación de código no publica datos. El dashboard, Supabase y los algoritmos existentes permanecen intactos. Datos históricos y sesiones Brave se migrarán en una segunda fase autorizada.
