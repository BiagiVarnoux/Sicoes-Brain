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


def _request(payload: dict, intentos: int = 3) -> dict | None:
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
                espera = 5 * (i + 1)
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


def clasificar_lote(objetos: list[str], ejemplos_pos: list[str] | None = None,
                    ejemplos_neg: list[str] | None = None) -> list[dict]:
    """objetos: lista de textos. Devuelve lista alineada de
    {relevante: bool, razon: str}. Ante fallo total, todo relevante=False.
    ejemplos_pos/neg: few-shot del criterio real del usuario (opcional)."""
    if not objetos:
        return []
    if not GROQ_API_KEY:
        print("      ⚠ GROQ_API_KEY no configurada; filtro IA desactivado.", flush=True)
        return [{"relevante": False, "razon": "IA sin API key"} for _ in objetos]

    system_prompt = SYSTEM_PROMPT + _bloque_ejemplos(ejemplos_pos, ejemplos_neg)

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
