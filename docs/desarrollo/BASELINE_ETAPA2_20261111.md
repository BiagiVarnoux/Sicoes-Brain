# Baseline congelado — Etapa 2 (observaciones) + capa de fichas v2

**Fecha de congelado:** 2026-11-11
**Propósito:** foto versionada y reproducible del estado verificado antes de abrir
la etapa 3 (atributos/DBC) y la canonización (etapas 4–6). Las etapas 4/5/6 comparan
contra ESTA base, no contra algo que se mueve.

**Salida de datos (en disco, gitignored):**
`procesamiento/historico/data/adquisiciones_v2_desc_01/`
Reproducible con:
```sh
scraper/venv/bin/python -B -m procesamiento.historico.acquisitions \
  --output <salida> --association-rules v2
```

## Conteos sellados
- **Observaciones:** 2.070 (ids idénticos a v1).
- **Fichas (cards):** 1.136, cubren las 2.070 observaciones, una por observación (sin inflar).
- **Aristas recepción↔contratación:** CONFIRMADA **934**, AMBIGUA 55, DESCARTADA 8.072.
- **monto_real_ejecutado (recepción):** Bs 15.750.444,48.
- Corpus: 194 manifiestos (0660-10 / 0660-11, gestiones 2022–2026).
- Gate: 75/75 tests de `procesamiento/historico/tests` + 3 curados con
  `acquisiciones_referencia_v2.json`.

## SHA-256 de las salidas deterministas
```
asociaciones.jsonl          c05ba27130fd98a7de2c173982d3ae806382dfe445c4c826e70895cd6d0d21c4
cobertura_procesos.jsonl    ab41880873abaf476cbf511085d8dbb47c3ed1156d8d07be0c2928bebfafeada
documentos.jsonl            5faf9447e532fe3ac2f2835ce0d091aa499a86511ad6673c27deefea34bd3e0a
especificaciones.jsonl      f1a542c1578ad6c4d5cc2167911f81d4dfced3456384c9b3263861ddd1c25564
fichas.jsonl                e29b7439a50bb63d392e9f36681b323060a1f6b147f09e0c8f9f3a4e4157d47c
inventario_documental.jsonl 31d5100e39b05031af9bf6ffc25325e12e1bd066ca9356fe6f09b50bf89203ee
observaciones.jsonl         6bac798edb8cc16da732b26455980051778a22f350c5ce0cfe9194385e462ba9
secciones_dbc.jsonl         f5d5d517c5ffa6db855b53c410fc4453ed1ae8568978fe51da6a6bce17b09928
resumen.json                6a27322f4366150c1cefecf1e4f2aad8e6fbf72cbd0e526d433025d882af80ea
procedencia.json            b06e41391a344cb54a75535a0ddccf8aaab6852f3cc3ea63e4de4ee27d3befe2
```
(`fichas.sqlite` se omite del sello: es derivado de `fichas.jsonl` y su estado
interno no es byte-estable.)

## Qué NO está en esta foto (gaps conocidos, no bloquean el congelado)
- ~23 formularios anunciados-no-descargados y los 4 procesos con FORM 170 múltiple
  (todos PARCIAL). Se corrigen en el frente del scraper (ver AVANCE §Hallazgo y
  §Coordinación). Cuando se re-scrapeen, se saca una **foto nueva** y se compara
  contra esta.
