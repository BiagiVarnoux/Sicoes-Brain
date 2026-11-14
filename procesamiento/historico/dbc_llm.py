"""Recorte del DBC hacia la sección de especificaciones técnicas, para alimentar
a un extractor LLM con el MÍNIMO de texto útil (menos tokens, mejor señal).

Ancla en el encabezado real "ESPECIFICACIONES TÉCNICAS…" (vía dbc.section_bounds,
que lo ubica en ~690/725 DBC). Si no hay encabezado, cae a un recorte acotado por
cluster de marcadores en la segunda mitad (tope chico, no la cola de 45k del radar).

No llama a ningún LLM: solo prepara el texto. El proveedor (Groq/OpenAI/otro) se
decide aparte.
"""
import re
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
