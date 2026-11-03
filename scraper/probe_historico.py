r"""
PROBE histórico — Fase 1 (NO toca Supabase).
=============================================
Para UNA entidad y UN año, toma los primeros N procesos (Bienes adjudicados) y,
por cada proceso, baja TODO lo que ofrece la fila:
  · archivos descargables  → descargarArchivo('token')   (el DBC .docx, anexos)
  · formularios            → verFormulario('token')       (FORM200/220/110/500…)
Luego convierte cada documento a Markdown con markitdown y arma un combinado.md.

El objetivo es COMPARAR: qué trae cada formulario, cuáles tienen precio
referencial vs. adjudicado, y si el DBC viene como .docx de verdad. No decide
nada todavía: solo deja la evidencia en disco.

ANTES DE CORRER:
  1. Cerrar Brave.
  2. Abrir Brave con debugging:
       /Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser \
         --remote-debugging-port=9222 --user-data-dir="/tmp/brave-sicoes"
  3. Ir a https://www.sicoes.gob.bo/portal/index.php y cerrar el popup de comunicados.
  4. Correr:
       ./venv/bin/python probe_historico.py --entidad 0660-10 --anio 2024 --n 10

Nota: ahora SOLO se baja el DBC (.docx); los demás archivos (PDFs de oferta,
contrato, acta) se ignoran porque abren un visor en pestaña nueva y no se usan.

Salida: scraper/salidas/probe_<entidad>_<anio>/<CUCE>/{crudos, md, combinado.md}
"""
import argparse
import asyncio
import json
import os
import re
import sys

from playwright.async_api import async_playwright

try:
    from markitdown import MarkItDown
    _MD = MarkItDown()
except Exception as e:  # pragma: no cover
    print(f"⚠ markitdown no disponible ({e}). Se guardarán los crudos igual.")
    _MD = None

CDP_URL = "http://localhost:9222"
PORTAL = "https://www.sicoes.gob.bo/portal/index.php"
BUSCADOR = "/portal/contrataciones/busqueda/convocatorias.php?tipo=convNacional"
BASE_OUT = os.path.join(os.path.dirname(__file__), "salidas")

# Modalidades en alcance (se excluye CND1 y el resto).
MODALIDADES = {"CM", "ANPE", "ANPP", "LP"}


# ─── markitdown ───────────────────────────────────────────────────────────────
def _a_markdown(path_in: str, path_out: str) -> str | None:
    """Convierte un archivo a Markdown. Devuelve el texto o None."""
    if _MD is None:
        return None
    try:
        res = _MD.convert(path_in)
        texto = getattr(res, "text_content", None) or getattr(res, "markdown", "")
        os.makedirs(os.path.dirname(path_out), exist_ok=True)  # blindaje ENOENT
        with open(path_out, "w", encoding="utf-8") as fh:
            fh.write(texto)
        return texto
    except Exception as e:
        print(f"        ⚠ markitdown falló en {os.path.basename(path_in)}: {e}", flush=True)
        return None


def _recortar_dbc(md_texto: str) -> str:
    """El DBC trae ~15 págs de relleno legal + un índice. Nos quedamos solo con lo
    útil: desde el ENCABEZADO real de 'Especificaciones Técnicas' (o la tabla de
    'Precio Referencial'), ignorando las entradas del índice (líneas tipo
    '[... 19](#_Toc...)'), y sin las imágenes base64."""
    import re as _re
    lineas = md_texto.splitlines()

    def es_toc(ln: str) -> bool:
        # entradas del índice: '[Texto 19](#_Toc...)' o terminan en link ancla
        return bool(_re.match(r"^\s*\[.*\]\(#", ln))

    inicio = None
    for i, ln in enumerate(lineas):
        if es_toc(ln):
            continue
        u = ln.upper()
        # ancla 1: encabezado markdown real de especificaciones (no el texto legal)
        es_heading_specs = bool(_re.match(r"^#{1,6}\s", ln)) and \
            ("ESPECIFICACIONES TÉCNICAS" in u or "ESPECIFICACIONES TECNICAS" in u)
        # ancla 2: cabecera de la tabla de precio referencial (precio unitario + referencial)
        es_tabla_precio = ("PRECIO UNITARIO" in u and "REFERENCIAL" in u)
        if es_heading_specs or es_tabla_precio:
            inicio = i
            break
    recorte = "\n".join(lineas[inicio:]) if inicio is not None else md_texto
    recorte = _re.sub(r"!\[[^\]]*\]\(data:[^)]*\)", "", recorte)  # fuera imágenes base64
    return recorte.strip()


def _sanitizar_fs(txt: str) -> str:
    import unicodedata
    if not txt:
        return ""
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^A-Za-z0-9 \-_]", "", t).strip()
    return (t[:60] or "archivo")


def _ext_desde_headers(h: dict) -> str:
    ct = (h.get("content-type") or "").lower()
    return {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/zip": ".zip",
        "application/x-rar-compressed": ".rar",
    }.get(ct.split(";")[0].strip(), ".bin")


# ─── navegación (portada del radar: todo automático, sin tocar el navegador) ──
async def _asegurar_portal(page) -> bool:
    """Deja la página en el portal con irLink() cargado. Reintenta (equipos lentos)."""
    async def tiene_irlink() -> bool:
        try:
            return bool(await page.evaluate("() => typeof irLink === 'function'"))
        except Exception:
            return False
    for _ in range(3):
        if await tiene_irlink():
            return True
        try:
            await page.goto(PORTAL, wait_until="domcontentloaded", timeout=90000)
        except Exception:
            pass
        try:
            await page.wait_for_function("() => typeof irLink === 'function'", timeout=60000)
            await page.wait_for_timeout(500)
            return True
        except Exception:
            await page.wait_for_timeout(2000)
    return False


async def ir_a_buscador(page):
    """Carga el portal, CIERRA el popup de comunicados solo, y entra a Búsqueda
    Avanzada vía irLink — sin que el usuario toque el navegador."""
    if not await _asegurar_portal(page):
        raise RuntimeError("No se pudo cargar el portal del SICOES (irLink no disponible).")
    await page.evaluate("""
        () => {
            document.querySelectorAll("button.close[data-dismiss='modal']").forEach(b => b.click());
            document.querySelectorAll(".modal").forEach(m => {
                m.style.display='none'; m.classList.remove('show','in'); });
            document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
            if (window.$) window.$.fn.modal = function() { return this; };
        }
    """)
    await page.wait_for_timeout(500)
    await page.evaluate(f"irLink('{BUSCADOR}')")
    try:
        await page.wait_for_function(
            "() => !!document.querySelector('a[href=\"#f-avanzada\"]') "
            "|| !!document.querySelector('#formAvanzada')", timeout=30000)
    except Exception:
        await page.wait_for_timeout(3000)
    await page.wait_for_timeout(600)
    try:
        await page.evaluate("var t=document.querySelector('a[href=\"#f-avanzada\"]'); if(t) t.click();")
    except Exception:
        pass
    await page.wait_for_timeout(800)


async def buscar(page, cuce2, cuce3, anio, estado_val="2C"):
    await page.evaluate("""
        () => {
            var tab = document.querySelector('a[href="#f-avanzada"]'); if (tab) tab.click();
            document.querySelectorAll('#f-avanzada input[type="text"], #f-avanzada input[type="number"]')
                .forEach(el => el.value = '');
            ['codigoModalidad','r1','codigoContrato','codigoDpto','codigoNormativa']
                .forEach(n => { var el = document.getElementById(n); if (el) el.value = ''; });
        }
    """)
    await page.wait_for_timeout(300)
    await page.evaluate("""
        (args) => {
            var tab = document.querySelector('#f-avanzada') || document;
            var f = sel => tab.querySelectorAll(sel);
            var c1 = f('[name="cuce1"]'); if (c1[0]) c1[0].value = args.anio;
            var c2 = f('[name="cuce2"]'); if (c2[0]) c2[0].value = args.cuce2;
            var c3 = f('[name="cuce3"]'); if (c3[0]) c3[0].value = args.cuce3;
            var ct = document.getElementById('codigoContrato'); if (ct) ct.value = 'B';
            var est = document.getElementById('r1'); if (est) est.value = args.estado_val;
        }
    """, {"anio": str(anio)[2:], "cuce2": cuce2, "cuce3": cuce3, "estado_val": estado_val})
    await page.wait_for_timeout(400)
    await page.evaluate("""
        () => {
            for (var b of document.querySelectorAll('.btn-primary, button[type="submit"]')) {
                if (b.offsetParent !== null && b.textContent.includes('Buscar')) { b.click(); return; }
            }
        }
    """)
    try:
        await page.wait_for_selector("table tbody tr td", timeout=12000)
        await page.wait_for_timeout(800)
    except Exception:
        await page.wait_for_timeout(4000)


async def extraer_filas(page, ent_codigo: str) -> list[dict]:
    """Por cada fila: cuce, meta y TODOS los tokens (archivos + formularios)."""
    filas = await page.evaluate(r"""
        () => {
            const out = [];
            const trs = document.querySelectorAll('table tbody tr');
            for (const tr of trs) {
                const tds = tr.querySelectorAll('td');
                if (tds.length < 9) continue;
                const txt = i => (tds[i] ? tds[i].innerText.trim() : '');
                const cuce = txt(0);
                if (!cuce || cuce.length < 5) continue;
                const archivos = [], forms = [];
                for (const a of tr.querySelectorAll('a[onclick]')) {
                    const oc = a.getAttribute('onclick') || '';
                    const label = (a.innerText || a.textContent || '').trim();
                    let m = oc.match(/descargarArchivo\('([^']+)'\)/);
                    if (m) { archivos.push({label, token: m[1]}); continue; }
                    m = oc.match(/verFormulario\('([^']+)'\)/);
                    if (m) { forms.push({label, token: m[1]}); }
                }
                out.push({
                    cuce, entidad: txt(1), tipo: txt(2), modalidad: txt(3),
                    objeto: txt(4), fecha_pub: txt(6), fecha_pres: txt(7),
                    estado: txt(8), archivos, forms,
                });
            }
            return out;
        }
    """)
    res = []
    for f in filas:
        partes = f["cuce"].split("-")
        if len(partes) >= 3 and f"{partes[1]}-{partes[2]}" != ent_codigo:
            continue
        if not any(s in f["estado"].lower() for s in ["contratado", "adjudicado"]):
            continue
        # SOLO las modalidades que interesan (se excluye CND1 y otras).
        mod = (f.get("modalidad") or "").strip().upper()
        if mod not in MODALIDADES:
            print(f"      (saltando {f['cuce']} — modalidad {mod!r} fuera de alcance)")
            continue
        res.append(f)
    return res


# ─── descargas ────────────────────────────────────────────────────────────────
async def descargar_token(page, token: str, carpeta: str, nombre_sugerido: str) -> str | None:
    os.makedirs(carpeta, exist_ok=True)
    ctx = page.context
    capturado, descarga = {}, {}

    async def on_response(resp):
        try:
            if "descargararchivo.php" in resp.url.lower() and "resp" not in capturado:
                capturado["resp"] = resp
        except Exception:
            pass

    def on_download(d):
        descarga["d"] = d

    ctx.on("response", on_response)
    page.on("download", on_download)
    ruta = None
    try:
        await page.evaluate(f"descargarArchivo('{token}')")
        for _ in range(60):
            if descarga.get("d") or capturado.get("resp"):
                break
            await page.wait_for_timeout(500)
        if descarga.get("d"):
            d = descarga["d"]
            fname = d.suggested_filename or (_sanitizar_fs(nombre_sugerido) + ".bin")
            ruta = os.path.join(carpeta, fname)
            await d.save_as(ruta)
        elif capturado.get("resp"):
            resp = capturado["resp"]
            body = await resp.body()
            if body:
                ext = _ext_desde_headers({k.lower(): v for k, v in (resp.headers or {}).items()})
                ruta = os.path.join(carpeta, _sanitizar_fs(nombre_sugerido) + ext)
                with open(ruta, "wb") as fh:
                    fh.write(body)
        await page.wait_for_timeout(800)
    except Exception as e:
        print(f"        ⚠ descarga falló: {e}", flush=True)
    finally:
        try: ctx.remove_listener("response", on_response)
        except Exception: pass
        try: page.remove_listener("download", on_download)
        except Exception: pass
        for extra in list(ctx.pages):
            if extra is not page:
                try: await extra.close()
                except Exception: pass
    return ruta


async def _cerrar_modales(page):
    await page.evaluate("""
        () => {
            document.querySelectorAll('.modal').forEach(m => {
                m.style.display='none'; m.classList.remove('show','in'); });
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
        }
    """)


async def _cerrar_modal_real(page):
    """Cierra el modal con el BOTÓN real del sitio (no solo CSS). Esto resetea el
    guard interno; si solo se oculta por CSS, el próximo verFormulario se bloquea."""
    await page.evaluate("""
        () => {
            var btn = document.querySelector('#modalFormulario .close, .modal.in .close, .modal.show .close');
            if (btn) btn.click();
        }
    """)
    await page.wait_for_timeout(800)
    await _cerrar_modales(page)  # respaldo CSS por si quedó algo


async def keepalive(page) -> bool:
    """Descarga el primer archivo de la página de resultados para RENOVAR la sesión
    (abrir el modal no basta: el servidor renueva el token al bajar un archivo)."""
    token = await page.evaluate(r"""
        () => {
            const a = document.querySelector('a[onclick*="descargarArchivo"]');
            if (!a) return null;
            const m = (a.getAttribute('onclick')||'').match(/descargarArchivo\('([^']+)'\)/);
            return m ? m[1] : null;
        }
    """)
    if not token:
        return False
    await descargar_token(page, token, "/tmp/sicoes_keepalive", "keepalive")
    return True


async def _abrir_form_intento(page, token: str, timeout_ms: int) -> str:
    await _cerrar_modales(page)
    await page.wait_for_timeout(500)
    await page.evaluate(f"verFormulario('{token}')")
    try:
        await page.wait_for_selector("#visualizarformulario0 table", timeout=timeout_ms)
        await page.wait_for_timeout(1500)  # dejar renderizar la tabla completa
    except Exception:
        return ""
    return await page.evaluate(
        "() => { var el = document.getElementById('visualizarformulario0'); return el ? el.innerHTML : ''; }") or ""


async def abrir_formulario_html(page, token: str) -> str:
    """Abre un form y devuelve su HTML. Dos intentos; si el 1º falla, renueva la
    sesión con un keepalive antes de reintentar. Cierra con el botón real."""
    html = await _abrir_form_intento(page, token, 25000)
    if not html or len(html) < 100:
        await _cerrar_modal_real(page)
        await keepalive(page)                 # renovar sesión antes de reintentar
        await page.wait_for_timeout(2500)
        html = await _abrir_form_intento(page, token, 30000)
    await _cerrar_modal_real(page)
    return html or ""


# ─── por proceso ────────────────────────────────────────────────────────────
async def procesar_proceso(page, fila: dict, raiz: str) -> dict:
    cuce = fila["cuce"]
    carpeta = os.path.join(raiz, _sanitizar_fs(cuce))
    crudos = os.path.join(carpeta, "crudos")
    md_dir = os.path.join(carpeta, "md")
    os.makedirs(crudos, exist_ok=True)
    os.makedirs(md_dir, exist_ok=True)

    with open(os.path.join(carpeta, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(fila, fh, ensure_ascii=False, indent=2)

    reporte = {"cuce": cuce, "modalidad": fila["modalidad"], "objeto": fila["objeto"],
               "archivos": [], "forms": []}
    combinado = [f"# {cuce}", f"**Objeto:** {fila['objeto']}",
                 f"**Modalidad:** {fila['modalidad']}  ·  **Estado:** {fila['estado']}",
                 f"**Publicación:** {fila['fecha_pub']}  ·  **Presentación:** {fila['fecha_pres']}", ""]

    # 1) SOLO el DBC (.docx). Los demás archivos son PDFs (oferta, DJ, contrato,
    #    acta) que no usamos y que abren un visor en pestaña nueva → problemas.
    dbc = next((a for a in fila.get("archivos", [])
                if "documento base" in (a.get("label") or "").lower()), None)
    if dbc:
        print(f"      ⬇ DBC: {dbc['label'][:40]}", flush=True)
        ruta = await descargar_token(page, dbc["token"], crudos, "DBC")
        if ruta:
            ext = os.path.splitext(ruta)[1].lower()
            md_full = os.path.join(md_dir, "DBC_completo.md")
            texto = _a_markdown(ruta, md_full)
            recorte = ""
            if texto:
                recorte = _recortar_dbc(texto)
                with open(os.path.join(md_dir, "DBC_recortado.md"), "w", encoding="utf-8") as fh:
                    fh.write(recorte)
                combinado += [f"## DBC (recortado a specs + precio referencial)", recorte, ""]
            reporte["archivos"].append({
                "label": dbc["label"], "ok": True, "ext": ext,
                "bytes": os.path.getsize(ruta),
                "md_full_chars": len(texto) if texto else 0,
                "md_recorte_chars": len(recorte)})
        else:
            reporte["archivos"].append({"label": dbc["label"], "ok": False})
        await page.wait_for_timeout(1200)
    else:
        reporte["sin_dbc"] = True  # normal en CM

    # 2) formularios (HTML). Keep-alive + pausa larga entre cada uno para no
    #    matar la sesión (abrir el modal no renueva el token; bajar un archivo sí).
    import random
    for fi, fm in enumerate(fila.get("forms", [])):
        label = (fm["label"] or "FORM").replace(" ", "").upper()
        print(f"      📄 form: {label}", flush=True)
        if fi > 0:
            await keepalive(page)
            await page.wait_for_timeout(int(random.uniform(4000, 7000)))
        html = await abrir_formulario_html(page, fm["token"])
        if not html or len(html) < 100:
            reporte["forms"].append({"label": label, "ok": False})
            continue
        html_path = os.path.join(crudos, f"{_sanitizar_fs(label)}.html")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(f"<html><meta charset='utf-8'><body>{html}</body></html>")
        md_path = os.path.join(md_dir, f"{_sanitizar_fs(label)}.md")
        texto = _a_markdown(html_path, md_path)
        low = (texto or "").lower()
        reporte["forms"].append({
            "label": label, "ok": True, "md_chars": len(texto) if texto else 0,
            "tiene_precio": "precio" in low or "bs" in low,
            "tiene_referencial": "referencial" in low or "estimad" in low,
            "tiene_adjudicado": "adjudic" in low})
        if texto:
            combinado += [f"## FORMULARIO: {label}", texto, ""]
        await page.wait_for_timeout(1500)

    with open(os.path.join(carpeta, "combinado.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(combinado))
    return reporte


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entidad", required=True, help="código, ej. 0660-10")
    ap.add_argument("--anio", type=int, default=2024)
    ap.add_argument("--n", type=int, default=10, help="procesos a probar")
    ap.add_argument("--estado", default="2C")
    args = ap.parse_args()

    cuce2, cuce3 = args.entidad.split("-")
    raiz = os.path.join(BASE_OUT, f"probe_{args.entidad}_{args.anio}")
    os.makedirs(raiz, exist_ok=True)

    async with async_playwright() as p:
        print(f"Conectando al navegador (CDP) en {CDP_URL}...")
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"❌ No se pudo conectar: {e}")
            print("Abrí Brave con --remote-debugging-port=9222 y entrá a sicoes.gob.bo")
            return
        ctx = browser.contexts[0]
        page = next((t for t in ctx.pages if "sicoes" in t.url), None)
        if not page:
            page = await ctx.new_page()
        print("Cargando portal y buscador (automático)...")
        await ir_a_buscador(page)
        print(f"✓ Buscador listo: {page.url[:60]}")
        print(f"Buscando {args.entidad} año {args.anio} (Bienes, estado {args.estado})...")
        await buscar(page, cuce2, cuce3, args.anio, args.estado)
        await page.evaluate("busquedadraw('1')")
        await page.wait_for_timeout(1200)

        filas = await extraer_filas(page, args.entidad)
        print(f"✓ {len(filas)} procesos en la 1ª página; tomo {min(args.n, len(filas))}")
        filas = filas[:args.n]

        reportes = []
        for idx, fila in enumerate(filas, 1):
            print(f"\n[{idx}/{len(filas)}] {fila['cuce']} — {fila['objeto'][:50]}")
            print(f"    archivos={len(fila['archivos'])}  forms={[x['label'] for x in fila['forms']]}")
            try:
                reportes.append(await procesar_proceso(page, fila, raiz))
            except Exception as e:
                print(f"    ⚠ error: {e}", flush=True)
            await page.wait_for_timeout(1500)

        with open(os.path.join(raiz, "REPORTE.json"), "w", encoding="utf-8") as fh:
            json.dump(reportes, fh, ensure_ascii=False, indent=2)
        print(f"\n✅ Listo. Evidencia en: {raiz}")
        print("   Revisá REPORTE.json (qué trajo cada doc) y los combinado.md por proceso.")


if __name__ == "__main__":
    asyncio.run(main())
