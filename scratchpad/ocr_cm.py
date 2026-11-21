#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR-only de las ofertas CM del histórico local. Sin Groq, sin Supabase.
Lee los PDFs 'Oferta del Proveedor' ya en disco, usa texto embebido si existe,
si no rasteriza + Tesseract (spa). Guarda scratchpad/ocr_cm/<cuce>.txt.
Reanudable (salta los ya hechos). 2 workers.
  uso: scraper/venv/bin/python scratchpad/ocr_cm.py
"""
import glob, os, io, json, time, sys
from multiprocessing import Pool
import pymupdf, pytesseract
from PIL import Image

OUT = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad/ocr_cm"
MANIFEST = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad/ocr_cm_manifest.jsonl"
DATA = "/Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data"
DPI = 220; LANG = "spa"; MAXPAG = 40; WORKERS = 2
os.makedirs(OUT, exist_ok=True)

def pdfs_por_cuce():
    d = {}
    for p in glob.glob(DATA + "/historico_http_paginas_*/*/crudos/Oferta_del_Proveedor*.pdf"):
        cuce = p.split("/crudos/")[0].split("/")[-1]
        d.setdefault(cuce, []).append(p)
    return d

def ocr_pdf(path):
    """texto embebido si lo hay, si no Tesseract. Devuelve (texto, metodo, npags)."""
    doc = pymupdf.open(path)
    n = doc.page_count
    emb = "".join(doc[i].get_text() for i in range(min(n, 6)))
    if len(emb.strip()) > 200:                       # PDF con texto real
        full = "".join(doc[i].get_text() for i in range(n))
        return full, "texto", n
    mat = pymupdf.Matrix(DPI/72, DPI/72)             # imagen -> OCR
    partes = []
    for i, page in enumerate(doc):
        if i >= MAXPAG: break
        try:
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            t = pytesseract.image_to_string(img, lang=LANG)
            if t and t.strip(): partes.append(t)
        except Exception as e:
            partes.append(f"[OCR err pág {i+1}: {e}]")
    return "\n".join(partes).strip(), "ocr", n

def trabajar(args):
    cuce, paths = args
    dest = os.path.join(OUT, cuce + ".txt")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return (cuce, "skip", 0, 0)
    t0 = time.time(); textos = []; met = "vacio"; tot_p = 0
    for p in sorted(paths):
        try:
            txt, m, np_ = ocr_pdf(p); tot_p += np_
            if txt: textos.append(txt); met = m if m == "texto" else ("ocr" if met != "texto" else met)
        except Exception as e:
            textos.append(f"[err PDF {os.path.basename(p)}: {e}]")
    full = ("\n\n==== PDF ====\n\n".join(textos)).strip()
    with open(dest, "w", encoding="utf-8") as f:
        f.write(full)
    rec = {"cuce": cuce, "metodo": (met if full else "ocr_sin_texto"),
           "chars": len(full), "paginas": tot_p, "pdfs": len(paths), "seg": round(time.time()-t0, 1)}
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return (cuce, rec["metodo"], len(full), rec["seg"])

if __name__ == "__main__":
    tareas = sorted(pdfs_por_cuce().items())
    pend = [(c, p) for c, p in tareas if not (os.path.exists(os.path.join(OUT, c+".txt")) and os.path.getsize(os.path.join(OUT, c+".txt"))>0)]
    print(f"CUCEs total {len(tareas)} | pendientes {len(pend)} | workers {WORKERS}", flush=True)
    hechos = 0; t0 = time.time()
    with Pool(WORKERS) as pool:
        for cuce, met, ch, seg in pool.imap_unordered(trabajar, pend):
            hechos += 1
            if hechos % 20 == 0:
                el = time.time()-t0
                print(f"  {hechos}/{len(pend)} | {el:.0f}s | ~{el/hechos:.1f}s/cuce | últ: {cuce} [{met}] {ch}c", flush=True)
    print(f"LISTO OCR. {hechos} CUCEs procesados en {time.time()-t0:.0f}s", flush=True)
