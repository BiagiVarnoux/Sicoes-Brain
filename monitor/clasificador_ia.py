"""
Filtro B — Clasificador con IA (Groq)
=====================================
Analiza el "Objeto de Contratación" de cada convocatoria y decide si corresponde
a los rubros del usuario: productos/accesorios de computación (hardware: RAM, SSD,
discos, periféricos, impresoras, computadoras, redes, etc.) o etiquetas
autoadhesivas / insumos de etiquetado.

Usa la API de Groq (endpoint compatible con OpenAI). Clasifica en lotes para
ahorrar requests. Si la IA falla, devuelve relevante=False sin crashear (el
filtro de diccionario sigue funcionando en paralelo).
"""
import os
import re
import json
import time
import urllib.request
import urllib.error

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
# gpt-oss-120b es el modelo de texto más potente disponible en esta cuenta Groq.
# (Los Llama no estaban habilitados para la key actual.) Configurable por .env.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

LOTE = 20  # objetos por request

SYSTEM_PROMPT = (
    "Eres un asistente que clasifica licitaciones públicas de Bolivia (SICOES). "
    "El usuario SOLO vende: productos y accesorios de computación (computadoras, "
    "laptops, memoria RAM, discos SSD/HDD, procesadores, placas, monitores, "
    "teclados, mouse, periféricos, impresoras, scanners, tóner/cartuchos/tinta, "
    "cables, redes, routers, switches, UPS, estabilizadores) y etiquetas "
    "autoadhesivas / insumos de etiquetado (stickers, rótulos, códigos de barras, "
    "ribbon, impresoras de etiquetas). "
    "Para cada objeto de contratación, decide si el usuario PODRÍA proveerlo. "
    "Marca relevante=true solo si el bien principal cae en esos rubros. "
    "Si es un servicio, obra, mobiliario, insumo médico, alimento, vehículo u otro "
    "rubro ajeno, relevante=false. "
    "Responde EXCLUSIVAMENTE un array JSON válido, un objeto por entrada, en el "
    'mismo orden, con forma: [{"i":<indice>,"relevante":<true|false>,'
    '"razon":"<=10 palabras"}]. Sin texto adicional.'
)


def _request(payload: dict, intentos: int = 5) -> dict | None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        GROQ_URL, data=data, method="POST",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            # Groq está detrás de Cloudflare: sin un User-Agent "de navegador"
            # devuelve 403 (error 1010) bloqueando el UA de python-urllib.
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0 Safari/537.36",
        },
    )
    for i in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            cuerpo = ""
            try:
                cuerpo = e.read().decode()[:200]
            except Exception:
                pass
            # 429 (rate limit) → esperar y reintentar; otros 4xx no se reintentan
            if e.code == 429 and i < intentos - 1:
                # TPM se resetea por minuto → esperar ~el minuto completo
                espera = min(65, 30 * (i + 1))
                print(f"      ⚠ Groq 429 rate limit; espero {espera}s...", flush=True)
                time.sleep(espera)
                continue
            print(f"      ✗ Groq HTTP {e.code}: {cuerpo}", flush=True)
            return None
        except Exception as e:
            espera = 2 ** i
            print(f"      ⚠ Groq red falló ({type(e).__name__}); reintento en {espera}s...", flush=True)
            time.sleep(espera)
    return None


def _parse_array(contenido: str) -> list[dict]:
    """Extrae el array JSON de la respuesta (tolerante a texto alrededor)."""
    contenido = contenido.strip()
    # quitar fences ```json ... ```
    if contenido.startswith("```"):
        contenido = contenido.strip("`")
        if contenido.lower().startswith("json"):
            contenido = contenido[4:]
    ini = contenido.find("[")
    fin = contenido.rfind("]")
    if ini == -1 or fin == -1:
        return []
    try:
        return json.loads(contenido[ini:fin + 1])
    except Exception:
        return []


def _bloque_ejemplos(pos: list[str] | None, neg: list[str] | None) -> str:
    """Few-shot con el criterio real del usuario (de sus decisiones en el radar)."""
    partes = []
    if pos:
        partes.append("Ejemplos que el usuario SÍ considera relevantes (relevante=true):\n"
                      + "\n".join(f"- {t}" for t in pos[:25]))
    if neg:
        partes.append("Ejemplos que el usuario DESCARTÓ porque NO maneja ese producto "
                      "(relevante=false; aprendé a descartar esa categoría):\n"
                      + "\n".join(f"- {t}" for t in neg[:25]))
    if not partes:
        return ""
    return ("\n\nCriterio aprendido de las decisiones reales del usuario — "
            "respetalo:\n" + "\n\n".join(partes))


C1_SYSTEM = (
    "Eres un asistente que extrae datos del Formulario C-1 de una licitación pública "
    "boliviana (SICOES). El C-1 lista, por ítem, lo que REQUIERE la entidad y lo que "
    "OFRECE el proveedor. Del texto dado, devolvé EXCLUSIVAMENTE un array JSON, un "
    "objeto por ítem, con la forma: "
    '[{"item":<nº o texto>,"requerimiento_entidad":"<lo que pide la entidad>",'
    '"ofertado":"<lo que ofrece el proveedor>","marca":"","modelo":"",'
    '"especificaciones":"","cantidad":<nº o null>,"precio_unitario":<nº o null>}]. '
    "Si un campo no aparece, usá \"\" o null. No inventes. Sin texto fuera del array."
)


def estructurar_c1(texto: str) -> list[dict]:
    """Convierte el texto crudo de un C-1 en items estructurados. [] si falla."""
    if not texto or not texto.strip() or not GROQ_API_KEY:
        return []
    payload = {
        "model": GROQ_MODEL, "temperature": 0,
        "messages": [
            {"role": "system", "content": C1_SYSTEM},
            {"role": "user", "content": "Texto del Formulario C-1:\n" + texto[:8000]},
        ],
    }
    resp = _request(payload)
    if not resp:
        return []
    try:
        return _parse_array(resp["choices"][0]["message"]["content"])
    except Exception:
        return []


DBC_SYSTEM = (
    "Eres un asistente que extrae las ESPECIFICACIONES TÉCNICAS DEL PRODUCTO "
    "requeridas por la entidad en un pliego/DBC de una licitación pública boliviana. "
    "Del texto dado, identificá cada ítem/producto solicitado y SOLO sus requisitos "
    "TÉCNICOS del bien (capacidad, dimensiones, velocidad, interfaz, potencia, "
    "conectividad, material, resolución, marca/modelo si se exige, norma técnica, "
    "etc.) — los que sirven para encontrar/comprar el producto. "
    "IGNORÁ las condiciones comerciales y administrativas: garantía, plazo de "
    "entrega, multas, forma/lugar de pago, lugar de entrega, 'producto nuevo/"
    "original', 'manifestar aceptación', embalaje y similares. "
    "Devolvé EXCLUSIVAMENTE un array JSON, un objeto por ítem: "
    '[{"item":<nº o texto>,"descripcion":"<nombre/producto>",'
    '"especificaciones":["<req técnico 1>","<req técnico 2>", ...],'
    '"cantidad":<nº o null>,"unidad":"<unidad o \\"\\">"}]. '
    "No inventes; si no hay specs técnicas claras, dejá la lista vacía. "
    "Sin texto fuera del array."
)


_RE_MARCADOR_SPECS = re.compile(
    r"especificaci[oó]n\w*\s+t[eé]cnic|caracter[ií]sticas", re.IGNORECASE)


def _region_specs(texto: str, ancho_max: int = 45000) -> str:
    """El DBC es largo (decenas de páginas) y las fichas técnicas (Formulario C-1)
    están en la segunda mitad. La PRIMERA mención de 'especificaciones técnicas' es
    solo la instrucción; la tabla real es un CLUSTER de menciones más adentro.
    Arranca la región en el primer marcador que tiene otro cerca (el cluster)."""
    pos = [m.start() for m in _RE_MARCADOR_SPECS.finditer(texto)]
    if not pos:
        return texto[:ancho_max]
    inicio = pos[0]
    for i, p in enumerate(pos):
        if i + 1 < len(pos) and pos[i + 1] - p <= 5000:
            inicio = p
            break
    inicio = max(0, inicio - 300)
    return texto[inicio:inicio + ancho_max]


def _dedup_items(items: list[dict]) -> list[dict]:
    """Une ítems de chunks distintos; ante misma descripción, deja el que tiene
    más especificaciones."""
    out: dict[str, dict] = {}
    orden: list[str] = []
    import unicodedata
    for it in items:
        if not isinstance(it, dict):
            continue
        d = unicodedata.normalize("NFKD", str(it.get("descripcion", "")))
        d = "".join(c for c in d if not unicodedata.combining(c)).strip().lower()
        k = d[:80] or str(len(orden))
        n = len(it.get("especificaciones") or [])
        if k not in out:
            out[k] = it
            orden.append(k)
        elif n > len(out[k].get("especificaciones") or []):
            out[k] = it
    return [out[k] for k in orden]


def estructurar_dbc(texto: str, chunk: int = 11000, solapa: int = 800,
                    max_chunks: int = 4) -> list[dict]:
    """Extrae ítems + specs requeridas del DBC. Procesa la región de fichas técnicas
    por chunks (el DBC supera el TPM de Groq en un solo request) y une los ítems."""
    if not texto or not texto.strip() or not GROQ_API_KEY:
        return []
    region = _region_specs(texto)
    items: list[dict] = []
    i = n = 0
    while i < len(region) and n < max_chunks:
        trozo = region[i:i + chunk]
        payload = {
            "model": GROQ_MODEL, "temperature": 0,
            "messages": [
                {"role": "system", "content": DBC_SYSTEM},
                {"role": "user", "content": "Texto del DBC / fichas técnicas:\n" + trozo},
            ],
        }
        resp = _request(payload)
        if resp:
            try:
                items += _parse_array(resp["choices"][0]["message"]["content"])
            except Exception:
                pass
        i += chunk - solapa
        n += 1
        if i < len(region) and n < max_chunks:
            time.sleep(30)  # throttle entre chunks (TPM Groq 8000)
    return _dedup_items(items)


def _bloque_catalogo(catalogo: list[str] | None) -> str:
    """Catálogo real del usuario (del ERP): la señal positiva más fuerte."""
    if not catalogo:
        return ""
    return ("\n\nCATÁLOGO REAL del usuario — productos que EFECTIVAMENTE oferta en "
            "licitaciones (su negocio real). Tratá como relevante (relevante=true) "
            "toda convocatoria de estos productos o equivalentes/variantes:\n"
            + "\n".join(f"- {t}" for t in catalogo[:80]))


def clasificar_lote(objetos: list[str], ejemplos_pos: list[str] | None = None,
                    ejemplos_neg: list[str] | None = None,
                    catalogo: list[str] | None = None) -> list[dict]:
    """objetos: lista de textos. Devuelve lista alineada de
    {relevante: bool, razon: str}. Ante fallo total, todo relevante=False.
    catalogo: productos reales del ERP (positivo fuerte). ejemplos_pos/neg:
    few-shot de las decisiones del usuario en el radar."""
    if not objetos:
        return []
    if not GROQ_API_KEY:
        print("      ⚠ GROQ_API_KEY no configurada; filtro IA desactivado.", flush=True)
        return [{"relevante": False, "razon": "IA sin API key"} for _ in objetos]

    system_prompt = (SYSTEM_PROMPT + _bloque_catalogo(catalogo)
                     + _bloque_ejemplos(ejemplos_pos, ejemplos_neg))

    resultados: list[dict] = [None] * len(objetos)  # type: ignore

    for base in range(0, len(objetos), LOTE):
        trozo = objetos[base:base + LOTE]
        listado = "\n".join(f"{i}. {t}" for i, t in enumerate(trozo))
        payload = {
            "model": GROQ_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Clasifica estos objetos de contratación:\n" + listado},
            ],
        }
        resp = _request(payload)
        parsed = []
        if resp:
            try:
                parsed = _parse_array(resp["choices"][0]["message"]["content"])
            except Exception:
                parsed = []
        # mapear por indice
        por_i = {}
        for obj in parsed:
            try:
                por_i[int(obj.get("i"))] = obj
            except Exception:
                continue
        for k in range(len(trozo)):
            obj = por_i.get(k)
            if obj is None:
                resultados[base + k] = {"relevante": False, "razon": "IA sin respuesta"}
            else:
                resultados[base + k] = {
                    "relevante": bool(obj.get("relevante")),
                    "razon": str(obj.get("razon", ""))[:120],
                }
    return resultados
