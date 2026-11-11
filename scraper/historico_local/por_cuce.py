"""Variante por CUCE del scraper histórico: capturar uno o más procesos puntuales,
posiblemente de distintas entidades/gestiones, reutilizando el recorrido existente.

Acepta cada CUCE en forma larga (``22-0660-10-1199042-1-2``) o corta, donde la
forma corta usa ``--entidad``/``--anio`` como contexto:

- ``1199042``        -> ``{aa}-{entidad}-1199042-1-1`` (convocatoria sola => -1-1)
- ``1199042-1-2``    -> ``{aa}-{entidad}-1199042-1-2`` (par final explícito)

Las formas largas se autodescriben (la entidad y la gestión salen del propio CUCE),
así que varias entidades/gestiones pueden darse en una sola invocación. No cambia la
captura: agrupa por (entidad, gestión) y llama al ``run`` por páginas ya probado.
"""
import argparse
import asyncio
import re
import time

FULL = re.compile(r'(\d{2})-(\d{4}-\d{2})-(\d+)-(\d+)-(\d+)')
SHORT_NUM = re.compile(r'\d+')
SHORT_FULL = re.compile(r'(\d+)-(\d+)-(\d+)')


def derive_scope(cuce):
    """(entidad, gestión) a partir de un CUCE completo."""
    m = FULL.fullmatch(cuce)
    if not m:
        raise ValueError(f'CUCE inválido: {cuce}')
    aa, entidad, _num, _x, _y = m.groups()
    return entidad, 2000 + int(aa)


def normalize(token, entidad=None, anio=None):
    """Devuelve el CUCE completo. Forma larga tal cual; forma corta exige entidad/anio."""
    token = token.strip()
    if FULL.fullmatch(token):
        return token
    if entidad is None or anio is None:
        raise ValueError(f'Forma corta "{token}" requiere --entidad y --anio')
    if not re.fullmatch(r'\d{4}-\d{2}', entidad) or not 2000 <= anio <= 2100:
        raise ValueError('Entidad o gestión inválida para forma corta')
    aa = f'{anio % 100:02d}'
    if SHORT_FULL.fullmatch(token):
        num, x, y = SHORT_FULL.fullmatch(token).groups()
    elif SHORT_NUM.fullmatch(token):
        num, x, y = token, '1', '1'
    else:
        raise ValueError(f'Token de CUCE no reconocido: {token}')
    return f'{aa}-{entidad}-{num}-{x}-{y}'


def group(tokens, entidad=None, anio=None):
    """Normaliza y agrupa CUCE por (entidad, gestión), sin duplicados y ordenados."""
    grouped = {}
    for t in tokens:
        full = normalize(t, entidad, anio)
        scope = derive_scope(full)
        bucket = grouped.setdefault(scope, [])
        if full not in bucket:
            bucket.append(full)
    return {k: sorted(v) for k, v in grouped.items()}


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cuces', nargs='+',
                   help='Uno o más CUCE: completo (22-0660-10-1199042-1-2) o corto (1199042 / 1199042-1-2)')
    p.add_argument('--entidad', help='Requerido solo para formas cortas, p.ej. 0660-10')
    p.add_argument('--anio', type=int, help='Requerido solo para formas cortas, p.ej. 2022')
    p.add_argument('--check', action='store_true', help='Listar procesos y verificar dependencias, sin conectar')
    args = p.parse_args()
    try:
        grupos = group(args.cuces, args.entidad, args.anio)
    except ValueError as exc:
        p.error(str(exc))

    from . import historico_http_directo as base, historico_http_paginas as pages
    converter = base.dependencies()
    print('Procesos por capturar:')
    for (entidad, anio), cuces in sorted(grupos.items()):
        for c in cuces:
            print(f'  {entidad} {anio}  {c}')
    if args.check:
        print('Dependencias disponibles. Sin conexiones.')
        return

    started = time.monotonic(); base.prepare_brave(); elapsed = time.monotonic() - started
    status = 0
    for (entidad, anio), cuces in sorted(grupos.items()):
        print(f'== {entidad} {anio}: {len(cuces)} CUCE ==', flush=True)
        rc = asyncio.run(pages.run(entidad, anio, converter, cuces, elapsed))
        elapsed = 0  # Brave ya quedó preparado; no volver a contar el arranque.
        status = status or rc
    raise SystemExit(status)


if __name__ == '__main__':
    main()
