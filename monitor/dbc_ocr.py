"""
dbc_ocr.py — OCR de los DBC ESCANEADOS (PDFs que son imagen, sin texto).

`dbc_specs.py` marca `metodo='ocr_pendiente'` cuando PyMuPDF no logra extraer
texto (el PDF es un escaneo / imagen). Este script toma esos pendientes, baja el
PDF del bucket público `dbc`, rasteriza cada página y la pasa por Tesseract
(español), arma el texto y lo estructura con la MISMA IA (Groq) que usa
`dbc_specs`. Cachea en `convocatoria_specs`. Idempotente:
  - OCR con texto        → metodo='ocr'
  - OCR sin texto útil    → metodo='ocr_sin_texto'  (no se reintenta salvo --reparse)

Requiere el binario Tesseract instalado:
    brew install tesseract tesseract-lang

Uso:
  ../scraper/venv/bin/python dbc_ocr.py            # solo los 'ocr_pendiente'
  ../scraper/venv/bin/python dbc_ocr.py --reparse  # reintenta también 'ocr_sin_texto'
"""
import os
import io
import sys
import json
import time
import urllib.request
import urllib.parse

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import pymupdf
import pytesseract
from PIL import Image
import clasificador_ia

DEST_URL = os.environ["SUPABASE_URL"].rstrip("/")
DEST_KEY = os.environ["SUPABASE_KEY"]
H = {"apikey": DEST_KEY, "Authorization": f"Bearer {DEST_KEY}"}

OCR_LANG = os.environ.get("OCR_LANG", "spa")      # idioma Tesseract
OCR_DPI = int(os.environ.get("OCR_DPI", "220"))   # resolución de rasterizado
OCR_MAX_PAGINAS = int(os.environ.get("OCR_MAX_PAGINAS", "40"))  # tope por PDF


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


def _pdf_url(archivos: list) -> str | None:
    for a in (archivos or []):
        if (a.get("nombre") or "").lower().endswith(".pdf") and a.get("url"):
            return a["url"]
    return None


def _tesseract_ok() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_pdf(data: bytes) -> str:
    """Rasteriza cada página del PDF y la pasa por Tesseract. Devuelve el texto
    concatenado (vacío si no se obtuvo nada)."""
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        print(f"      ⚠ error abriendo PDF: {e}", flush=True)
        return ""
    mat = pymupdf.Matrix(OCR_DPI / 72, OCR_DPI / 72)
    partes: list[str] = []
    for i, page in enumerate(doc):
        if i >= OCR_MAX_PAGINAS:
            print(f"      … corte en {OCR_MAX_PAGINAS} páginas (PDF más largo)", flush=True)
            break
        try:
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            txt = pytesseract.image_to_string(img, lang=OCR_LANG)
            if txt and txt.strip():
                partes.append(txt)
        except Exception as e:
            print(f"      ⚠ OCR falló en pág {i + 1}: {e}", flush=True)
    return "\n".join(partes).strip()


def main():
    reparse = "--reparse" in sys.argv

    if not _tesseract_ok():
        print("✗ Tesseract no está instalado (o no está en el PATH).", flush=True)
        print("  Instalalo con:  brew install tesseract tesseract-lang", flush=True)
        sys.exit(1)

    metodos = "(ocr_pendiente,ocr_sin_texto)" if reparse else "(ocr_pendiente)"
    specs = _get(f"convocatoria_specs?select=cuce&metodo=in.{metodos}")
    cuces = [s["cuce"] for s in specs]
    if not cuces:
        print("Nada pendiente de OCR. ✅", flush=True)
        return

    # traer objeto + archivos de esos CUCE (en bloques para no pasarnos del largo de URL)
    radar: list[dict] = []
    for base in range(0, len(cuces), 50):
        trozo = cuces[base:base + 50]
        lista = ",".join(f'"{c}"' for c in trozo)
        radar += _get(f"convocatorias_radar?select=cuce,objeto,dbc_archivos&cuce=in.({lista})")

    print(f"DBC escaneados a OCR: {sum(1 for r in radar if _pdf_url(r.get('dbc_archivos')))} "
          f"(de {len(cuces)} pendientes)", flush=True)

    ok = vacios = 0
    for r in radar:
        cuce = r["cuce"]
        url = _pdf_url(r.get("dbc_archivos"))
        if not url:
            print(f"  · {cuce} — sin PDF en Storage; salto", flush=True)
            continue
        print(f"  · {cuce} — {(r.get('objeto') or '')[:55]}", flush=True)
        data = _descargar(url)
        if not data:
            continue
        print("      · OCR en curso (rasterizando páginas)...", flush=True)
        texto = _ocr_pdf(data)
        if not texto:
            vacios += 1
            print("      ⚠ OCR no obtuvo texto; marco 'ocr_sin_texto'", flush=True)
            _upsert({"cuce": cuce, "items": [], "texto_crudo": "", "metodo": "ocr_sin_texto"})
            continue
        items = clasificador_ia.estructurar_dbc(texto)
        _upsert({"cuce": cuce, "items": items, "texto_crudo": texto[:20000], "metodo": "ocr"})
        ok += 1
        print(f"      ✓ {len(items)} ítem(s) con specs (vía OCR)", flush=True)
        time.sleep(30)  # throttle Groq entre DBC (TPM)

    print(f"\n✅ OCR DBC: {ok} con specs, {vacios} sin texto aprovechable.", flush=True)


if __name__ == "__main__":
    main()
