"""
Navegación SICOES para el radar de convocatorias.
Reutiliza la mecánica ya probada del scraper viejo:
- conexión por CDP a un Chrome abierto a mano (--remote-debugging-port=9222)
- entrar al buscador por irLink() (la URL directa rebota al home)
- keep-alive de sesión descargando un archivo (renueva el token del servidor)

A diferencia del scraper viejo, acá buscamos por RANGO DE FECHAS de publicación
(no por CUCE), tipo Bienes, estado Vigente; y leemos la tabla completa de
resultados con sus archivos descargables.
"""
import os
import re

CDP_URL = "http://localhost:9222"
PORTAL = "https://www.sicoes.gob.bo/portal/index.php"
BUSCADOR = "/portal/contrataciones/busqueda/convocatorias.php?tipo=convNacional"


async def conectar(p):
    """Conecta a Chrome vía CDP y devuelve una página en sicoes (o nueva)."""
    browser = await p.chromium.connect_over_cdp(CDP_URL)
    contexts = browser.contexts
    if not contexts:
        raise RuntimeError("Chrome no tiene contexto activo.")
    context = contexts[0]
    page = None
    for tab in context.pages:
        if "sicoes" in tab.url:
            page = tab
            break
    if not page:
        page = await context.new_page()
        await page.goto(PORTAL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
    return browser, page


async def ir_a_buscador(page):
    # cerrar modal de comunicados si aparece
    await page.evaluate("""
        () => {
            document.querySelectorAll("button.close[data-dismiss='modal']").forEach(b => b.click());
            document.querySelectorAll(".modal").forEach(m => {
                m.style.display = 'none'; m.classList.remove('show','in');
            });
            document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
            if (window.$) window.$.fn.modal = function() { return this; };
        }
    """)
    await page.wait_for_timeout(500)
    await page.evaluate(f"irLink('{BUSCADOR}')")
    await page.wait_for_timeout(2500)
    await page.evaluate("document.querySelector('a[href=\"#f-avanzada\"]').click()")
    await page.wait_for_timeout(800)


async def buscar_por_fechas(page, desde: str, hasta: str, estado_val: str = "11"):
    """Busca convocatorias de Bienes publicadas en [desde, hasta] (dd/mm/yyyy).
    estado_val='11' = Vigente. OJO: SICOES a veces ignora el filtro de tipo/estado,
    por eso el radar RE-filtra localmente (tipo, modalidad, estado, fecha límite).

    IMPORTANTE: hay DOS formularios con los mismos campos (formSimple y
    formAvanzada) y DOS tablas (tablaSimple y tablaAvanzada). Hay que setear los
    campos en #formAvanzada, clickear SU botón Buscar, y forzar el redibujado con
    busquedadraw('1') para que #tablaAvanzada se llene con los resultados."""
    await page.evaluate("""
        (a) => {
            var tab = document.querySelector('a[href="#f-avanzada"]'); if (tab) tab.click();
            var form = document.querySelector('#formAvanzada');
            if (!form) return;
            // limpiar solo el form avanzado
            form.querySelectorAll('input[type="text"], input[type="number"]').forEach(el => el.value = '');
            var set = (name, val) => {
                var el = form.querySelector('[name="'+name+'"]');
                if (el) { el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); }
            };
            set('publicacionDesde', a.desde);
            set('publicacionHasta', a.hasta);
            set('codigoContrato', 'B');
            set('r1', a.estado);
        }
    """, {"desde": desde, "hasta": hasta, "estado": estado_val})
    await page.wait_for_timeout(400)
    # click Buscar DENTRO de formAvanzada
    await page.evaluate("""
        () => {
            var form = document.querySelector('#formAvanzada');
            var btn = form && form.querySelector('input.busquedaForm[value="Buscar"], button[type="submit"], input[type="submit"]');
            if (btn) btn.click();
        }
    """)
    await page.wait_for_timeout(2000)
    # forzar render de la primera página de resultados avanzados
    try:
        await page.evaluate("busquedadraw('1')")
    except Exception:
        pass
    try:
        await page.wait_for_selector("#tablaAvanzada tbody tr td", timeout=15000)
        await page.wait_for_timeout(800)
    except Exception:
        await page.wait_for_timeout(4000)


async def buscar_por_cuce4(page, cuce4: str):
    """Busca un proceso puntual por el 4º grupo del CUCE (nº de convocatoria).
    Útil para re-descargar los archivos frescos de un CUCE ya conocido."""
    await page.evaluate("""
        (num) => {
            var tab = document.querySelector('a[href="#f-avanzada"]'); if (tab) tab.click();
            var form = document.querySelector('#formAvanzada'); if (!form) return;
            form.querySelectorAll('input[type="text"], input[type="number"]').forEach(el => el.value = '');
            ['codigoModalidad','r1','codigoContrato','codigoDpto','codigoNormativa']
                .forEach(n => { var el = form.querySelector('[name="'+n+'"]'); if (el) el.value = ''; });
            var c4 = form.querySelector('[name="cuce4"]');
            if (c4) { c4.value = num; c4.dispatchEvent(new Event('change', {bubbles:true})); }
        }
    """, str(cuce4))
    await page.wait_for_timeout(400)
    await page.evaluate("""
        () => {
            var form = document.querySelector('#formAvanzada');
            var btn = form && form.querySelector('input.busquedaForm[value="Buscar"], button[type="submit"], input[type="submit"]');
            if (btn) btn.click();
        }
    """)
    await page.wait_for_timeout(2000)
    try:
        await page.evaluate("busquedadraw('1')")
    except Exception:
        pass
    try:
        await page.wait_for_selector("#tablaAvanzada tbody tr td", timeout=12000)
        await page.wait_for_timeout(600)
    except Exception:
        await page.wait_for_timeout(3000)


async def detectar_total_paginas(page) -> int:
    try:
        return int(await page.evaluate(r"""
            () => {
                let max = 1;
                document.querySelectorAll('[onclick*="busquedadraw"]').forEach(el => {
                    const m = (el.getAttribute('onclick') || '').match(/busquedadraw\('(\d+)'\)/);
                    if (m) max = Math.max(max, parseInt(m[1]));
                });
                return max;
            }
        """))
    except Exception:
        return 1


async def total_registros(page) -> int:
    try:
        return int(await page.evaluate(r"""
            () => {
                const t = document.body.innerText.match(/Se han encontrado\s+([\d.]+)\s+registros/i);
                return t ? parseInt(t[1].replace(/\./g,'')) : 0;
            }
        """))
    except Exception:
        return 0


async def ir_pagina(page, n: int):
    await page.evaluate(f"busquedadraw('{n}')")
    await page.wait_for_timeout(1000)
    try:
        await page.wait_for_selector("#tablaAvanzada tbody tr td", timeout=10000)
        await page.wait_for_timeout(300)
    except Exception:
        await page.wait_for_timeout(2500)


async def leer_tabla(page) -> list[dict]:
    """Lee la página actual de resultados → lista de convocatorias con sus archivos.
    Lee #tablaAvanzada (la tabla de la búsqueda avanzada; existe también
    #tablaSimple oculta — NO usar esa). Columnas: 0 CUCE, 1 Entidad,
    2 Tipo Contratación, 3 Modalidad, 4 Objeto, 5 Subasta, 6 Fecha Publicación,
    7 Fecha Presentación, 8 Estado, 9 Archivos (links descargarArchivo)."""
    filas = await page.evaluate(r"""
        () => {
            const out = [];
            const tbl = document.querySelector('#tablaAvanzada');
            if (!tbl) return out;
            tbl.querySelectorAll('tbody tr').forEach(tr => {
                const tds = tr.querySelectorAll('td');
                if (tds.length < 9) return;
                const txt = i => (tds[i] ? tds[i].innerText.trim() : '');
                // archivos: links con descargarArchivo('TOKEN')
                const archivos = [];
                const celdaArch = tds[9];
                if (celdaArch) {
                    celdaArch.querySelectorAll('a[onclick*="descargarArchivo"]').forEach(a => {
                        const m = (a.getAttribute('onclick')||'').match(/descargarArchivo\('([^']+)'\)/);
                        if (m) archivos.push({ nombre: a.textContent.trim(), token: m[1] });
                    });
                }
                out.push({
                    cuce: txt(0),
                    entidad: txt(1),
                    tipo_contratacion: txt(2),
                    modalidad: txt(3),
                    objeto: txt(4),
                    subasta: txt(5),
                    fecha_publicacion: txt(6),
                    fecha_presentacion: txt(7),
                    estado: txt(8),
                    archivos: archivos,
                });
            });
            return out;
        }
    """)
    return filas or []


def _ext_desde_headers(headers: dict) -> str:
    """Deriva la extensión del archivo desde Content-Disposition / Content-Type."""
    cd = headers.get("content-disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd, re.I)
    if m:
        e = os.path.splitext(m.group(1).strip())[1].lower()
        if e:
            return e
    ct = headers.get("content-type", "").lower()
    return {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/zip": ".zip",
        "application/x-rar-compressed": ".rar",
    }.get(ct.split(";")[0].strip(), ".pdf")


async def _esperar_guard(page):
    """Espera a que el sitio no tenga otra descarga en proceso
    (var global esperandoTokenDescargaArchivo cuando el captcha está activo)."""
    try:
        await page.wait_for_function(
            "() => typeof esperandoTokenDescargaArchivo === 'undefined' "
            "|| esperandoTokenDescargaArchivo === false",
            timeout=20000)
    except Exception:
        pass


async def descargar_token(page, token: str, carpeta: str, nombre_sugerido: str = "") -> str | None:
    """Descarga UN archivo por su token. Devuelve la ruta guardada o None.

    SICOES envía el archivo con un form target=_blank: los Word disparan un evento
    de descarga, pero los PDF se ABREN INLINE en una pestaña nueva (sin evento).
    Por eso capturamos de las dos formas: (1) evento download, o (2) los bytes de
    la respuesta de descargarArchivo.php (sirve para los inline). Además esperamos
    el guard del sitio para no pisar una descarga con la siguiente (hay captcha
    Turnstile invisible que el navegador real resuelve solo)."""
    os.makedirs(carpeta, exist_ok=True)
    await _esperar_guard(page)

    ctx = page.context
    capturado: dict = {}
    descarga: dict = {}
    paginas_antes = set(ctx.pages)

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
        # esperar hasta ~30s a que llegue el evento de descarga o la respuesta
        for _ in range(60):
            if descarga.get("d") or capturado.get("resp"):
                break
            await page.wait_for_timeout(500)

        if descarga.get("d"):
            d = descarga["d"]
            fname = d.suggested_filename or nombre_sugerido or "archivo"
            ruta = os.path.join(carpeta, fname)
            await d.save_as(ruta)
        elif capturado.get("resp"):
            resp = capturado["resp"]
            try:
                body = await resp.body()
            except Exception:
                body = None
            if body:
                ext = _ext_desde_headers({k.lower(): v for k, v in (resp.headers or {}).items()})
                base = _sanitizar_fs(nombre_sugerido) or "archivo"
                ruta = os.path.join(carpeta, base + ext)
                with open(ruta, "wb") as fh:
                    fh.write(body)
        # dar un respiro para que el guard del sitio se libere antes del próximo
        await page.wait_for_timeout(800)
    except Exception as e:
        print(f"        ⚠ descarga falló ({type(e).__name__}): {e}", flush=True)
    finally:
        try:
            ctx.remove_listener("response", on_response)
        except Exception:
            pass
        try:
            page.remove_listener("download", on_download)
        except Exception:
            pass
        for extra in list(ctx.pages):
            if extra is not page and extra not in paginas_antes:
                try:
                    await extra.close()
                except Exception:
                    pass
    return ruta


def _sanitizar_fs(txt: str) -> str:
    import unicodedata
    if not txt:
        return ""
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^A-Za-z0-9 \-_]", "", t).strip()
    return t[:60]


async def keepalive(page) -> bool:
    """Descarga el primer archivo disponible para renovar la sesión."""
    token = await page.evaluate(r"""
        () => {
            const scope = document.querySelector('#tablaAvanzada') || document;
            const a = scope.querySelector('a[onclick*="descargarArchivo"]');
            if (!a) return null;
            const m = (a.getAttribute('onclick')||'').match(/descargarArchivo\('([^']+)'\)/);
            return m ? m[1] : null;
        }
    """)
    if not token:
        return False
    await descargar_token(page, token, "/tmp/sicoes_keepalive")
    return True
