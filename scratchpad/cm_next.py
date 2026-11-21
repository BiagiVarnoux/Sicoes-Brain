#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entrega los proximos N CM pendientes (no en el store) para que Opus los estructure.
  uso: python3 scratchpad/cm_next.py [N]
"""
import json, os, sys, glob

SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
STORE = SP + "/cm_estructurado.jsonl"
OCR = SP + "/ocr_cm"

N = int(sys.argv[1]) if len(sys.argv) > 1 else 15

hechos = set()
if os.path.exists(STORE):
    for l in open(STORE):
        l = l.strip()
        if l:
            hechos.add(json.loads(l)["cuce"])

saltar = set()
susp = SP + "/cm_malos.json"
if os.path.exists(susp) and "--incluir-sosp" not in sys.argv:
    saltar = set(json.load(open(susp)))

todos = sorted(c[:-4] for c in os.listdir(OCR) if c.endswith(".txt"))
pend = [c for c in todos if c not in hechos and c not in saltar]
print(f"### STORE: {len(hechos)} hechos | PENDIENTES: {len(pend)} | muestro {min(N,len(pend))}\n", flush=True)
for c in pend[:N]:
    txt = open(os.path.join(OCR, c + ".txt"), encoding="utf-8").read()
    print("=" * 72)
    print("CUCE:", c)
    print("=" * 72)
    print(txt[:6000])
    print()
