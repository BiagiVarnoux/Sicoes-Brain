# Radar de Convocatorias SICOES

Revisa el SICOES **por rango de fechas de publicación** y detecta oportunidades
abiertas de los rubros del usuario (**computación + etiquetas autoadhesivas**),
descarga sus **DBC** y las guarda en Supabase para verlas en el dashboard.

Es un módulo **nuevo e independiente** del scraper histórico (`../scraper/`).
No toca las tablas `procesos` / `items`; usa su propia tabla `convocatorias_radar`.

## Cómo funciona

1. **Buscar** en el buscador avanzado por `publicacionDesde`/`publicacionHasta`,
   tipo Bienes, estado Vigente. Recorre todas las páginas de resultados.
2. **Pre-filtrar local** (porque SICOES a veces ignora los filtros):
   - Tipo = Bienes
   - Modalidad ∈ {CM, LP, ANPE, ANPP}
   - Estado = Vigente
   - Fecha de presentación ≥ hoy (sigue abierta)
3. **Clasificar por rubro con doble filtro (OR):**
   - **A — Diccionario** (`rubros.py`): términos conocidos en el objeto.
   - **B — IA (Groq)** (`clasificador_ia.py`): analiza el objeto semánticamente.
   - `relevante = A or B`. Se guardan los dos veredictos por separado.
4. **Descargar el documento objetivo** de cada relevante (UNO solo):
   ANPE/ANPP/LP → "Documento Base de Contratación"; CM → "Oferta del Proveedor".
   Se guarda en **ambos formatos**: el Word original (`.docx`) y el PDF convertido
   con LibreOffice (`DBC - <cuce4>.docx` + `DBC - <cuce4>.pdf`; prefijo `CM` para CM).
   Se suben al bucket público `dbc` de Supabase Storage.
5. **Guardar** todas las candidatas en Supabase (`convocatorias_radar`).
6. **Exportar** `salidas/objetos_<fecha>.csv` con todos los objetos y sus
   veredictos → sirve para **refinar el diccionario** (`rubros.py`).

## Correr

```bash
# 1. Cerrar Chrome del todo y abrirlo con debugging:
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir="/tmp/chrome-sicoes"

# 2. Entrar a https://www.sicoes.gob.bo/portal/index.php (cerrar el popup)

# 3. Correr el radar (usa el venv del scraper, ya tiene playwright):
../scraper/venv/bin/python radar.py --desde 01/10/2026
```

Opciones:

| flag | default | qué hace |
|------|---------|----------|
| `--desde dd/mm/yyyy` | hace 7 días | fecha publicación desde |
| `--hasta dd/mm/yyyy` | hoy | fecha publicación hasta |
| `--max-paginas N` | 0 (todas) | límite de páginas |
| `--no-ia` | — | solo diccionario (sin Groq) |
| `--no-descargar` | — | no bajar DBC |

## Config (`.env`)

```
SUPABASE_URL=...
SUPABASE_KEY=<service_role>
GROQ_API_KEY=<key>
GROQ_MODEL=openai/gpt-oss-120b
```

> El modelo por defecto es `openai/gpt-oss-120b` (el más potente de texto
> disponible en la cuenta Groq actual; los Llama no estaban habilitados).

## Refinar el diccionario

Tras cada corrida, abrí `salidas/objetos_<fecha>.csv`. Las filas donde la IA
dijo SÍ pero el diccionario NO (o al revés) son las que ayudan a mejorar:
agregá/quitá términos en `rubros.py` → `TERMINOS_SUBSTRING`, `TERMINOS_PALABRA`
o `EXCLUIR`.
