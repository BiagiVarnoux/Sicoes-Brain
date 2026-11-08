"""
Pasada 1 — Propuesta de taxonomía (canonicalización de productos)
=================================================================
Lee las descripciones distintas de `hist_items` y le pide a Gemini (Google AI
Studio) que ETIQUETE cada una con una rama jerárquica + atributos. Después
agrega TODO localmente por rama para armar un árbol de taxonomía PROPUESTO
(categoría → subcategoría → producto canónico), con conteos y los atributos
discriminantes vistos en cada hoja.

NO toca la base de datos: solo genera dos archivos para que el usuario los CURE
una vez:
  - taxonomia_propuesta.json  (estructurado, para la Pasada 2)
  - taxonomia_propuesta.md    (árbol legible para revisar/editar a ojo)

Por qué este diseño (ver memoria canonicalizacion-diseno):
  * Esto es ENTITY RESOLUTION, no clasificación. El UNSPSC / el prefijo de
    categoría que traen las entidades es RUIDO y NO se usa como verdad.
  * El método es EXTRACCIÓN DE ATRIBUTOS → llave determinista, no embeddings.
    La IA extrae campos (marca, modelo del consumible, capacidad, medida…) y la
    hoja se arma con esos campos, no por parecido de texto.
  * La hoja es el PRODUCTO COMPRABLE EQUIVALENTE. Para un tóner discrimina el
    modelo DEL CONSUMIBLE (78A, TN-225C), NO para qué impresora es. La medida/
    ancho SÍ separa (62mm ≠ 102mm).
  * El merge entre lotes es local/determinista: el modelo etiqueta ítem por
    ítem y acá se agrupan por (categoría, subcategoría, producto). Re-ejecutable.

Correr (desde monitor/):
  ../scraper/venv/bin/python canonicalizar_taxonomia.py            # corpus completo
  ../scraper/venv/bin/python canonicalizar_taxonomia.py --muestra 300   # prueba rápida
"""
import os
import re
import sys
import json
import time
import argparse
import urllib.request
import urllib.error
import urllib.parse

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip()
GOOGLE_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GOOGLE_MODEL}:generateContent"
)

# --- Groq (backend alternativo, más robusto: no da 503 como Gemini) ---
# Keys DEDICADAS a canonicalización para no tocar el cupo del radar. Orden de
# failover: CANON → CANON_2 → (último recurso) GROQ_API_KEY_2 del radar.
GROQ_CANON_KEYS = [k for k in (
    os.environ.get("GROQ_API_KEY_CANON", "").strip(),
    os.environ.get("GROQ_API_KEY_CANON_2", "").strip(),
    os.environ.get("GROQ_API_KEY_2", "").strip(),   # colchón del radar
) if k]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL_CANON = os.environ.get("GROQ_MODEL_CANON", "openai/gpt-oss-120b").strip()

LOTE = 40            # descripciones por request (cuello real = TPM, troceamos)
PAUSA_RPM = 4.2      # seg entre requests (~15 RPM free tier Gemini, con colchón)

SYSTEM = (
    "Sos un experto en catalogación de bienes de compras públicas de Bolivia "
    "(SICOES). Te paso una lista de descripciones de ítems comprados. Tu tarea "
    "es ubicar cada ítem en un ÁRBOL de productos, pensando en 'qué producto "
    "comprable es', NO en el texto literal.\n\n"
    "REGLAS CLAVE:\n"
    "1) IGNORÁ cualquier prefijo de categoría antes de ' — ': es el código "
    "UNSPSC que carga la entidad y es RUIDO poco confiable. Guiate por la "
    "descripción real.\n"
    "2) La HOJA (producto_canonico) es el producto comprable equivalente: dos "
    "ítems que un proveedor cotizaría como el MISMO artículo van a la misma "
    "hoja. Distinguí por los atributos FÍSICOS/FUNCIONALES del propio producto "
    "(marca, modelo del consumible como '78A' o 'TN-225C', capacidad, medida/"
    "ancho, generación), NO por para qué máquina es. Ej.: un tóner lo define su "
    "propio modelo (78A), no la impresora que lo usa. La medida SÍ separa "
    "(62mm ≠ 102mm).\n"
    "3) Estructura jerárquica de profundidad variable: categoria (familia "
    "amplia, ej 'Tóner y cartuchos', 'Memoria RAM', 'Etiquetas autoadhesivas'), "
    "subcategoria (puede ser null si no aplica) y producto_canonico (la hoja). "
    "Algunos productos son hoja directa de la categoría (subcategoria=null).\n"
    "4) atributos: objeto con SOLO los campos que de verdad discriminan esa "
    "hoja (ej {\"marca\":\"HP\",\"modelo\":\"78A\"} o {\"formato\":\"SODIMM\","
    "\"generacion\":\"DDR4\",\"capacidad_gb\":8}). Vacío {} si no hay atributos "
    "finos.\n\n"
    "Respondé EXCLUSIVAMENTE un array JSON, un objeto por ítem, MISMO orden, con "
    "forma: [{\"i\":<indice>,\"categoria\":\"...\",\"subcategoria\":<str|null>,"
    "\"producto_canonico\":\"...\",\"atributos\":{...}}]. Sin texto extra."
)


# ---------------------------------------------------------------- Supabase
def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def leer_descripciones(muestra: int | None) -> list[str]:
    """Trae las descripciones DISTINTAS de hist_items (ordenadas, para que la
    propuesta sea reproducible). Con --muestra N toma solo las primeras N."""
    offset, out, vistas = 0, [], set()
    paso = 1000
    while True:
        path = (f"hist_items?select=descripcion&descripcion=not.is.null"
                f"&order=descripcion.asc&limit={paso}&offset={offset}")
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}",
                                     headers=_sb_headers())
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read())
        if not rows:
            break
        for row in rows:
            d = (row.get("descripcion") or "").strip()
            clave = d.lower()
            if d and clave not in vistas:
                vistas.add(clave)
                out.append(d)
        offset += paso
        if muestra and len(out) >= muestra:
            return out[:muestra]
    return out


# ---------------------------------------------------------------- Gemini
def _espera_http(code: int, intento: int) -> int:
    """Backoff. 429 (rate)/500/503 (sobrecarga) son transitorios → espera larga
    y creciente, con techo de 60s. Resto, backoff corto."""
    if code in (429, 500, 503):
        return min(60, 8 * (2 ** intento))   # 8,16,32,60,60,60…
    return 4 * (intento + 1)


def _gemini(system: str, user: str, intentos: int = 7):
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0,
        },
    }
    url = f"{GEMINI_URL}?key={urllib.parse.quote(GOOGLE_API_KEY)}"
    for intento in range(intentos):
        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(), method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
            texto = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(texto)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode(errors="ignore")[:120].replace("\n", " ")
            espera = _espera_http(e.code, intento)
            print(f"      ⚠ Gemini HTTP {e.code}: {cuerpo} → reintento en {espera}s",
                  flush=True)
            time.sleep(espera)
        except Exception as e:
            print(f"      ⚠ Gemini {type(e).__name__}: {e} → reintento",
                  flush=True)
            time.sleep(4 * (intento + 1))
    return None


# ---------------------------------------------------------------- Groq backend
_groq_idx = 0
_groq_agotadas: set[int] = set()


def _extraer_json(texto: str):
    """Groq a veces envuelve el JSON en texto/```json. Recorta al primer [ o {
    y al último ] o } correspondiente."""
    t = texto.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    for ab, ce in (("[", "]"), ("{", "}")):
        i, j = t.find(ab), t.rfind(ce)
        if 0 <= i < j:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                continue
    return None


def _groq_chat(system: str, user: str, intentos: int = 8):
    """POST a Groq con FAILOVER entre las keys de canonicalización. Devuelve el
    objeto/array parseado, o None. Marca keys sin cupo DIARIO (TPD) para no
    reintentarlas en esta corrida."""
    global _groq_idx
    if not GROQ_CANON_KEYS:
        return None
    payload = {
        "model": GROQ_MODEL_CANON,
        "temperature": 0,
        # gpt-oss son modelos de RAZONAMIENTO: sin esto gastan todo el presupuesto
        # de salida en 'reasoning' y devuelven content vacío (finish=length).
        "reasoning_effort": "low",
        "max_completion_tokens": 8000,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    data = json.dumps(payload).encode()
    for intento in range(intentos):
        if len(_groq_agotadas) >= len(GROQ_CANON_KEYS):
            print("      ✗ todas las keys Groq sin cupo diario (TPD)", flush=True)
            return None
        while _groq_idx in _groq_agotadas:
            _groq_idx = (_groq_idx + 1) % len(GROQ_CANON_KEYS)
        key = GROQ_CANON_KEYS[_groq_idx]
        try:
            req = urllib.request.Request(
                GROQ_URL, data=data, method="POST",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         # el WAF de Groq (Cloudflare) banea el UA de urllib → 403 code 1010
                         "User-Agent": "curl/8.4.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read())
            ch = resp["choices"][0]
            parsed = _extraer_json(ch["message"].get("content", "") or "")
            if parsed is not None:
                return parsed
            # 200 pero no parseable (truncado o texto basura): reintentar, no rendirse
            print(f"      ⚠ Groq 200 no-parseable (finish={ch.get('finish_reason')}) "
                  f"→ reintento", flush=True)
            time.sleep(3)
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode(errors="ignore").lower()
            es_tpd = "tpd" in cuerpo or "per day" in cuerpo or "requests per day" in cuerpo
            if e.code == 429 and es_tpd:
                print(f"      ⚠ Groq key #{_groq_idx+1} sin cupo DIARIO → salto de cuenta",
                      flush=True)
                _groq_agotadas.add(_groq_idx)
                _groq_idx = (_groq_idx + 1) % len(GROQ_CANON_KEYS)
                continue
            if e.code == 429:
                # 429 por MINUTO (TPM/RPM): hay que ESPERAR (cambiar de key no
                # ayuda si la otra también está caliente). Respetar Retry-After.
                ra = e.headers.get("retry-after") if e.headers else None
                try:
                    espera = max(2, int(float(ra))) if ra else min(60, 6 * (2 ** intento))
                except ValueError:
                    espera = min(60, 6 * (2 ** intento))
                print(f"      ⚠ Groq 429 por minuto → espera {espera}s y reintento",
                      flush=True)
                time.sleep(espera)
                _groq_idx = (_groq_idx + 1) % len(GROQ_CANON_KEYS)  # rotar por las dudas
                continue
            espera = min(60, 5 * (2 ** intento))
            print(f"      ⚠ Groq HTTP {e.code} → reintento en {espera}s", flush=True)
            time.sleep(espera)
        except Exception as e:
            print(f"      ⚠ Groq {type(e).__name__}: {e} → reintento", flush=True)
            time.sleep(4 * (intento + 1))
    return None


# ---------------------------------------------------------------- Despachador
BACKEND = "groq"   # se fija en main() según --backend


def llamar(system: str, user: str):
    """Llama al backend elegido. Devuelve el objeto/array parseado o None."""
    if BACKEND == "groq":
        return _groq_chat(system, user)
    return _gemini(system, user)


# ---------------------------------------------------------------- Consolidación
CONSOLIDA_SYS = (
    "Te paso una lista de nombres de {que} de productos de compras públicas. "
    "Varios son SINÓNIMOS o variantes del mismo concepto (mayúsculas, plural, "
    "un término más amplio vs otro: ej 'Aires acondicionados' y 'Climatización' "
    "son lo mismo). Unificá los sinónimos bajo UN nombre canónico claro y "
    "general. NO fusiones conceptos genuinamente distintos. "
    "Respondé EXCLUSIVAMENTE un objeto JSON {{\"<nombre crudo>\":\"<nombre "
    "canónico>\"}} con TODOS los nombres de entrada como clave. Sin texto extra."
)


def _mapa(system: str, user: str) -> dict | None:
    obj = llamar(system, user)
    return obj if isinstance(obj, dict) else None


def consolidar_categorias(etiquetas: list[dict]) -> None:
    """Un solo request a Gemini: mapea los nombres de categoría crudos (que
    derivan entre lotes) a un conjunto canónico, y remapea in-place.
    Después consolida las subcategorías DENTRO de cada categoría ya canónica."""
    # --- categorías
    crudas = sorted({_norm(e.get("categoria")) for e in etiquetas if _norm(e.get("categoria"))})
    if len(crudas) > 1:
        mapa = _mapa(CONSOLIDA_SYS.format(que="categorías"),
                                "\n".join(f"- {c}" for c in crudas))
        if mapa:
            n_antes = len(crudas)
            for e in etiquetas:
                c = _norm(e.get("categoria"))
                if c in mapa and _norm(mapa[c]):
                    e["categoria"] = _norm(mapa[c])
            n_desp = len({_norm(e.get("categoria")) for e in etiquetas if _norm(e.get("categoria"))})
            print(f"  consolidación: {n_antes} → {n_desp} categorías", flush=True)
        else:
            print("  ⚠ consolidación de categorías falló; se deja sin unificar", flush=True)

    # --- subcategorías (con contexto de su categoría ya canónica)
    pares = sorted({(_norm(e.get("categoria")), _norm(e.get("subcategoria")))
                    for e in etiquetas if _norm(e.get("subcategoria"))})
    if len(pares) > 1:
        etiq = [f"{cat} › {sub}" for cat, sub in pares]
        mapa = _mapa(
            CONSOLIDA_SYS.format(que="subcategorías (formato 'Categoría › Subcategoría')"),
            "\n".join(f"- {x}" for x in etiq))
        if mapa:
            # el valor canónico puede venir como 'Cat › Sub' o solo 'Sub'; tomo lo último
            def _solo_sub(v: str) -> str:
                return _norm(v.split("›")[-1])
            lut = {f"{cat} › {sub}": _solo_sub(mapa[f"{cat} › {sub}"])
                   for cat, sub in pares if f"{cat} › {sub}" in mapa and _norm(mapa[f"{cat} › {sub}"])}
            for e in etiquetas:
                cat, sub = _norm(e.get("categoria")), _norm(e.get("subcategoria"))
                clave = f"{cat} › {sub}"
                if clave in lut:
                    e["subcategoria"] = lut[clave]


LEAF_SYS = (
    "Te paso HOJAS de producto de la categoría «{cat}», una por línea, en formato "
    "'subcategoría :: producto' (la subcategoría puede ser 'null'). Varias líneas "
    "son EXACTAMENTE EL MISMO producto comprable escrito distinto (mayúsculas, "
    "con o sin marca, códigos equivalentes: ej 'HP 78A', '78A' y 'CE278A' son el "
    "MISMO cartucho HP). Fusionalas bajo UNA hoja canónica.\n"
    "REGLAS DURAS:\n"
    "1) NO fusiones productos genuinamente distintos. DISTINGUEN siempre: el "
    "modelo del consumible (78A ≠ 78B ≠ 78X), la capacidad (8GB ≠ 16GB), la "
    "medida/ancho (62mm ≠ 102mm, 8×8 ≠ 8×7) y la generación (DDR3 ≠ DDR4).\n"
    "2) Asigná a cada hoja su subcategoría canónica; si una hoja está en una "
    "subcategoría equivocada, corregila para que las iguales queden juntas.\n"
    "Respondé EXCLUSIVAMENTE un objeto JSON con TODAS las líneas de entrada como "
    "clave (tal cual te las paso) y valor '<subcategoría canónica o null> :: "
    "<producto canónico>'. Sin texto extra."
)
HOJAS_POR_REQUEST = 30   # troceo chico: 20b emite JSON confiable y no satura TPM
MIN_HOJAS_CONSOLIDAR = 4  # categorías con menos hojas no se tocan


def _cargar_ck_hojas(path: str) -> dict:
    """{ 'categoria||chunk': {fila_cruda: 'sub :: prod'} } ya resueltos."""
    hecho = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    r = json.loads(linea)
                    hecho[r["clave"]] = r["mapa"]
                except Exception:
                    continue
    return hecho


def consolidar_hojas(etiquetas: list[dict], ck_path: str) -> None:
    """Fusiona, DENTRO de cada categoría ya consolidada, las hojas que son el
    mismo producto (78A = HP 78A = CE278A), troceando por el tope de tokens.
    Remapea (subcategoria, producto) in-place. Reanudable vía checkpoint."""
    por_cat: dict[str, list[int]] = {}
    for idx, e in enumerate(etiquetas):
        por_cat.setdefault(_norm(e.get("categoria")) or "(sin categoría)", []).append(idx)

    hecho = _cargar_ck_hojas(ck_path)
    if hecho:
        print(f"  ↻ checkpoint hojas: {len(hecho)} grupos ya hechos", flush=True)
    ck = open(ck_path, "a", encoding="utf-8")

    cats = sorted(por_cat, key=lambda c: -len(por_cat[c]))
    for cat in cats:
        idxs = por_cat[cat]
        # etiqueta cruda de cada hoja: 'sub :: prod'
        def _fila(e):
            return f"{_norm(e.get('subcategoria')) or 'null'} :: {_norm(e.get('producto_canonico')) or '(sin producto)'}"
        filas = sorted({_fila(etiquetas[i]) for i in idxs})
        if len(filas) < MIN_HOJAS_CONSOLIDAR:
            continue
        mapa_cat: dict[str, str] = {}
        for ci in range(0, len(filas), HOJAS_POR_REQUEST):
            trozo = filas[ci:ci + HOJAS_POR_REQUEST]
            clave = f"{cat}||{ci}"
            if clave in hecho:
                mapa_cat.update(hecho[clave])
                continue
            mapa = _mapa(LEAF_SYS.format(cat=cat), "\n".join(trozo))
            if not mapa:
                print(f"    ⚠ hojas «{cat}» chunk {ci//HOJAS_POR_REQUEST} falló; se deja sin fusionar",
                      flush=True)
                continue
            mapa = {k: v for k, v in mapa.items() if isinstance(v, str)}
            mapa_cat.update(mapa)
            ck.write(json.dumps({"clave": clave, "mapa": mapa}, ensure_ascii=False) + "\n")
            ck.flush()
            if BACKEND == "groq":
                time.sleep(6.0)   # respetar ~8000 TPM por key
        # aplicar el mapa de esta categoría a sus ítems
        for i in idxs:
            fila = _fila(etiquetas[i])
            canon = mapa_cat.get(fila)
            if not canon or "::" not in canon:
                continue
            sub, _, prod = canon.partition("::")
            sub, prod = _norm(sub), _norm(prod)
            etiquetas[i]["subcategoria"] = None if sub.lower() in ("", "null", "none") else sub
            if prod:
                etiquetas[i]["producto_canonico"] = prod
    ck.close()


# ---------------------------------------------------------------- Agregación
def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def agregar(etiquetas: list[dict], descripciones: list[str]) -> dict:
    """Agrupa las etiquetas por rama y arma el árbol con conteos y atributos."""
    # arbol[categoria][subcategoria][producto] = {"n":int, "attr_keys":set, "ej":list}
    arbol: dict = {}
    for et in etiquetas:
        cat = _norm(et.get("categoria")) or "(sin categoría)"
        sub = _norm(et.get("subcategoria")) or None
        prod = _norm(et.get("producto_canonico")) or "(sin producto)"
        attrs = et.get("atributos") or {}
        # El texto va ATADO a la etiqueta (et["desc"]), fijado en el momento de etiquetar.
        # Solo caemos al índice global como respaldo para etiquetas viejas sin "desc".
        desc = et.get("desc")
        if desc is None:
            idx = et.get("i")
            if isinstance(idx, int) and 0 <= idx < len(descripciones):
                desc = descripciones[idx]
        hoja = arbol.setdefault(cat, {}).setdefault(sub, {}).setdefault(
            prod, {"n": 0, "attr_keys": set(), "ejemplos": []})
        hoja["n"] += 1
        if isinstance(attrs, dict):
            hoja["attr_keys"].update(k for k in attrs.keys())
        if desc is not None and len(hoja["ejemplos"]) < 3:
            hoja["ejemplos"].append(desc)
    return arbol


def arbol_a_json(arbol: dict) -> dict:
    cats = []
    for cat in sorted(arbol):
        subs = []
        n_cat = 0
        for sub in sorted(arbol[cat], key=lambda x: (x is None, x or "")):
            hojas = []
            for prod in sorted(arbol[cat][sub]):
                h = arbol[cat][sub][prod]
                n_cat += h["n"]
                hojas.append({
                    "producto_canonico": prod,
                    "n_items": h["n"],
                    "atributos_discriminantes": sorted(h["attr_keys"]),
                    "ejemplos": h["ejemplos"],
                })
            subs.append({"subcategoria": sub,
                         "n_items": sum(x["n_items"] for x in hojas),
                         "productos": hojas})
        cats.append({"categoria": cat, "n_items": n_cat, "subcategorias": subs})
    cats.sort(key=lambda c: c["n_items"], reverse=True)
    return {"categorias": cats,
            "total_hojas": sum(len(s["productos"]) for c in cats for s in c["subcategorias"])}


def arbol_a_md(data: dict) -> str:
    out = ["# Taxonomía propuesta (Pasada 1 — para CURAR)\n",
           f"_{len(data['categorias'])} categorías · {data['total_hojas']} productos canónicos (hojas)_\n",
           "> Revisá y editá: fusionar hojas que son el mismo producto, separar "
           "las que no, corregir atributos. Esto se cura UNA vez.\n"]
    for c in data["categorias"]:
        out.append(f"\n## {c['categoria']}  _(n={c['n_items']})_")
        for s in c["subcategorias"]:
            if s["subcategoria"]:
                out.append(f"\n### {s['subcategoria']}  _(n={s['n_items']})_")
            for p in s["productos"]:
                attr = (" · attrs: " + ", ".join(p["atributos_discriminantes"])) if p["atributos_discriminantes"] else ""
                out.append(f"- **{p['producto_canonico']}** _(n={p['n_items']})_{attr}")
                for ej in p["ejemplos"]:
                    out.append(f"    - _{ej[:120]}_")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- Checkpoint
def _cargar_checkpoint(path: str) -> dict[int, list]:
    """Lee el .jsonl de progreso: {b_inicio_lote: [etiquetas rebaseadas]}."""
    hecho: dict[int, list] = {}
    if not os.path.exists(path):
        return hecho
    with open(path, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                r = json.loads(linea)
                ets = r["etiquetas"]
                # Solo aceptar filas del formato nuevo (cada etiqueta trae su "desc"
                # atado). Las filas viejas mapeaban por índice global y quedaron
                # corridas al crecer el corpus: ignorarlas evita re-barajar.
                if ets and not all(isinstance(e, dict) and "desc" in e for e in ets):
                    continue
                hecho[int(r["b"])] = ets
            except Exception:
                continue
    return hecho


# ---------------------------------------------------------------- Main
def main():
    global BACKEND
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=None,
                    help="procesar solo las primeras N descripciones (prueba rápida)")
    ap.add_argument("--backend", choices=["groq", "gemini"], default="groq",
                    help="motor LLM (default groq: robusto, no da 503)")
    ap.add_argument("--solo-consolidar", action="store_true",
                    help="no etiqueta: reusa el checkpoint y solo (re)consolida "
                         "categorías + hojas, y reescribe los archivos")
    ap.add_argument("--salida", default=os.path.dirname(__file__) or ".")
    args = ap.parse_args()
    BACKEND = args.backend

    if BACKEND == "groq" and not GROQ_CANON_KEYS:
        print("❌ Faltan GROQ_API_KEY_CANON / _CANON_2 en monitor/.env"); sys.exit(1)
    if BACKEND == "gemini" and not GOOGLE_API_KEY:
        print("❌ Falta GOOGLE_API_KEY en monitor/.env"); sys.exit(1)
    modelo = GROQ_MODEL_CANON if BACKEND == "groq" else GOOGLE_MODEL

    print(f"→ Leyendo descripciones distintas de hist_items…", flush=True)
    descripciones = leer_descripciones(args.muestra)
    total = len(descripciones)
    n_lotes = (total + LOTE - 1) // LOTE
    print(f"  {total} descripciones distintas · {n_lotes} lotes de {LOTE} "
          f"(backend {BACKEND} / {modelo})", flush=True)

    # checkpoint: reanuda sin rehacer lotes ya etiquetados (clave = inicio de lote)
    ck_path = os.path.join(args.salida, "taxonomia_checkpoint.jsonl")
    hecho = _cargar_checkpoint(ck_path)
    if hecho:
        print(f"  ↻ checkpoint: {len(hecho)} lotes ya hechos, se saltan", flush=True)

    etiquetas: list[dict] = []
    for b, et_prev in hecho.items():
        etiquetas.extend(et_prev)

    if args.solo_consolidar:
        if not etiquetas:
            print("❌ No hay checkpoint de etiquetas para consolidar"); sys.exit(1)
        print(f"→ Modo solo-consolidar: {len(etiquetas)} ítems del checkpoint "
              "(no se re-etiqueta)", flush=True)
    else:
        ck = open(ck_path, "a", encoding="utf-8")
        for b in range(0, total, LOTE):
            nro = b // LOTE + 1
            if b in hecho:
                continue
            trozo = descripciones[b:b + LOTE]
            print(f"  lote {nro}/{n_lotes} ({len(trozo)} ítems)…", flush=True)
            numeradas = "\n".join(f"{i}. {d}" for i, d in enumerate(trozo))
            res = llamar(SYSTEM, numeradas)
            if not isinstance(res, list):
                print(f"    ✗ lote {nro} falló tras reintentos; se omite (reintentable)",
                      flush=True)
                continue
            # Atar CADA etiqueta a su descripción REAL del lote local (trozo) en el acto.
            # Nunca se re-resuelve por índice global después: así el texto queda inmune a
            # que el corpus cambie de orden/tamaño entre corridas (causa del barajado previo).
            limpio = []
            if len(res) == len(trozo):
                # un objeto por ítem y MISMO orden (lo pedido): mapear por POSICIÓN,
                # señal más fuerte que confiar en que el modelo acertó cada entero "i".
                for pos, et in enumerate(res):
                    if isinstance(et, dict):
                        et["i"] = b + pos
                        et["desc"] = trozo[pos]
                        limpio.append(et)
            else:
                # el modelo omitió/añadió ítems: caer al índice local "i" que reporta.
                for et in res:
                    if not isinstance(et, dict):
                        continue
                    li = et.get("i")
                    if isinstance(li, int) and 0 <= li < len(trozo):
                        et["i"] = b + li
                        et["desc"] = trozo[li]
                        limpio.append(et)
            if not limpio:
                print(f"    ✗ lote {nro}: sin etiquetas mapeables; se omite", flush=True)
                continue
            etiquetas.extend(limpio)
            ck.write(json.dumps({"b": b, "etiquetas": limpio}, ensure_ascii=False) + "\n")
            ck.flush()
            if nro < n_lotes:
                time.sleep(PAUSA_RPM if BACKEND == "gemini" else 2.0)
        ck.close()

    print(f"→ {len(etiquetas)} ítems. Consolidando nombres de categoría/subcategoría…",
          flush=True)
    consolidar_categorias(etiquetas)
    print(f"→ Consolidando hojas (fusión de productos iguales)…", flush=True)
    consolidar_hojas(etiquetas, os.path.join(args.salida, "taxonomia_hojas_ck.jsonl"))
    print(f"→ Agregando árbol…", flush=True)
    arbol = agregar(etiquetas, descripciones)
    data = arbol_a_json(arbol)

    p_json = os.path.join(args.salida, "taxonomia_propuesta.json")
    p_md = os.path.join(args.salida, "taxonomia_propuesta.md")
    with open(p_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(p_md, "w", encoding="utf-8") as f:
        f.write(arbol_a_md(data))

    print(f"✓ {len(data['categorias'])} categorías, {data['total_hojas']} hojas")
    print(f"✓ {p_json}")
    print(f"✓ {p_md}  ← revisá/curá este")


if __name__ == "__main__":
    main()
