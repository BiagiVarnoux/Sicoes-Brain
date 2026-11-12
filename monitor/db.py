"""
Capa Supabase para el radar — tabla `convocatorias_radar`.
Reutiliza el patrón de reintentos de red del scraper (no crashear por un blip).
"""
import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

TABLA = "convocatorias_radar"


def _headers(extra: dict = {}) -> dict:
    base = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    base.update(extra)
    return base


def _urlopen_retry(req, timeout: int = 20, intentos: int = 4):
    ultimo = None
    for i in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError:
            raise
        except Exception as e:
            ultimo = e
            espera = 2 ** i
            print(f"      ⚠ Supabase red falló ({type(e).__name__}); reintento {i+1}/{intentos} en {espera}s...",
                  flush=True)
            time.sleep(espera)
    raise ultimo


def cuces_existentes(cuces: list[str]) -> set:
    """Devuelve el subconjunto de CUCE que ya está en la tabla (para no re-procesar)."""
    if not cuces:
        return set()
    vistos = set()
    # consultar en bloques por si la lista es larga (límite de URL)
    for base in range(0, len(cuces), 100):
        trozo = cuces[base:base + 100]
        lista = ",".join(f'"{c}"' for c in trozo)
        path = f"{TABLA}?cuce=in.({lista})&select=cuce"
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
        try:
            _s, body = _urlopen_retry(req, timeout=15)
            for row in json.loads(body):
                vistos.add(row["cuce"])
        except Exception as e:
            print(f"      ⚠ No se pudo consultar existentes: {e}", flush=True)
    return vistos


def cuces_con_dbc(cuces: list[str]) -> set:
    """Devuelve el subconjunto de CUCE que ya tiene su DBC descargado
    (dbc_descargado=True). Sirve para reanudar una corrida interrumpida sin
    volver a bajar y re-procesar lo ya hecho."""
    if not cuces:
        return set()
    vistos = set()
    for base in range(0, len(cuces), 100):
        trozo = cuces[base:base + 100]
        lista = ",".join(f'"{c}"' for c in trozo)
        path = f"{TABLA}?cuce=in.({lista})&dbc_descargado=is.true&select=cuce"
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
        try:
            _s, body = _urlopen_retry(req, timeout=15)
            for row in json.loads(body):
                vistos.add(row["cuce"])
        except Exception as e:
            print(f"      ⚠ No se pudo consultar DBC ya descargados: {e}", flush=True)
    return vistos


def catalogo_erp(limite: int = 80) -> list[str]:
    """Catálogo REAL del usuario: productos que efectivamente ofertó en el ERP
    (tabla espejo erp_productos). Deduplicado, 'nombre — especificacion'. Es la
    señal positiva más fuerte para la IA (lo que de verdad maneja/vende)."""
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/erp_productos?select=nombre,especificacion&limit=1000",
        headers=_headers())
    try:
        _s, body = _urlopen_retry(req, timeout=15)
        rows = json.loads(body)
    except Exception:
        return []
    vistos, out = set(), []
    for r in rows:
        nombre = (r.get("nombre") or "").strip()
        if not nombre:
            continue
        espec = (r.get("especificacion") or "").strip()
        texto = f"{nombre} — {espec}" if espec else nombre
        clave = texto.lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        out.append(texto)
        if len(out) >= limite:
            break
    return out


def ejemplos_entrenamiento(limite: int = 25) -> tuple[list[str], list[str]]:
    """Devuelve (positivos, negativos) para enseñarle a la IA el criterio real:
    - positivos: objetos marcados relevantes que el usuario NO descartó.
    - negativos: objetos descartados específicamente por motivo 'producto'
      (los únicos que son señal de que esa CATEGORÍA de producto no va).
    Los descartes por precio/plazos/especificaciones/etc. NO entran (son de la
    convocatoria puntual, no del producto)."""
    def _objetos(path: str) -> list[str]:
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
        try:
            _s, body = _urlopen_retry(req, timeout=15)
            return [r["objeto"] for r in json.loads(body) if r.get("objeto")]
        except Exception:
            return []
    pos = _objetos(f"{TABLA}?relevante=eq.true&descartado=eq.false&select=objeto&limit={limite}")
    neg = _objetos(f"{TABLA}?descartado=eq.true&motivo_descarte=cs.%7Bproducto%7D&select=objeto&limit={limite}")

    # Ejemplos curados a mano (camino 1): van PRIMERO — son "gold" y cubren los
    # títulos genéricos ("Papel", "Material de Escritorio") que el diccionario no
    # caza. Se deduplican contra los de la BD por texto normalizado.
    try:
        import ejemplos_curados as _ec
        cur_pos, cur_neg = list(_ec.POSITIVOS), list(_ec.NEGATIVOS)
    except Exception:
        cur_pos, cur_neg = [], []

    def _merge(curados: list[str], bd: list[str]) -> list[str]:
        import unicodedata, re as _re
        def _norm(s: str) -> str:
            s = unicodedata.normalize("NFKD", s or "")
            s = "".join(c for c in s if not unicodedata.combining(c)).lower()
            return _re.sub(r"\s+", " ", s).strip()
        vistos, out = set(), []
        for o in curados + bd:
            k = _norm(o)
            if not k or k in vistos:
                continue
            vistos.add(k)
            out.append(o)
            if len(out) >= limite:
                break
        return out

    return _merge(cur_pos, pos), _merge(cur_neg, neg)


def upsert(rows: list[dict]) -> dict:
    """Inserta/actualiza por CUCE. Devuelve {ok, count} o {error}."""
    if not rows:
        return {"ok": True, "count": 0}
    url = f"{SUPABASE_URL}/rest/v1/{TABLA}?on_conflict=cuce"
    req = urllib.request.Request(
        url, data=json.dumps(rows).encode(), method="POST",
        headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
    )
    try:
        status, _body = _urlopen_retry(req)
        return {"ok": True, "count": len(rows), "status": status}
    except urllib.error.HTTPError as e:
        try:
            cuerpo = e.read().decode()
        except Exception:
            cuerpo = f"HTTP {e.code} (cuerpo ilegible)"
        return {"error": cuerpo}
    except Exception as e:
        return {"error": f"red: {e}"}


def registrar_corrida(fecha_corrida: str, fecha_desde: str | None = None,
                      fecha_hasta: str | None = None) -> None:
    """Agrega una fila a la bitácora `radar_corridas`: cuándo corrió el radar y qué
    rango de fechas de publicación escaneó. Fechas en ISO (yyyy-mm-dd). No crashea."""
    payload = {"fecha_corrida": fecha_corrida}
    if fecha_desde:
        payload["fecha_desde"] = fecha_desde
    if fecha_hasta:
        payload["fecha_hasta"] = fecha_hasta
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/radar_corridas",
        data=json.dumps([payload]).encode(), method="POST",
        headers=_headers({"Prefer": "return=minimal"}),
    )
    try:
        _urlopen_retry(req)
    except Exception as e:
        print(f"      ⚠ No se pudo registrar la corrida en radar_corridas: {e}", flush=True)


def limpiar_storage_descartados() -> int:
    """Borra los archivos del bucket Storage y limpia los campos dbc_* de las
    convocatorias descartadas que aún tengan archivos. Devuelve filas afectadas."""
    import json as _json
    import urllib.parse as _up
    BUCKET = "dbc"
    # 1) obtener CUCEs descartados con archivos
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{TABLA}?descartado=eq.true&dbc_archivos=not.is.null&select=cuce",
        headers=_headers(),
    )
    try:
        _s, body = _urlopen_retry(req, timeout=15)
        cuces = [r["cuce"] for r in _json.loads(body) if r.get("cuce")]
    except Exception as e:
        print(f"      ⚠ limpiar_storage_descartados (query): {e}", flush=True)
        return 0
    if not cuces:
        return 0
    h_storage = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json"}
    borrados = 0
    for cuce in cuces:
        try:
            req_list = urllib.request.Request(
                f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}",
                data=_json.dumps({"prefix": f"{cuce}/", "limit": 100}).encode(),
                method="POST", headers=h_storage,
            )
            objs = _json.loads(urllib.request.urlopen(req_list, timeout=20).read())
            prefixes = [f"{cuce}/{o['name']}" for o in objs if o.get("name")]
            if prefixes:
                req_del = urllib.request.Request(
                    f"{SUPABASE_URL}/storage/v1/object/{BUCKET}",
                    data=_json.dumps({"prefixes": prefixes}).encode(),
                    method="DELETE", headers=h_storage,
                )
                urllib.request.urlopen(req_del, timeout=20).read()
            borrados += 1
        except Exception as e:
            print(f"      ⚠ limpiar_storage_descartados ({cuce}): {e}", flush=True)
    # 2) limpiar campos en la DB
    if borrados:
        url = (f"{SUPABASE_URL}/rest/v1/{TABLA}"
               f"?descartado=eq.true&dbc_archivos=not.is.null")
        payload = {"dbc_archivos": None, "dbc_path": None, "dbc_descargado": False}
        req_patch = urllib.request.Request(
            url, data=_json.dumps(payload).encode(),
            method="PATCH", headers=_headers({"Prefer": "return=minimal"}),
        )
        try:
            _urlopen_retry(req_patch)
        except Exception as e:
            print(f"      ⚠ limpiar_storage_descartados (patch): {e}", flush=True)
    return borrados


def limpiar_documentos_vencidos() -> int:
    """Borra los documentos (archivos, dbc_archivos, dbc_path) de convocatorias
    cuya fecha_presentacion ya pasó. Devuelve el número de filas afectadas."""
    url = (f"{SUPABASE_URL}/rest/v1/{TABLA}"
           f"?fecha_presentacion=lt.{__import__('datetime').date.today().isoformat()}")
    payload = {"archivos": None, "dbc_archivos": None, "dbc_path": None, "dbc_descargado": False}
    req = urllib.request.Request(
        url, data=__import__('json').dumps(payload).encode(),
        method="PATCH", headers=_headers({"Prefer": "return=minimal,count=exact"}),
    )
    try:
        status, _body = _urlopen_retry(req)
        return 0
    except Exception as e:
        print(f"      ⚠ limpiar_documentos_vencidos falló: {e}", flush=True)
        return 0


def marcar_dbc(cuce: str, dbc_path: str, dbc_archivos: list | None = None,
               dbc_markdown: str | None = None) -> None:
    """Actualiza la ruta local, archivos subidos y markdown del DBC para un CUCE."""
    payload = {"dbc_path": dbc_path, "dbc_descargado": True}
    if dbc_archivos is not None:
        payload["dbc_archivos"] = dbc_archivos
    if dbc_markdown is not None:
        payload["dbc_markdown"] = dbc_markdown
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{TABLA}?cuce=eq.{urllib.parse.quote(cuce)}",
        data=json.dumps(payload).encode(),
        method="PATCH", headers=_headers(),
    )
    try:
        _urlopen_retry(req)
    except Exception as e:
        print(f"      ⚠ No se pudo marcar DBC de {cuce}: {e}", flush=True)
