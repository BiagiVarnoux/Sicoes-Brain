"""
Extrae las ESPECIFICACIONES TÉCNICAS requeridas por la entidad del DBC de cada
convocatoria RELEVANTE. Es la base para después buscar/cotizar el producto.

Fuente preferida: campo `dbc_markdown` en la DB (ya convertido por dbc_store).
Fallback: PDF en Supabase Storage (registros anteriores a la migración markitdown).

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
    relevantes = _get("convocatorias_radar?select=cuce,objeto,dbc_archivos,dbc_markdown"
                      "&relevante=eq.true&descartado=eq.false")
    hechos = set()
    if not reparse:
        # Marcar como hecho cualquier CUCE que ya exista en convocatoria_specs,
        # aunque haya devuelto 0 items (evita re-procesar en corridas siguientes).
        for x in _get("convocatoria_specs?select=cuce"):
            hechos.add(x["cuce"])

    pendientes = [r for r in relevantes if r["cuce"] not in hechos
                  and (r.get("dbc_markdown") or _pdf_url(r.get("dbc_archivos")))]
    print(f"Relevantes con DBC a procesar: {len(pendientes)}")

    nuevos = escaneados = 0
    for r in pendientes:
        cuce = r["cuce"]
        print(f"  · {cuce} — {(r.get('objeto') or '')[:55]}", flush=True)

        texto = r.get("dbc_markdown") or ""
        metodo = "markdown"

        if not texto:
            # Fallback: bajar PDF de Storage (registros anteriores a markitdown)
            url = _pdf_url(r.get("dbc_archivos"))
            if not url:
                continue
            data = _descargar(url)
            if not data:
                continue
            texto = _texto_pdf(data)
            metodo = "texto_pdf"
            if not texto:
                escaneados += 1
                print("      (sin texto — escaneado, OCR pendiente)", flush=True)
                _upsert({"cuce": cuce, "items": [], "texto_crudo": "", "metodo": "ocr_pendiente"})
                continue

        items = clasificador_ia.estructurar_dbc(texto)
        _upsert({"cuce": cuce, "items": items, "texto_crudo": texto[:20000], "metodo": metodo})
        nuevos += 1
        print(f"      ✓ {len(items)} ítem(s) con specs (vía {metodo})", flush=True)
        time.sleep(40)  # throttle: los DBC son requests grandes (TPM Groq 8000)

    print(f"\n✅ DBC specs: {nuevos} extraídos, {escaneados} escaneados pendientes de OCR.")


if __name__ == "__main__":
    main()
