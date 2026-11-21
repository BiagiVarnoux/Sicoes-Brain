#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-OCR de los CM sospechosos (escaneo rotado) con deteccion de orientacion.
Usa image_to_osd para hallar el giro, rota la imagen y vuelve a OCR.
Sobrescribe scratchpad/ocr_cm/<cuce>.txt solo si mejora.
  uso: scraper/venv/bin/python scratchpad/reocr_rotados.py
"""
import json, os, io, glob, re
import pymupdf, pytesseract
from PIL import Image

SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
OCR = SP + "/ocr_cm"
DATA = "/Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data"
DPI = 300; LANG = "spa"; MAXPAG = 40

ANC = re.compile(r'\b(de|la|para|con|cantidad|precio|unidad|total|color|material|tipo|caja|bolsa|papel|tinta|toner|unitario|especificaciones|producto|marca|medida|contenido|envase)\b', re.I)

def ratio(t):
    nw = len(re.findall(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]{2,}', t)) or 1
    return len(ANC.findall(t)) / nw

def pdfs(cuce):
    return sorted(glob.glob(f"{DATA}/historico_http_paginas_*/{cuce}/crudos/Oferta_del_Proveedor*.pdf"))

def ocr_rot(path):
    doc = pymupdf.open(path)
    mat = pymupdf.Matrix(DPI/72, DPI/72)
    partes = []
    for i, page in enumerate(doc):
        if i >= MAXPAG: break
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            osd = pytesseract.image_to_osd(img)
            m = re.search(r"Rotate: (\d+)", osd)
            ang = int(m.group(1)) if m else 0
            if ang: img = img.rotate(-ang, expand=True)
        except Exception:
            pass
        try:
            t = pytesseract.image_to_string(img, lang=LANG)
            if t and t.strip(): partes.append(t)
        except Exception as e:
            partes.append(f"[err {i}: {e}]")
    return "\n".join(partes).strip()

susp = json.load(open(SP + "/cm_sospechosos.json"))
print(f"re-OCR de {len(susp)} sospechosos (DPI {DPI}, auto-rotacion)\n", flush=True)
mejor = igual = 0
for k, cuce in enumerate(susp, 1):
    ps = pdfs(cuce)
    if not ps:
        print(f"  {k}/{len(susp)} {cuce}: sin PDF", flush=True); continue
    viejo = open(f"{OCR}/{cuce}.txt", encoding="utf-8").read()
    r0 = ratio(viejo)
    nuevo = "\n\n==== PDF ====\n\n".join(ocr_rot(p) for p in ps).strip()
    r1 = ratio(nuevo)
    if r1 > r0 + 0.01 and len(nuevo) > 200:
        open(f"{OCR}/{cuce}.txt", "w", encoding="utf-8").write(nuevo)
        mejor += 1; flag = "MEJORA"
    else:
        igual += 1; flag = "igual"
    print(f"  {k}/{len(susp)} {cuce}: ratio {r0:.3f}->{r1:.3f} [{flag}]", flush=True)
print(f"\nLISTO. mejorados {mejor} | sin cambio {igual}", flush=True)
