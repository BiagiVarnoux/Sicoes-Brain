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


async def descargar_token(page, token: str, carpeta: str, nombre_sugerido: str = "") -> str | None:
    """Descarga un archivo por su token. Devuelve la ruta guardada o None.
    También sirve de keep-alive de sesión (el request renueva el token SICOES)."""
    os.makedirs(carpeta, exist_ok=True)
    paginas_antes = set(page.context.pages)
    try:
        async with page.expect_download(timeout=25000) as di:
            await page.evaluate(f"descargarArchivo('{token}')")
        download = await di.value
        fname = download.suggested_filename or nombre_sugerido or "archivo"
        ruta = os.path.join(carpeta, fname)
        await download.save_as(ruta)
        return ruta
    except Exception:
        # No disparó evento de descarga (abrió visor inline / pestaña nueva).
        # El request igual se hizo → sesión renovada; devolvemos None.
        return None
    finally:
        for extra in list(page.context.pages):
            if extra is not page and extra not in paginas_antes:
                try:
                    await extra.close()
                except Exception:
                    pass


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
