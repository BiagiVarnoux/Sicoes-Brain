"""
Parseo del Formulario C-1 (una vez por documento, cacheado).

El C-1 trae el REQUERIMIENTO LITERAL de la entidad vs lo OFERTADO (marca/modelo/
specs/precio). Vive SOLO como PDF en el Storage privado del ERP (bucket
`licitacion-files`). Este script, por cada C-1 aún no parseado:
  1. descarga el PDF del ERP,
  2. extrae el texto (PyMuPDF; si el PDF es escaneado y no hay texto, lo marca
     para OCR y lo salta),
  3. lo estructura con Groq (ítem, requerimiento, ofertado, marca, modelo, specs,
     cantidad, precio),
  4. lo cachea en `erp_c1` (Sicoes Brain). Re-correr NO re-parsea lo ya hecho.

⚠️ Descargar de un bucket PRIVADO requiere una credencial con acceso a Storage.
El acceso de SOLO LECTURA por RPC (erp_sync) NO alcanza para Storage. Por eso este
paso puntual usa la SERVICE_ROLE del ERP, SERVER-SIDE y de una sola vez (se puede
rotar después). Config en monitor/.env:
  ERP_SUPABASE_URL=...
  ERP_SERVICE_KEY=<service_role del ERP>     (solo para este parseo; gitignored)

Uso:
  ../scraper/venv/bin/python c1_parse.py            # parsea los pendientes
  ../scraper/venv/bin/python c1_parse.py --reparse  # reparsea todo
"""
import os
import sys
import json
import urllib.request
import urllib.parse

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import pymupdf  # PyMuPDF
import clasificador_ia

ERP_URL = os.environ.get("ERP_SUPABASE_URL", "").rstrip("/")
ERP_SERVICE_KEY = os.environ.get("ERP_SERVICE_KEY", "")
DEST_URL = os.environ["SUPABASE_URL"].rstrip("/")
DEST_KEY = os.environ["SUPABASE_KEY"]
BUCKET = "licitacion-files"


def _erp_get(path: str) -> list:
    req = urllib.request.Request(f"{ERP_URL}/rest/v1/{path}", headers={
        "apikey": ERP_SERVICE_KEY, "Authorization": f"Bearer {ERP_SERVICE_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _erp_download(storage_path: str) -> bytes | None:
    url = f"{ERP_URL}/storage/v1/object/{BUCKET}/{urllib.parse.quote(storage_path)}"
    req = urllib.request.Request(url, headers={
        "apikey": ERP_SERVICE_KEY, "Authorization": f"Bearer {ERP_SERVICE_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except Exception as e:
        print(f"      ⚠ no se pudo bajar {storage_path}: {e}", flush=True)
        return None


def _dest(method: str, path: str, rows=None, prefer: str = "") -> None:
    data = json.dumps(rows).encode() if rows is not None else None
    headers = {"apikey": DEST_KEY, "Authorization": f"Bearer {DEST_KEY}",
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(f"{DEST_URL}/rest/v1/{path}", data=data,
                                 method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def _ya_parseados() -> set:
    req = urllib.request.Request(
        f"{DEST_URL}/rest/v1/erp_c1?select=doc_path",
        headers={"apikey": DEST_KEY, "Authorization": f"Bearer {DEST_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {x["doc_path"] for x in json.loads(r.read())}
    except Exception:
        return set()


def _texto_pdf(data: bytes) -> str:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        return "\n".join(page.get_text() for page in doc).strip()
    except Exception as e:
        print(f"      ⚠ error leyendo PDF: {e}", flush=True)
        return ""


def listar_c1() -> list[dict]:
    """Documentos C-1 del ERP (categoria FORMULARIOS, nombre ~ 'C-1')."""
    sel = "nombre,path,licitaciones(numero_sicoes)"
    docs = _erp_get(f"licitacion_documentos?categoria=eq.FORMULARIOS"
                    f"&nombre=ilike.*C-1*&select={urllib.parse.quote(sel)}")
    out = []
    for d in docs:
        ns = ((d.get("licitaciones") or {}) or {}).get("numero_sicoes")
        if ns and d.get("path"):
            out.append({"numero_sicoes": ns, "nombre": d.get("nombre"), "path": d["path"]})
    return out


def main():
    if not ERP_URL or not ERP_SERVICE_KEY:
        print("❌ Falta ERP_SUPABASE_URL / ERP_SERVICE_KEY en monitor/.env "
              "(service_role del ERP; solo para este parseo de Storage).")
        return
    reparse = "--reparse" in sys.argv
    docs = listar_c1()
    print(f"C-1 encontrados en el ERP: {len(docs)}")
    hechos = set() if reparse else _ya_parseados()

    nuevos = escaneados = 0
    for d in docs:
        if d["path"] in hechos:
            continue
        print(f"  · {d['nombre']}", flush=True)
        data = _erp_download(d["path"])
        if not data:
            continue
        texto = _texto_pdf(data)
        if not texto:
            escaneados += 1
            print("      (sin texto — PDF escaneado, requiere OCR; lo salto por ahora)", flush=True)
            # igual guardamos el registro para saber que quedó pendiente de OCR
            _dest("POST", "erp_c1?on_conflict=doc_path", [{
                "numero_sicoes": d["numero_sicoes"], "doc_nombre": d["nombre"],
                "doc_path": d["path"], "items": [], "texto_crudo": "",
                "metodo": "ocr_pendiente"}], "resolution=merge-duplicates,return=minimal")
            continue
        items = clasificador_ia.estructurar_c1(texto)
        _dest("POST", "erp_c1?on_conflict=doc_path", [{
            "numero_sicoes": d["numero_sicoes"], "doc_nombre": d["nombre"],
            "doc_path": d["path"], "items": items, "texto_crudo": texto[:20000],
            "metodo": "texto"}], "resolution=merge-duplicates,return=minimal")
        nuevos += 1
        print(f"      ✓ {len(items)} ítem(s) estructurados", flush=True)

    print(f"\n✅ C-1: {nuevos} parseados, {escaneados} escaneados pendientes de OCR.")


if __name__ == "__main__":
    main()
