"""Captura/re-captura por CUCE buscando directamente por NÚMERO DE CONVOCATORIA.

El buscador avanzado del SICOES parte el CUCE en casillas independientes
(cuce1=año, cuce2/cuce3=entidad, cuce4=nº de convocatoria, cuce5/cuce6=variante)
y permite dejar vacías las que uno quiera. Con solo el nº de convocatoria el
proceso sale a la primera, sin paginar todo el listado de la entidad/gestión.

Por eso aquí NO hace falta entidad ni año: se escribe solo el número.

- ``1199042``        -> busca la convocatoria 1199042, variante -1-1 (por defecto)
- ``1199042-1-2``    -> variante explícita (llena cuce5/cuce6)
- ``22-0660-10-1199042-1-2`` -> forma larga válida; se usa solo el tramo
  convocatoria-variante (1199042-1-2), el año/entidad salen del resultado.

La carpeta de guardado se deriva del CUCE que devuelve el portal, así que cae
en la MISMA ruta que el lanzador por entidad/gestión:
``data/historico_http_paginas_<entidad>_<gestion>/<CUCE>/``.
"""
import argparse
import asyncio
import json
import re
import time

from . import historico_http_directo as base

# Forma larga opcional (año-entidad) + convocatoria-variante, o solo la cola.
TAIL = re.compile(r'(?:\d{2}-\d{4}-\d{2}-)?(\d+)-(\d+)-(\d+)$')
NUM_ONLY = re.compile(r'(\d+)$')

RAW_CUCES_JS = (
    "()=>[...document.querySelectorAll('#tablaAvanzada > tbody > tr')]"
    ".map(r=>r.cells[0]?.innerText.trim()||'')"
    ".filter(x=>/^\\d{2}-\\d{4}-\\d{2}-\\d+-\\d+-\\d+$/.test(x))"
)


def parse_entry(token):
    """(num, var1, var2) a partir de un token. Falta de variante => -1-1."""
    token = token.strip()
    m = TAIL.fullmatch(token)
    if m:
        return m.group(1), m.group(2), m.group(3)
    m = NUM_ONLY.fullmatch(token)
    if m:
        return m.group(1), '1', '1'
    raise ValueError(f'CUCE/convocatoria no reconocido: {token!r}')


def parse_all(tokens):
    """Normaliza, descarta duplicados y conserva el orden de aparición."""
    out = []
    for t in tokens:
        entry = parse_entry(t)
        if entry not in out:
            out.append(entry)
    return out


def scope_of(cuce):
    """(entidad, gestión) a partir de un CUCE completo del resultado."""
    p = cuce.split('-')
    return f'{p[1]}-{p[2]}', 2000 + int(p[0])


async def locate(page, nav, num, var1, var2):
    """Busca por nº de convocatoria y devuelve los CUCE de la tabla que calzan."""
    await nav['ir_a_buscador'](page)
    await nav['buscar'](page, '', '', '', '2C', num, var1, var2)
    await page.evaluate("busquedadraw('1')")
    await page.wait_for_timeout(1200)
    base.ensure_browser(page)
    raw = await page.evaluate(RAW_CUCES_JS)
    return [c for c in raw if tuple(c.split('-')[3:6]) == (num, var1, var2)]


async def capture_one(page, nav, converter, num, var1, var2, roots, forms_only=None):
    tag = f'{num}-{var1}-{var2}'
    matches = await locate(page, nav, num, var1, var2)
    if not matches:
        print(f'  {tag}: no está en el buscador (¿anulado, otra modalidad o sin contratación?)', flush=True)
        return 1
    if len(matches) > 1:
        print(f'  {tag}: varios CUCE calzan {matches}; se omite por ambigüedad', flush=True)
        return 1
    cuce = matches[0]
    entity, year = scope_of(cuce)
    root = base.safe_root(base.PACKAGE / 'data' / f'historico_http_paginas_{entity}_{year}')

    async def pick_row():
        rows = await nav['extraer_filas'](page, entity)
        hit = [r for r in rows if r['cuce'] == cuce]
        if not hit:
            return None
        row = hit[0]
        row['_result_page'] = 1
        nav['_active_cuce'] = cuce
        return row

    row = await pick_row()
    if row is None:
        print(f'  {cuce}: aparece en la tabla pero no pasa el filtro (estado/modalidad fuera de alcance)', flush=True)
        return 1
    print(f'  {cuce} -> {entity} {year}', flush=True)
    if forms_only and not [f for f in row.get('forms', []) if base._formnum(f['label']) in forms_only]:
        print(f'    (sin FORM{"/".join(sorted(forms_only))} anunciado todavía — nada que recapturar)', flush=True)
    ok = await base.process(page, row, root, nav, converter, forms_only=forms_only)
    if not ok and base.needs_recovery(root, cuce):
        print('    Recuperación: re-buscando el proceso por convocatoria…', flush=True)
        if cuce in await locate(page, nav, num, var1, var2):
            row = await pick_row()
            if row is not None:
                ok = await base.process(page, row, root, nav, converter, forms_only=forms_only)
    manifest = json.loads((root / cuce / 'manifest.json').read_text())
    status = manifest['status'] if ok else 'PARCIAL'
    rep = roots.setdefault(str(root), {})
    rep[cuce] = status
    base.atomic(root / 'REPORTE.json', (base.dumps(rep) + '\n').encode())
    print(f'    Resultado: {status.replace("_", " ")}', flush=True)
    return 0 if ok else 1


async def capture(entries, converter, startup_seconds=0, forms_map=None, forms_default=None):
    from playwright.async_api import async_playwright
    nav = base.original_functions('primary')
    nav.setdefault('_timings', []).append({'phase': 'brave_startup', 'seconds': startup_seconds, 'status': 'OK'})
    roots = {}
    status = 0
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(base.ENDPOINT, timeout=60000)
        if not browser.contexts:
            raise base.BrowserUnavailable('Brave todavía no tiene contexto')
        context = browser.contexts[0]
        page = next((p for p in context.pages if not p.is_closed() and p.url.startswith(base.PORTAL)), None)
        if page is None:
            page = await context.new_page()
        staging = base.safe_root(base.PACKAGE / 'data' / 'historico_http_paginas_descargas_porcuce')
        await base.configure_downloads(context, page, staging)
        for num, var1, var2 in entries:
            try:
                fo = (forms_map or {}).get(num, forms_default)
                rc = await capture_one(page, nav, converter, num, var1, var2, roots, fo)
            except base.BrowserUnavailable:
                raise
            except Exception as exc:  # un proceso que falla no tumba a los demás
                print(f'  {num}-{var1}-{var2}: error {type(exc).__name__}: {exc}', flush=True)
                rc = 1
            status = status or rc
            await page.wait_for_timeout(1000)
    if roots:
        print('Carpetas afectadas:')
        for r in sorted(roots):
            print(f'  {r}')
    return status


def _formset(texto):
    """Conjunto de nros de form (3 dígitos) desde un csv/espacios. Ej "100,500" -> {'100','500'}."""
    nums = set(re.findall(r'\d{3}', texto or ''))
    if not nums:
        raise ValueError(f'forms inválidos: {texto!r} (se esperan nros de 3 dígitos como 100,200,500)')
    return nums


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cuces', nargs='*',
                   help='Nº de convocatoria (1199042), con variante (1199042-1-2) o CUCE completo')
    p.add_argument('--check', action='store_true',
                   help='Listar lo que se buscaría y verificar dependencias, sin conectar')
    p.add_argument('--forms', default=None,
                   help='Captura SOLO estos forms (csv de nros, ej "100,200,500"); omite DBC/oferta. '
                        'Aplica a todos los CUCE que no estén en --forms-file.')
    p.add_argument('--solo-form500', action='store_true',
                   help='Atajo de --forms 500 (solo la recepción/entrega).')
    p.add_argument('--forms-file', default=None,
                   help='Archivo con "CUCE<espacio o TAB>forms_csv" por línea (# = comentario). '
                        'Define la lista de CUCE y, por cada uno, qué forms recapturar.')
    args = p.parse_args()

    forms_default = _formset(args.forms) if args.forms else ({'500'} if args.solo_form500 else None)
    forms_map, cuces = {}, list(args.cuces)
    if args.forms_file:
        with open(args.forms_file, encoding='utf-8') as fh:
            lineas = fh.readlines()
        for linea in lineas:
            linea = linea.split('#', 1)[0].strip()
            if not linea:
                continue
            tok = linea.replace(',', ' ').split()
            cuce_tok, nums = tok[0], tok[1:]
            cuces.append(cuce_tok)
            if nums:
                try:
                    forms_map[parse_entry(cuce_tok)[0]] = _formset(' '.join(nums))
                except ValueError as exc:
                    p.error(f'{cuce_tok}: {exc}')
    if not cuces:
        p.error('indicá CUCE(s) en la línea o con --forms-file')
    try:
        entries = parse_all(cuces)
    except ValueError as exc:
        p.error(str(exc))

    converter = base.dependencies()
    print('Convocatorias por capturar:')
    for num, var1, var2 in entries:
        fo = forms_map.get(num, forms_default)
        detalle = f'  solo FORM {",".join(sorted(fo))}' if fo else '  (todos los forms + DBC/oferta)'
        print(f'  {num}-{var1}-{var2}{detalle}')
    if args.check:
        print('Dependencias disponibles. Sin conexiones.')
        return

    started = time.monotonic()
    base.prepare_brave()
    elapsed = time.monotonic() - started
    raise SystemExit(asyncio.run(capture(entries, converter, elapsed, forms_map, forms_default)))


if __name__ == '__main__':
    main()
