"""Recorte del DBC hacia la sección de especificaciones técnicas, para alimentar
a un extractor LLM con el MÍNIMO de texto útil (menos tokens, mejor señal).

Ancla en el encabezado real "ESPECIFICACIONES TÉCNICAS…" (vía dbc.section_bounds,
que lo ubica en ~690/725 DBC). Si no hay encabezado, cae a un recorte acotado por
cluster de marcadores en la segunda mitad (tope chico, no la cola de 45k del radar).

No llama a ningún LLM: solo prepara el texto. El proveedor (Groq/OpenAI/otro) se
decide aparte.
"""
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from . import dbc

CAP = 24000  # tope de chars del recorte (la mediana real es ~6.7k; acota outliers)
_MARK = re.compile(r"especificaci[oó]n\w*\s+t[eé]cnic|caracter[ií]sticas", re.I)
_C1 = re.compile(r"formulario\s*c\s*[-–]?\s*1\b", re.I)
_C2 = re.compile(r"formulario\s*c\s*[-–]?\s*2\b", re.I)
_P3 = re.compile(r"parte\s+(iii|3)\b", re.I)


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
    """Entrada preferida para el extractor LLM: el texto de las celdas del docx
    (preserva lo que el markdown aplana). Si el docx no da sección, cae al markdown."""
    if original_path and str(original_path).lower().endswith(".docx"):
        dt = region_from_docx(original_path, cap)
        if dt and len(dt) > 150:
            return dt
    return clip_region(markdown, cap)


def clip_region(markdown, cap=CAP):
    """Devuelve el tramo de specs del DBC (<= cap chars).

    Orden: (1) encabezado real "ESPECIFICACIONES TÉCNICAS…"; (2) C-1→C-2 del
    cuerpo; (3) cluster de marcadores / cola acotada."""
    sec = dbc.section_bounds(markdown)
    if sec and sec.get("text", "").strip():
        return sec["text"][:cap].strip()
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
