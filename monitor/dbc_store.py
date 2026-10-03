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


def convertir_a_pdf(ruta: str) -> str:
    """Si es Word, lo convierte a PDF y devuelve la ruta del PDF (borrando el
    Word). Si ya es PDF u otro formato, devuelve la ruta original.
    Intenta LibreOffice y, si no está, textutil + Chromium headless (Brave/Chrome)."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext not in (".doc", ".docx", ".odt", ".rtf"):
        return ruta
    pdf = _conv_libreoffice(ruta) or _conv_textutil_chromium(ruta)
    if pdf and os.path.exists(pdf):
        if pdf != ruta:
            try:
                os.remove(ruta)  # borrar el Word original
            except OSError:
                pass
        return pdf
    print(f"      ⚠ No se pudo convertir a PDF ({os.path.basename(ruta)}); dejo original.", flush=True)
    return ruta


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


def nombre_archivo(cuce: str, modalidad: str, rol: str, idx: int, total: int, ext: str) -> str:
    base = f"{prefijo(modalidad)} - {cuce4(cuce)}"
    if total > 1:
        etiqueta = _sanitizar(rol) or f"{idx+1}"
        base = f"{base} - {etiqueta}"
    return base + ext


def procesar(cuce: str, modalidad: str, archivos_locales: list[dict]) -> list[dict]:
    """archivos_locales: [{ruta, nombre}] ya descargados.
    Convierte, renombra, sube; devuelve [{nombre, url}] para el dashboard."""
    total = len(archivos_locales)
    salida = []
    usados = set()
    for idx, a in enumerate(archivos_locales):
        ruta = a.get("ruta")
        if not ruta or not os.path.exists(ruta):
            continue
        ruta = convertir_a_pdf(ruta)
        ext = os.path.splitext(ruta)[1].lower()
        fname = nombre_archivo(cuce, modalidad, a.get("nombre", ""), idx, total, ext)
        # evitar colisiones de nombre dentro de la misma convocatoria
        if fname in usados:
            raiz, e = os.path.splitext(fname)
            fname = f"{raiz} ({idx+1}){e}"
        usados.add(fname)
        path_remoto = f"{cuce}/{fname}"
        url = subir(ruta, path_remoto)
        if url:
            salida.append({"nombre": fname, "url": url})
    return salida
