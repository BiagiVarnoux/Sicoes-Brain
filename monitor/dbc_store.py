"""
Manejo de DBC: conversión Word→PDF, nombrado y subida a Supabase Storage.

Reglas acordadas con el usuario:
- Nombre de archivo: prefijo según modalidad → "CM" si la modalidad es CM,
  "DBC" para el resto (ANPE/ANPP/LP); seguido de " - <4ª casilla del CUCE>".
  Si la convocatoria trae varios archivos, se agrega " - <rol>" (Convocatoria,
  Especificaciones Tecnicas, Pliego...) o un índice.
- Formato: los Word (.doc/.docx) se convierten a PDF; los PDF se dejan igual;
  cualquier otro formato se sube tal cual.
- Se sube al bucket público 'dbc' de Supabase Storage; se devuelve la URL pública.
"""
import os
import re
import json
import subprocess
import unicodedata
import urllib.request
import urllib.error
import urllib.parse

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BUCKET = "dbc"

# Rutas posibles del binario de LibreOffice (macOS / PATH)
_SOFFICE_CANDIDATOS = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "soffice",
    "libreoffice",
]

# Navegadores Chromium para HTML→PDF headless (macOS / PATH)
_CHROMIUM_CANDIDATOS = [
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
]


def _buscar(cands: list[str]) -> str | None:
    from shutil import which
    for c in cands:
        if c.startswith("/"):
            if os.path.exists(c):
                return c
        elif which(c):
            return c
    return None


def _soffice() -> str | None:
    return _buscar(_SOFFICE_CANDIDATOS)


def cuce4(cuce: str) -> str:
    partes = (cuce or "").split("-")
    return partes[3] if len(partes) >= 4 else (cuce or "sincuce")


def prefijo(modalidad: str) -> str:
    return "CM" if (modalidad or "").strip().upper() == "CM" else "DBC"


def _sanitizar(txt: str) -> str:
    """Nombre de archivo seguro (sin acentos ni caracteres raros)."""
    if not txt:
        return ""
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^A-Za-z0-9 \-]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:60]


def _conv_libreoffice(ruta: str) -> str | None:
    soffice = _soffice()
    if not soffice:
        return None
    outdir = os.path.dirname(ruta)
    try:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", outdir, ruta],
            check=True, capture_output=True, timeout=120,
            env={**os.environ, "HOME": os.environ.get("HOME", "/tmp")},
        )
        pdf = os.path.splitext(ruta)[0] + ".pdf"
        return pdf if os.path.exists(pdf) else None
    except Exception:
        return None


def _conv_textutil_chromium(ruta: str) -> str | None:
    """Word→HTML con textutil (nativo macOS) y HTML→PDF con Chromium headless.
    No requiere instalar nada (usa Brave/Chrome ya instalado)."""
    chromium = _buscar(_CHROMIUM_CANDIDATOS)
    if not chromium:
        return None
    base = os.path.splitext(ruta)[0]
    html = base + ".__conv.html"
    pdf = base + ".pdf"
    try:
        subprocess.run(["textutil", "-convert", "html", ruta, "-output", html],
                       check=True, capture_output=True, timeout=60)
        # OJO: NO usar --user-data-dir con un perfil nuevo: Brave se cuelga
        # inicializándolo en headless. El perfil por defecto funciona y no choca
        # con el scraper (que corre con --user-data-dir=/tmp/brave-sicoes).
        subprocess.run(
            [chromium, "--headless=new", "--disable-gpu",
             "--no-first-run", "--no-default-browser-check", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf}", "file://" + os.path.abspath(html)],
            check=True, capture_output=True, timeout=90,
        )
        return pdf if os.path.exists(pdf) else None
    except Exception:
        return None
    finally:
        if os.path.exists(html):
            try:
                os.remove(html)
            except OSError:
                pass


def convertir_a_pdf(ruta: str, borrar_original: bool = True) -> str:
    """Si es Word, lo convierte a PDF y devuelve la ruta del PDF. Si ya es PDF u
    otro formato, devuelve la ruta original. Usa LibreOffice (fiel al formato) y,
    si no está, textutil + Chromium headless como último recurso.
    `borrar_original=False` conserva el .docx (para guardar docx Y pdf)."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext not in (".doc", ".docx", ".odt", ".rtf"):
        return ruta
    pdf = _conv_libreoffice(ruta) or _conv_textutil_chromium(ruta)
    if pdf and os.path.exists(pdf):
        if borrar_original and pdf != ruta:
            try:
                os.remove(ruta)
            except OSError:
                pass
        return pdf
    print(f"      ⚠ No se pudo convertir a PDF ({os.path.basename(ruta)}); dejo original.", flush=True)
    return ruta


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def seleccionar_objetivo(modalidad: str, archivos: list[dict]) -> dict | None:
    """Devuelve el ÚNICO archivo que interesa por convocatoria:
    - CM → 'Oferta del Proveedor'
    - ANPE/ANPP/LP (y resto) → 'Documento Base de Contratación'
    archivos: [{token, nombre}]. None si no se encuentra el objetivo."""
    if not archivos:
        return None
    es_cm = (modalidad or "").strip().upper() == "CM"
    for a in archivos:
        n = _norm(a.get("nombre", ""))
        if es_cm and "oferta" in n:
            return a
        if not es_cm and ("documento base" in n or n.strip() == "dbc"):
            return a
    return None


def _content_type(ext: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "application/zip",
        ".rar": "application/x-rar-compressed",
    }.get(ext.lower(), "application/octet-stream")


def subir(ruta_local: str, path_remoto: str) -> str | None:
    """Sube un archivo al bucket (upsert) y devuelve la URL pública, o None."""
    ext = os.path.splitext(ruta_local)[1].lower()
    with open(ruta_local, "rb") as fh:
        data = fh.read()
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{urllib.parse.quote(path_remoto)}"
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": _content_type(ext),
            "x-upsert": "true",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=60).read()
        return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{urllib.parse.quote(path_remoto)}"
    except urllib.error.HTTPError as e:
        cuerpo = ""
        try:
            cuerpo = e.read().decode()[:160]
        except Exception:
            pass
        print(f"      ⚠ Storage HTTP {e.code}: {cuerpo}", flush=True)
        return None
    except Exception as e:
        print(f"      ⚠ Storage red: {e}", flush=True)
        return None


def limpiar_storage(cuce: str) -> None:
    """Borra todos los objetos bajo '{cuce}/' en el bucket (para no dejar PDFs
    viejos mal convertidos ni nombres antiguos al re-subir)."""
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}",
            data=json.dumps({"prefix": f"{cuce}/", "limit": 100}).encode(),
            method="POST",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Content-Type": "application/json"},
        )
        objs = json.loads(urllib.request.urlopen(req, timeout=30).read())
        prefixes = [f"{cuce}/{o['name']}" for o in objs if o.get("name")]
        if not prefixes:
            return
        req = urllib.request.Request(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}",
            data=json.dumps({"prefixes": prefixes}).encode(),
            method="DELETE",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        print(f"      ⚠ No se pudo limpiar Storage de {cuce}: {e}", flush=True)


def procesar(cuce: str, modalidad: str, archivos_locales: list[dict]) -> list[dict]:
    """archivos_locales: [{ruta, nombre}] — normalmente UN solo archivo objetivo
    (el DBC para ANPE/ANPP/LP, o la Oferta para CM). Para los Word guarda AMBOS
    formatos (.docx original + .pdf convertido con LibreOffice); para PDF guarda el
    PDF. Nombre: '<CM|DBC> - <cuce4>.<ext>'. Devuelve [{nombre, url}]."""
    base = f"{prefijo(modalidad)} - {cuce4(cuce)}"
    limpiar_storage(cuce)  # borrar objetos viejos antes de subir los nuevos
    salida = []
    for a in archivos_locales:
        ruta = a.get("ruta")
        if not ruta or not os.path.exists(ruta):
            continue
        ext0 = os.path.splitext(ruta)[1].lower()
        if ext0 in (".doc", ".docx", ".odt", ".rtf"):
            # 1) subir el Word original tal cual
            fdoc = base + ext0
            url = subir(ruta, f"{cuce}/{fdoc}")
            if url:
                salida.append({"nombre": fdoc, "url": url})
            # 2) convertir a PDF (sin borrar el original) y subir
            pdf = convertir_a_pdf(ruta, borrar_original=False)
            if pdf and os.path.exists(pdf) and pdf.lower().endswith(".pdf"):
                fpdf = base + ".pdf"
                url = subir(pdf, f"{cuce}/{fpdf}")
                if url:
                    salida.append({"nombre": fpdf, "url": url})
        elif ext0 == ".pdf":
            fpdf = base + ".pdf"
            url = subir(ruta, f"{cuce}/{fpdf}")
            if url:
                salida.append({"nombre": fpdf, "url": url})
        else:
            fo = base + ext0
            url = subir(ruta, f"{cuce}/{fo}")
            if url:
                salida.append({"nombre": fo, "url": url})
    return salida
