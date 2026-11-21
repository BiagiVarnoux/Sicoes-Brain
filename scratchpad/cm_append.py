#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida scratchpad/cm_batch.json y lo agrega (dedup por cuce) al store.
Cada registro: {cuce, items:[{item,descripcion,especificaciones,cantidad,unidad}]}
  uso: python3 scratchpad/cm_append.py
"""
import json, os, datetime

SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
STORE = SP + "/cm_estructurado.jsonl"
BATCH = SP + "/cm_batch.json"

hechos = set()
if os.path.exists(STORE):
    for l in open(STORE):
        if l.strip():
            hechos.add(json.loads(l)["cuce"])

recs = json.load(open(BATCH, encoding="utf-8"))
ts = datetime.datetime.now().isoformat(timespec="seconds")
nuevos = ok = dup = 0
with open(STORE, "a", encoding="utf-8") as f:
    for r in recs:
        c = r["cuce"]
        if c in hechos:
            dup += 1; continue
        items = r.get("items", [])
        for it in items:          # normaliza claves faltantes
            it.setdefault("cantidad", None)
            it.setdefault("unidad", None)
            it.setdefault("especificaciones", "")
        rec = {"cuce": c, "fuente": "cm_ocr", "n_items": len(items),
               "items": items, "ts": ts}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        hechos.add(c); nuevos += 1; ok += len(items)
print(f"agregados {nuevos} CUCE ({ok} items) | duplicados saltados {dup} | store total {len(hechos)}")
