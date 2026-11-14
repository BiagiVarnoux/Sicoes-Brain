# Baseline etapa 2 — corpus COMPLETO (8 entidades, 1.296 CUCE)

**Fecha:** 2026-11-14. Reemplaza al baseline de 194 CUCE
([BASELINE_ETAPA2_20261111.md](BASELINE_ETAPA2_20261111.md), ahora solo histórico).

Corrida desde cero sobre todo el corpus re-scrapeado (no reusa la muestra anterior).
Salida en disco (gitignored): `procesamiento/historico/data/adquisiciones_etapa2_full_20261114/`.
Reproducible con:
```sh
scraper/venv/bin/python -B -m procesamiento.historico.acquisitions \
  --output <salida_nueva> --association-rules v2
```
(`acquisitions.py` ahora descubre dinámicamente las 40 carpetas entidad/gestión; no hay lista fija.)

## Conteos sellados
- Corpus: **1.296 CUCE**, 8 entidades (0660-06 … 0660-13), gestiones 2022–2026.
- **Observaciones: 18.253**  ·  **Fichas: 9.460**.
- Asociación recepción↔contratación (ficha-level): **CONFIRMADA 8.793 (93%)**, AMBIGUA 346, SIN_VINCULAR 321.
- Aristas recepción↔contratación: CONFIRMADA 8.793, AMBIGUA 203, DESCARTADA 103.409.
- `demand_additive = false` (anti doble-conteo).
- Fidelidad: **207.715 celdas verificadas, 0 fallas** (COTEJO_TEXTO_OK).
- **DBC specs↔ficha (débil, pendiente etapa 3 LLM): CONFIRMADA 318, AMBIGUA 3.450, SIN_VINCULAR 5.692.**

## SHA-256 (salidas deterministas clave)
```
resumen.json             af9178a828c9eab7f1090be234495ca90713ad289ea838f9a256ea28c9868975
cobertura_procesos.jsonl 64496968e6bc3026207903f73ab5606b43916957a481ecae531ab91b277575eb
observaciones.jsonl      84ee92b48171e081800f33abbba97f1217df53252e10a7851668591310be8343
especificaciones.jsonl   f015a116cae7516182dcf098e82c939fbfbd78f518bb6135800b81d008f2281a
secciones_dbc.jsonl      e7ca139b0f81b3e87066735c6995855dff13d9eadbba4a8b42980244f473fc30
```
(`fichas.jsonl`, `asociaciones.jsonl`, `documentos.jsonl`, `fichas.sqlite` se omiten del
sello por tamaño/derivabilidad; se regeneran de lo anterior.)

## Pendientes que abre este baseline
1. **Etapa 3 (DBC specs)**: subir CONFIRMADA de 318 con el extractor LLM del radar
   (`clasificador_ia.estructurar_dbc`) — es lo que da specs útiles al dashboard.
2. **Cargador fichas → Supabase** (`hist_procesos`/`hist_items`) con specs del DBC, para
   que el dashboard histórico lea el corpus nuevo.
3. **Tests dependientes de datos**: 13 fallas + 1 error por conteos/etiquetas clavados al
   corpus viejo de 194 (p.ej. "Formulario 220 (Erroneo)" en un CUCE donde ya no existe).
   No es lógica rota — refrescar contra el corpus nuevo o clavar a fixture congelado.
