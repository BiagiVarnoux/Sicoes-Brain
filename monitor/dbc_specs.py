"""
Extrae las ESPECIFICACIONES TÉCNICAS requeridas por la entidad del DBC de cada
convocatoria RELEVANTE. Es la base para después buscar/cotizar el producto.

Fuente: el PDF del DBC ya está en el bucket PÚBLICO `dbc` de Supabase (lo subió el
radar en dbc_archivos). Se baja por URL pública (sin credenciales), se extrae el
texto (PyMuPDF; escaneados → OCR pendiente) y se estructura con Groq. Cachea en
`convocatoria_specs`. Idempotente.

Uso:
  ../scraper/venv/bin/python dbc_specs.py            # pendientes
  ../scraper/venv/bin/python dbc_specs.py --reparse  # todo
"""
import os
import sys
import json
import time
import urllib.request

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import pymupdf
import clasificador_ia

DEST_URL = os.environ["SUPABASE_URL"].rstrip("/")
DEST_KEY = os.environ["SUPABASE_KEY"]
H = {"apikey": DEST_KEY, "Authorization": f"Bearer {DEST_KEY}"}


def _get(path: str) -> list:
    req = urllib.request.Request(f"{DEST_URL}/rest/v1/{path}", headers=H)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def _upsert(row: dict) -> None:
    req = urllib.request.Request(
        f"{DEST_URL}/rest/v1/convocatoria_specs?on_conflict=cuce",
        data=json.dumps([row]).encode(), method="POST",
        headers={**H, "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"})
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def _descargar(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.read()
    except Exception as e:
        print(f"      ⚠ no se pudo bajar: {e}", flush=True)
        return None


def _texto_pdf(data: bytes) -> str:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        return "\n".join(p.get_text() for p in doc).strip()
    except Exception as e:
        print(f"      ⚠ error PDF: {e}", flush=True)
        return ""


def _pdf_url(archivos: list) -> str | None:
    for a in (archivos or []):
        if (a.get("nombre") or "").lower().endswith(".pdf") and a.get("url"):
            return a["url"]
    return None


def main():
    reparse = "--reparse" in sys.argv
    relevantes = _get("convocatorias_radar?select=cuce,objeto,dbc_archivos"
                      "&relevante=eq.true&descartado=eq.false")
    hechos = set()
    if not reparse:
        for x in _get("convocatoria_specs?select=cuce,items,metodo"):
            if x.get("items") or x.get("metodo") == "ocr_pendiente":
                hechos.add(x["cuce"])

    print(f"Relevantes con DBC a procesar: "
          f"{sum(1 for r in relevantes if r['cuce'] not in hechos and _pdf_url(r.get('dbc_archivos')))}")
    nuevos = escaneados = 0
    for r in relevantes:
        cuce = r["cuce"]
        if cuce in hechos:
            continue
        url = _pdf_url(r.get("dbc_archivos"))
        if not url:
            continue
        print(f"  · {cuce} — {(r.get('objeto') or '')[:55]}", flush=True)
        data = _descargar(url)
        if not data:
            continue
        texto = _texto_pdf(data)
        if not texto:
            escaneados += 1
            print("      (sin texto — escaneado, OCR pendiente)", flush=True)
            _upsert({"cuce": cuce, "items": [], "texto_crudo": "", "metodo": "ocr_pendiente"})
            continue
        items = clasificador_ia.estructurar_dbc(texto)
        _upsert({"cuce": cuce, "items": items, "texto_crudo": texto[:20000], "metodo": "texto"})
        nuevos += 1
        print(f"      ✓ {len(items)} ítem(s) con specs", flush=True)
        time.sleep(40)  # throttle: los DBC son requests grandes (TPM Groq 8000)

    print(f"\n✅ DBC specs: {nuevos} extraídos, {escaneados} escaneados pendientes de OCR.")


if __name__ == "__main__":
    main()
