r"""
SCRAPER HISTÓRICO POR ENTIDAD — backbone (sin IA).
===================================================
Para una entidad y un año, barre los Bienes adjudicados (modalidades CM, ANPE,
ANPP, LP) y, por cada proceso, PARSEA LOS FORMULARIOS de forma determinista
(cero tokens) y escribe:
  · hist_procesos  — un renglón por proceso
  · hist_items     — un renglón por ítem (requerido + adjudicado fusionados)

Las especificaciones finas del DBC las agrega DESPUÉS `historico_specs.py` (IA).
Acá solo se baja el DBC (.docx), se recorta y se guarda en disco para esa 2ª fase,
y se marca hist_procesos.tiene_dbc.

Fuentes por modalidad (ver memoria historico-mapa-forms):
  CM            → FORM110 (requerido) + FORM220 (adjudicado, trae todo)
  ANPE/ANPP/LP  → FORM100 (requerido, precio ref) + FORM200 (adjudicado + proveedor) + DBC

Reusa la maquinaria ya validada del probe (navegación, apertura de forms, descarga)
y los parsers probados del scraper viejo.

USO (o doble clic en "Correr Historico.command"):
  ./venv/bin/python historico.py --entidad 0660-10 --anio 2024 --n 10    # prueba (10 procesos)
  ./venv/bin/python historico.py --entidad 0660-10 --anio 2024           # TODO el año (todas las páginas)
  ./venv/bin/python historico.py --entidad 0660-10 --anio 2024 --paginas 2  # cap de páginas
  ./venv/bin/python historico.py --entidad 0660-10 --anio 2024 --reparse # re-scrapea los ya hechos
"""
import argparse
import asyncio
import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from playwright.async_api import async_playwright

# Maquinaria de navegación/descarga ya validada en el probe.
from probe_historico import (
    MODALIDADES, ir_a_buscador, buscar, extraer_filas,
    descargar_token, abrir_formulario_html, keepalive,
    _a_markdown, _recortar_dbc, _sanitizar_fs, CDP_URL,
)
# Parsers deterministas probados del scraper viejo.
from sicoes_items_cdp import (
    parsear_form200_100, parsear_form220_110, parsear_descripcion, limpiar,
    ir_pagina,
)
from bs4 import BeautifulSoup

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

BASE_OUT = os.path.join(os.path.dirname(__file__), "salidas")

# Qué forms abrir según modalidad (ítems). El FORM500 (recepción) se abre siempre.
FORM_REQUERIDO = {"CM": "FORM110", "ANPE": "FORM100", "ANPP": "FORM100", "LP": "FORM100"}
FORM_ADJUDICADO = {"CM": "FORM220", "ANPE": "FORM200", "ANPP": "FORM200", "LP": "FORM200"}


# ─── Supabase REST ────────────────────────────────────────────────────────────
def _get(path: str) -> list:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=H)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _post(tabla: str, rows: list, prefer: str = "resolution=merge-duplicates,return=minimal",
          on_conflict: str = "") -> None:
    if not rows:
        return
    url = f"{SUPABASE_URL}/rest/v1/{tabla}"
    if on_conflict:
        url += f"?on_conflict={on_conflict}"
    req = urllib.request.Request(
        url, data=json.dumps(rows).encode(), method="POST",
        headers={**H, "Content-Type": "application/json", "Prefer": prefer})
    with urllib.request.urlopen(req, timeout=60) as r:
        r.read()


def _delete(path: str) -> None:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", method="DELETE",
                                 headers={**H, "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def _cuces_ya_hechos(entidad: str, anio: int) -> set:
    anio2 = str(anio)[2:]
    rows = _get(f"hist_procesos?select=cuce&entidad_codigo=eq.{urllib.parse.quote(entidad)}"
                f"&cuce_anio=eq.{anio}")
    return {r["cuce"] for r in rows}


# ─── utilidades ───────────────────────────────────────────────────────────────
def _parse_fecha(txt: str) -> str | None:
    """'dd/mm/yyyy' (o con hora) → 'yyyy-mm-dd'. None si no parsea."""
    if not txt:
        return None
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", txt)
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _anio_de_cuce(cuce: str) -> int | None:
    m = re.match(r"(\d{2})-", cuce)
    return 2000 + int(m.group(1)) if m else None


def _norm_desc(s: str) -> str:
    """Normaliza una descripción para emparejar entre formularios: mayúsculas y
    solo alfanuméricos (ignora espacios, puntuación y acentos)."""
    import unicodedata
    if not s:
        return ""
    t = unicodedata.normalize("NFKD", s)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", t.upper())


def _fusionar_items(req_items: list, adj_items: list, fila: dict) -> list:
    """Fusiona ítems requeridos y adjudicados. Base: adjudicados (traen proveedor +
    precio adjudicado). El precio_referencial se trae del requerido emparejando por
    DESCRIPCIÓN (no por nro_item: el SICOES numera distinto cada formulario).
    Los ítems solo-requeridos (p.ej. no adjudicados) también se incluyen."""
    # índice de requeridos por descripción normalizada (lista, por si hay repetidos)
    req_by_desc: dict[str, list] = {}
    for it in (req_items or []):
        req_by_desc.setdefault(_norm_desc(it.get("descripcion_producto")), []).append(it)
    req_restantes = {k: list(v) for k, v in req_by_desc.items()}
    filas_out = []

    def base_row(it: dict) -> dict:
        return {
            "nro_item": it.get("nro_item"),
            "unspsc_codigo": it.get("unspsc_codigo"),
            "descripcion": it.get("descripcion_producto"),
            "unidad_medida": it.get("unidad_medida"),
            "cantidad": it.get("cantidad"),
            "precio_referencial": it.get("precio_referencial"),
            "precio_adjudicado": it.get("precio_adjudicado"),
            "monto_total": it.get("monto_total"),
            "proveedor": it.get("_proveedor_nombre"),
            "fuente": it.get("fuente_formulario"),
        }

    for it in (adj_items or []):
        row = base_row(it)
        # emparejar con el requerido por descripción (pop para no reusar el mismo)
        key = _norm_desc(it.get("descripcion_producto"))
        cola = req_restantes.get(key)
        req = cola.pop(0) if cola else None
        if req:
            if row.get("precio_referencial") is None:
                row["precio_referencial"] = req.get("precio_referencial")
            if not row.get("descripcion"):
                row["descripcion"] = req.get("descripcion_producto")
            if not row.get("unidad_medida"):
                row["unidad_medida"] = req.get("unidad_medida")
            if row.get("cantidad") is None:
                row["cantidad"] = req.get("cantidad")
            if not row.get("unspsc_codigo"):
                row["unspsc_codigo"] = req.get("unspsc_codigo")
        filas_out.append(row)

    # ítems solo requeridos (no aparecieron en adjudicados)
    for cola in req_restantes.values():
        for it in cola:
            filas_out.append(base_row(it))

    return filas_out


def _num(txt: str) -> float | None:
    """Texto → float. Soporta formatos del SICOES: coma decimal ('15399,9'),
    miles con punto + coma decimal ('152.000,00') y punto decimal ('15399.9').
    Regla: si hay ambos separadores, el ÚLTIMO es el decimal; si solo hay coma,
    la coma es decimal. None si no hay número."""
    if not txt:
        return None
    t = re.sub(r"[^\d.,\-]", "", str(txt))
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):          # coma es el decimal
            t = t.replace(".", "").replace(",", ".")
        else:                                     # punto es el decimal
            t = t.replace(",", "")
    elif "," in t:                                # solo coma → decimal boliviano
        t = t.replace(",", ".")
    elif t.count(".") > 1:                        # varios puntos → todos son miles
        t = t.replace(".", "")
    try:
        return float(t) if t not in ("", "-", ".") else None
    except ValueError:
        return None


def _h(s: str) -> str:
    """Normaliza un encabezado: minúsculas, sin acentos, espacios colapsados."""
    import unicodedata
    t = unicodedata.normalize("NFKD", s or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t.lower()).strip()


# Encabezado (subcadena normalizada) → clave de salida. Se mapea por NOMBRE, no por
# posición, porque el nº de columnas del FORM500 varía entre modalidades.
_COLS_500 = {
    "razon social": "proveedor",
    "firma de contrato": "fecha_firma",
    "estado de la recepcion": "estado",
    "recepcionada": "cantidad_recibida",           # "Cantidad Recepcionada/No Recepcionada"
    "recepcion definitiva": "fecha_definitiva",
    "recepcion provisional": "fecha_provisional",
    "recepcion segun contrato": "fecha_contrato",
    "monto real ejecutado": "monto_ejecutado",
    "descripcion del bien": "descripcion",
}


def parsear_form500(html: str) -> list[dict]:
    """Sección 3 del FORM500 (Recepción). Una fila por ítem. Mapea columnas por
    NOMBRE de encabezado (robusto ante variación de nº de columnas entre modalidades)
    y devuelve, por ítem: detalle de specs (llave de cruce), proveedor, firma, estado,
    cantidad recibida, monto ejecutado y fecha de recepción."""
    soup = BeautifulSoup(html, "lxml")
    for tabla in soup.find_all("table"):
        # Fila de encabezado = la que menciona 'estado de la recepcion'.
        hdr = next((tr for tr in tabla.find_all("tr")
                    if "estado de la recepcion" in _h(tr.get_text())), None)
        if not hdr:
            continue
        idx = {}
        for i, celda in enumerate(hdr.find_all(["td", "th"])):
            h = _h(celda.get_text())
            for sub, clave in _COLS_500.items():
                if sub in h and clave not in idx:
                    idx[clave] = i
        if "descripcion" not in idx:
            continue
        celdas_hdr = hdr.find_all(["td", "th"])
        out = []
        for tr in tabla.find_all("tr"):
            if tr is hdr:
                continue
            celdas = tr.find_all("td")
            if len(celdas) < len(celdas_hdr):
                continue
            if not limpiar(celdas[0].get_text()).isdigit():
                continue

            def val(clave):
                i = idx.get(clave)
                return limpiar(celdas[i].get_text()) if i is not None and i < len(celdas) else ""

            _cat, detalle = parsear_descripcion(str(celdas[idx["descripcion"]]))
            fecha = (_parse_fecha(val("fecha_definitiva"))
                     or _parse_fecha(val("fecha_provisional"))
                     or _parse_fecha(val("fecha_contrato")))
            out.append({
                "detalle": detalle,
                "proveedor": val("proveedor") or None,
                "fecha_firma": _parse_fecha(val("fecha_firma")),
                "estado": val("estado") or None,
                "cantidad_recibida": _num(val("cantidad_recibida")),
                "fecha_entrega": fecha,
                "monto_ejecutado": _num(val("monto_ejecutado")),
            })
        return out
    return []


def _enganchar_form500(items: list, recep: list) -> tuple[int, dict]:
    """Enriquece los ítems (ya fusionados) con los datos de recepción del FORM500,
    emparejando por CONTENCIÓN de las specs normalizadas (el FORM500 usa un nombre
    corto distinto, pero el detalle técnico es el mismo texto que el FORM100/200).
    Devuelve (n_enganchados, resumen_proceso con fecha_firma/fecha_entrega)."""
    pendientes = [r for r in (recep or []) if _norm_desc(r.get("detalle"))]
    enganchados = 0
    for it in items:
        full = _norm_desc(it.get("descripcion"))
        if not full:
            continue
        idx = next((i for i, r in enumerate(pendientes)
                    if _norm_desc(r["detalle"]) in full), None)
        if idx is None:
            continue
        r = pendientes.pop(idx)
        it["estado_recepcion"] = r.get("estado")
        it["cantidad_recibida"] = r.get("cantidad_recibida")
        it["monto_ejecutado"] = r.get("monto_ejecutado")
        it["fecha_entrega"] = r.get("fecha_entrega")
        if not it.get("proveedor"):
            it["proveedor"] = r.get("proveedor")
        enganchados += 1
    firmas = sorted(f for f in (r.get("fecha_firma") for r in recep) if f)
    entregas = sorted(f for f in (r.get("fecha_entrega") for r in recep) if f)
    resumen = {
        "fecha_firma_contrato": firmas[0] if firmas else None,     # mín
        "fecha_entrega": entregas[-1] if entregas else None,        # máx (completó)
    }
    return enganchados, resumen


async def _detectar_paginas(page) -> int:
    """Máximo número de página leyendo SOLO el paginador (ul.pagination), ignorando
    los enlaces 'Siguiente/Anterior'. El SICOES a veces deja números enormes sueltos
    en el DOM; acá nos ceñimos al paginador visible."""
    try:
        return int(await page.evaluate(r"""
            () => {
                let max = 1;
                const ul = document.querySelector('ul.pagination');
                if (!ul) return 1;
                ul.querySelectorAll('a[onclick*="busquedadraw"]').forEach(a => {
                    const t = (a.textContent || '').trim();
                    if (/^\d+$/.test(t)) max = Math.max(max, parseInt(t));
                });
                return max;
            }
        """))
    except Exception:
        return 1


# ─── por proceso ──────────────────────────────────────────────────────────────
async def procesar(page, fila: dict, raiz: str) -> dict:
    cuce = fila["cuce"]
    modalidad = (fila.get("modalidad") or "").strip().upper()

    # 1) Abrir forms de ítems y parsear
    forms_cap = []
    req_items, adj_items = [], []
    for rol, mapa, parser in (
        ("req", FORM_REQUERIDO, None),
        ("adj", FORM_ADJUDICADO, None),
    ):
        form_name = mapa.get(modalidad)
        token = next((f["token"] for f in fila.get("forms", [])
                      if (f["label"] or "").replace(" ", "").upper() == form_name), None)
        if not token:
            continue
        html = await abrir_formulario_html(page, token)
        if not html or len(html) < 100:
            print(f"        ⚠ {form_name} no cargó", flush=True)
            continue
        forms_cap.append(form_name)
        if form_name in ("FORM200", "FORM100"):
            items = parsear_form200_100(html, cuce, form_name)
        else:
            items = parsear_form220_110(html, cuce, form_name)
        if rol == "req":
            req_items = items
        else:
            adj_items = items
        await keepalive(page)
        await page.wait_for_timeout(5000)

    items = _fusionar_items(req_items, adj_items, fila)

    # 1b) FORM500 (recepción): fechas de entrega reales + monto ejecutado por ítem.
    recep_proc = {"fecha_firma_contrato": None, "fecha_entrega": None}
    tok500 = next((f["token"] for f in fila.get("forms", [])
                   if (f["label"] or "").replace(" ", "").upper() == "FORM500"), None)
    if tok500:
        html500 = await abrir_formulario_html(page, tok500)
        if html500 and len(html500) > 100:
            forms_cap.append("FORM500")
            recep = parsear_form500(html500)
            n_eng, recep_proc = _enganchar_form500(items, recep)
            if recep:
                print(f"        · FORM500: {len(recep)} recepciones, {n_eng}/{len(items)} ítems enganchados", flush=True)
            await keepalive(page)
            await page.wait_for_timeout(5000)

    # 2) DBC (.docx) solo modalidades grandes → recorte a disco para la fase IA
    tiene_dbc = False
    if modalidad in ("ANPE", "ANPP", "LP"):
        dbc = next((a for a in fila.get("archivos", [])
                    if "documento base" in (a.get("label") or "").lower()), None)
        if dbc:
            carpeta = os.path.join(raiz, _sanitizar_fs(cuce))
            os.makedirs(carpeta, exist_ok=True)
            ruta = await descargar_token(page, dbc["token"], carpeta, "DBC")
            if ruta:
                texto = _a_markdown(ruta, os.path.join(carpeta, "DBC_completo.md"))
                if texto:
                    with open(os.path.join(carpeta, "DBC_recortado.md"), "w", encoding="utf-8") as fh:
                        fh.write(_recortar_dbc(texto))
                    tiene_dbc = True
            await page.wait_for_timeout(1500)

    # 3) Armar filas para Supabase
    fecha_pub = _parse_fecha(fila.get("fecha_pub"))
    monto_adj = sum((r.get("monto_total") or 0) for r in items) or None
    proc_row = {
        "cuce": cuce,
        "entidad_codigo": f'{cuce.split("-")[1]}-{cuce.split("-")[2]}' if len(cuce.split("-")) > 2 else None,
        "entidad_nombre": fila.get("entidad"),
        "modalidad": modalidad,
        "objeto": fila.get("objeto"),
        "tipo_contratacion": fila.get("tipo"),
        "estado": fila.get("estado"),
        "fecha_publicacion": fecha_pub,
        "fecha_presentacion": _parse_fecha(fila.get("fecha_pres")),
        "cuce_anio": _anio_de_cuce(cuce),
        "monto_adjudicado": monto_adj,
        "fecha_firma_contrato": recep_proc.get("fecha_firma_contrato"),
        "fecha_entrega": recep_proc.get("fecha_entrega"),
        "tiene_dbc": tiene_dbc,
        "forms_capturados": forms_cap,
    }
    item_rows = []
    for r in items:
        item_rows.append({
            "cuce": cuce,
            "nro_item": r.get("nro_item"),
            "unspsc_codigo": r.get("unspsc_codigo"),
            "descripcion": r.get("descripcion"),
            "unidad_medida": r.get("unidad_medida"),
            "cantidad": r.get("cantidad"),
            "precio_referencial": r.get("precio_referencial"),
            "precio_adjudicado": r.get("precio_adjudicado"),
            "monto_total": r.get("monto_total"),
            "proveedor": r.get("proveedor"),
            "estado_recepcion": r.get("estado_recepcion"),
            "cantidad_recibida": r.get("cantidad_recibida"),
            "monto_ejecutado": r.get("monto_ejecutado"),
            "fecha_entrega": r.get("fecha_entrega"),
            "fecha_publicacion": fecha_pub,
            "entidad_codigo": proc_row["entidad_codigo"],
            "modalidad": modalidad,
            "fuente": (r.get("fuente") or "").lower(),
        })

    # 4) Escribir (idempotente: reemplaza ítems del proceso)
    _post("hist_procesos", [proc_row], on_conflict="cuce")
    _delete(f"hist_items?cuce=eq.{urllib.parse.quote(cuce)}")
    _post("hist_items", item_rows, prefer="return=minimal")

    print(f"      ✓ {cuce}: {len(item_rows)} ítems "
          f"(forms={forms_cap}, dbc={'sí' if tiene_dbc else 'no'})", flush=True)
    return {"cuce": cuce, "items": len(item_rows), "tiene_dbc": tiene_dbc}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entidad", required=True)
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--n", type=int, default=0, help="límite total de procesos (0 = sin límite)")
    ap.add_argument("--paginas", type=int, default=0, help="cap de páginas del buscador (0 = todas)")
    ap.add_argument("--estado", default="2C")
    ap.add_argument("--reparse", action="store_true")
    args = ap.parse_args()

    cuce2, cuce3 = args.entidad.split("-")
    raiz = os.path.join(BASE_OUT, f"historico_{args.entidad}_{args.anio}")
    os.makedirs(raiz, exist_ok=True)

    ya = set() if args.reparse else _cuces_ya_hechos(args.entidad, args.anio)
    if ya:
        print(f"Ya hechos (se saltan): {len(ya)}")

    async with async_playwright() as p:
        print(f"Conectando al navegador (CDP) en {CDP_URL}...")
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"❌ No se pudo conectar: {e}\nAbrí Brave con --remote-debugging-port=9222")
            return
        ctx = browser.contexts[0]
        page = next((t for t in ctx.pages if "sicoes" in t.url), None)
        if not page:
            page = await ctx.new_page()
        print("Cargando portal y buscador (automático)...")
        await ir_a_buscador(page)
        print(f"Buscando {args.entidad} año {args.anio} (Bienes, estado {args.estado})...")
        await buscar(page, cuce2, cuce3, args.anio, args.estado)
        await page.evaluate("busquedadraw('1')")
        await page.wait_for_timeout(1200)

        # Recorrer las páginas del buscador juntando filas. El paginador del SICOES
        # a veces reporta un total inflado, así que NO confiamos en él: cortamos
        # cuando 2 páginas seguidas no aportan nada nuevo (o la tabla queda vacía).
        total_hint = await _detectar_paginas(page)
        tope = args.paginas or total_hint or 1
        print(f"Páginas en el paginador: {total_hint}"
              + (f" (cap {args.paginas})" if args.paginas else ""))
        filas, vistos, vacias = [], set(), 0
        pag = 1
        while pag <= tope + 3:                   # +3 de colchón por si el paginador se queda corto
            if pag > 1:
                await ir_pagina(page, pag)
            de_pag = await extraer_filas(page, args.entidad)
            nuevas = [f for f in de_pag if f["cuce"] not in vistos]
            vistos.update(f["cuce"] for f in nuevas)
            filas.extend(nuevas)
            print(f"   · página {pag}: {len(nuevas)} en alcance (acum {len(filas)})")
            vacias = vacias + 1 if not nuevas else 0
            if vacias >= 2:                      # 2 páginas seguidas sin novedad → fin
                break
            if args.n and len(filas) >= args.n:  # ya tenemos suficientes
                break
            pag += 1

        filas = [f for f in filas if f["cuce"] not in ya]
        if args.n:
            filas = filas[:args.n]
        print(f"✓ {len(filas)} procesos a procesar (modalidades {sorted(MODALIDADES)})")

        resultados = []
        for idx, fila in enumerate(filas, 1):
            print(f"\n[{idx}/{len(filas)}] {fila['cuce']} [{fila['modalidad']}] — {fila['objeto'][:50]}")
            try:
                resultados.append(await procesar(page, fila, raiz))
            except Exception as e:
                print(f"    ⚠ error: {e}", flush=True)
            await page.wait_for_timeout(1500)

        tot_items = sum(r["items"] for r in resultados)
        con_dbc = sum(1 for r in resultados if r["tiene_dbc"])
        print(f"\n✅ Listo: {len(resultados)} procesos, {tot_items} ítems, {con_dbc} con DBC.")
        print(f"   DBC recortados en: {raiz}  (para historico_specs.py)")


if __name__ == "__main__":
    asyncio.run(main())
