"""Recorte del DBC hacia la sección de especificaciones técnicas, para alimentar
a un extractor LLM con el MÍNIMO de texto útil (menos tokens, mejor señal).

Ancla en el encabezado real "ESPECIFICACIONES TÉCNICAS…" (vía dbc.section_bounds,
que lo ubica en ~690/725 DBC). Si no hay encabezado, cae a un recorte acotado por
cluster de marcadores en la segunda mitad (tope chico, no la cola de 45k del radar).

No llama a ningún LLM: solo prepara el texto. El proveedor (Groq/OpenAI/otro) se
decide aparte.
"""
import re
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from . import dbc

_SOFFICE_CANDS = ("/Applications/LibreOffice.app/Contents/MacOS/soffice", "soffice", "libreoffice")


def _soffice():
    for c in _SOFFICE_CANDS:
        if c.startswith("/") and Path(c).exists():
            return c
        if shutil.which(c):
            return c
    return None


def ensure_docx(path):
    """Devuelve un .docx legible (zip). Si `path` ya es docx-zip, lo devuelve. Si es
    .doc viejo (OLE) o un .docx corrupto, lo convierte con LibreOffice y cachea el
    resultado en _docx_cache/ junto al archivo. None si no se puede."""
    path = Path(path)
    try:
        with ZipFile(path) as z:
            if "word/document.xml" in z.namelist():
                return path   # ya es un docx (zip con word/document.xml)
    except Exception:
        pass   # no es zip (o está corrupto) → convertir abajo
    # Es un zip SIN word/document.xml (p.ej. .doc que en realidad es un objeto de
    # dibujo OOXML: drs/e2oDoc.xml) o no es zip → convertir con LibreOffice.
    cache_dir = path.parent / "_docx_cache"
    cached = cache_dir / (path.stem + ".docx")
    if cached.exists():
        return cached
    soffice = _soffice()
    if not soffice:
        return None
    cache_dir.mkdir(exist_ok=True)
    try:
        subprocess.run([soffice, "--headless", "--convert-to", "docx", "--outdir",
                        str(cache_dir), str(path)], capture_output=True, timeout=180)
    except Exception:
        return None
    produced = cache_dir / (path.stem + ".docx")
    return produced if produced.exists() else None

CAP = 24000  # tope de chars del recorte (la mediana real es ~6.7k; acota outliers)
_MARK = re.compile(r"especificaci[oó]n\w*\s+t[eé]cnic|caracter[ií]sticas", re.I)
_C1 = re.compile(r"formulario\s*c\s*[-–]?\s*1\b", re.I)
_C2 = re.compile(r"formulario\s*c\s*[-–]?\s*2\b", re.I)
_P3 = re.compile(r"parte\s+(iii|3)\b", re.I)

# Encabezados que marcan el inicio de la sección de specs reales (varias grafías).
_HEAD_VARIANTS = (
    "especificaciones tecnicas y condiciones tecnicas requeridas del bien",
    "caracteristicas y condiciones tecnicas requeridas de los bienes",
    "caracteristicas tecnicas y condiciones tecnicas requeridas del bien",
    "especificaciones tecnicas requeridas",
)
# Señales de PLANTILLA en blanco / grilla de evaluación (NO son specs reales).
_TEMPLATE = ("llenado por la entidad", "proponente a", "proponente b",
             "cumple no cumple", "cumpleno cumple")


def _md_region(markdown, cap=CAP):
    """Recorte por TEXTO del markdown (para DBC .doc/OLE que no abren como docx).
    Ancla en la línea del encabezado real de specs (saltando el índice), y entre
    varias ocurrencias elige la que trae CONTENIDO real, no la plantilla en blanco
    'Formulario C-1 (Llenado por la Entidad)'."""
    lineas = markdown.splitlines()
    norm = [dbc.norm(l) for l in lineas]
    cands = [i for i, nl in enumerate(norm)
             if any(h in nl for h in _HEAD_VARIANTS)
             and "pageref" not in nl and "_toc" not in nl and "...." not in lineas[i]]
    if not cands:
        return ""
    best, best_score = "", -1e9
    for i in cands:
        ventana = "\n".join(lineas[i:i + 400])[:cap].strip()
        wn = dbc.norm(ventana)
        contenido = sum(1 for l in ventana.splitlines()[1:] if len(l.strip()) > 15)
        penal = sum(wn.count(mk) for mk in _TEMPLATE) * 6
        score = contenido - penal
        if score > best_score:
            best, best_score = ventana, score
    return best


def _c1_a_c2(markdown):
    """Formulario C-1 DEL CUERPO (última aparición, no la del índice) hasta el
    siguiente C-2 o Parte III. Captura specs cuando no hay encabezado explícito."""
    c1 = [m.start() for m in _C1.finditer(markdown)]
    if not c1:
        return None
    start = c1[-1]
    ends = [m.start() for m in _C2.finditer(markdown) if m.start() > start]
    ends += [m.start() for m in _P3.finditer(markdown) if m.start() > start]
    end = min(ends) if ends else min(len(markdown), start + CAP)
    region = markdown[start:end].strip()
    return region if len(region) > 200 else None


def region_from_docx(original_path, cap=CAP):
    """Texto de la sección de specs leído DIRECTO de las celdas del docx (no del
    markdown, que MarkItDown a veces aplana a celdas vacías). Ancla en el encabezado
    real y corta en Parte III. Devuelve '' si no hay docx/encabezado."""
    try:
        root = ET.fromstring(ZipFile(original_path).read("word/document.xml"))
    except Exception:
        return ""
    W = dbc.W
    body = list(root.find(W + "body"))
    start = next((i for i, e in enumerate(body)
                  if e.tag == W + "p" and dbc.HEADING in dbc.norm(dbc.text(e)) and len(dbc.text(e)) < 150), None)
    if start is None:
        return ""
    stop = next((i for i in range(start + 1, len(body))
                 if body[i].tag == W + "p" and (dbc.norm(dbc.text(body[i])) == "parte iii"
                 or "criterios que se pueden anadir" in dbc.norm(dbc.text(body[i])))), len(body))
    out = []
    for child in body[start:stop]:
        if child.tag == W + "tbl":
            for tr in child.findall(".//" + W + "tr"):
                cells = [dbc.text(c).strip() for c in tr.findall(W + "tc")]
                cells = [c for c in cells if c]
                if cells:
                    out.append(" | ".join(cells))
        else:
            t = dbc.text(child).strip()
            if t:
                out.append(t)
    return "\n".join(out)[:cap].strip()


def region_for_llm(original_path, markdown, cap=CAP):
    """Entrada para el extractor LLM: SIEMPRE el texto de las celdas del archivo
    (.docx directo, o .doc viejo convertido a .docx con LibreOffice). El markdown
    queda solo como último recurso si no se puede abrir/convertir el archivo."""
    if original_path:
        docx = ensure_docx(original_path)   # .docx tal cual, o .doc→.docx convertido
        if docx:
            dt = region_from_docx(docx, cap)
            if dt and len(dt) > 150:
                return dt
    return clip_region(markdown, cap)


def clip_region(markdown, cap=CAP):
    """Devuelve el tramo de specs del DBC (<= cap chars).

    Orden: (1) encabezado real como título markdown; (2) encabezado real por TEXTO
    (DBC .doc/OLE sin títulos #, evitando la plantilla en blanco); (3) C-1→C-2 del
    cuerpo; (4) cluster de marcadores / cola acotada."""
    sec = dbc.section_bounds(markdown)
    if sec and sec.get("text", "").strip():
        return sec["text"][:cap].strip()
    md = _md_region(markdown, cap)
    if md and len(md) > 150:
        return md
    alt = _c1_a_c2(markdown)
    if alt:
        return alt[:cap]
    # Fallback final: primer cluster de marcadores en la 2da mitad.
    pos = [m.start() for m in _MARK.finditer(markdown)]
    start = None
    for i, p in enumerate(pos):
        if i + 1 < len(pos) and pos[i + 1] - p <= 5000 and p > len(markdown) * 0.3:
            start = max(0, p - 300)
            break
    if start is None:
        start = max(0, len(markdown) - cap)  # cola acotada, no 45k
    region = markdown[start:start + cap]
    return re.sub(r"!\[[^\]]*\]\(data:[^)]*\)", "", region).strip()  # sin imágenes base64
