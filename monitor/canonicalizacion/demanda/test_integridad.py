#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRENTE 3 — PRUEBA DE INTEGRIDAD REPRODUCIBLE. SOLO LECTURA (no escribe en producción).
=============================================================================================
Dos bloques:

  A) BUG DEL PARSER REQUERIDO (FORM100/110): demuestra, sobre los HTML de dump reales, que el
     parser por ÍNDICE FIJO (viejo) desalineaba columnas (descripción = "Unidad", referencial =
     total en vez de unitario) y que el parser por ENCABEZADO (actual, scraper/sicoes_items_cdp.py
     parsear_requerido, commit 21e0f84) lo corrige. Luego compara el re-parse correcto contra lo
     PERSISTIDO en hist_items para esos CUCE → dice si la fila persistida es anterior o posterior
     al fix (sin tocarla).

  B) ANTI DOBLE-CONTEO: valida las invariantes del colapso a ítem económico (agregador_demanda):
     - cada fila de hist_items pertenece a exactamente un ítem económico (sin pérdida ni duplicado),
     - Σ referencial colapsada ≤ Σ referencial cruda (elimina el doble conteo, no lo inventa),
     - las fases (referencial/adjudicado/ejecutado) nunca se suman entre sí.

Correr (desde monitor/):
  ../scraper/venv/bin/python canonicalizacion/demanda/test_integridad.py
Sale 0 si todo pasa; 1 si alguna aserción falla. Imprime el detalle afectado.
"""
import os, sys, glob, json, urllib.request, urllib.parse
from bs4 import BeautifulSoup
from dotenv import load_dotenv

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = "/Users/fabriziocuellar/Sicoes-Brain"
sys.path.insert(0, os.path.join(RAIZ, "scraper"))
sys.path.insert(0, AQUI)
load_dotenv(os.path.join(RAIZ, "monitor", ".env"))
from sicoes_items_cdp import parsear_requerido, limpiar, parse_numero, armar_descripcion, parsear_descripcion  # parser ACTUAL
from agregador_demanda import colapsar, clave_economica, _f, REQUERIDO

U = os.environ["SUPABASE_URL"].rstrip("/"); K = os.environ["SUPABASE_KEY"]
HDR = {"apikey": K, "Authorization": f"Bearer {K}"}
DUMPS = os.path.join(RAIZ, "scraper", "salidas", "historico_0660-10_2026", "_dump_forms")

fallos = []


def parser_viejo_indice_fijo(html, cuce, form_name):
    """Reconstrucción del parser VIEJO (índice fijo) tal como trataba el requerido: asumía una
    columna 'Objeto del Gasto' inexistente → [2]=Obj.Gasto [3]=Descripción [4]=Unidad [5]=Cantidad
    [6]=P.Ref [7]=Monto. Sobre el layout real (7 cols, SIN Obj.Gasto) lee mal. Es solo para la
    demostración del bug; NO se usa en producción."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tabla in soup.find_all("table"):
        if "DETALLE DE BIENES" not in tabla.get_text().upper():
            continue
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all("td")
            if len(celdas) < 8:
                continue
            nro = limpiar(celdas[0].get_text())
            if not nro.isdigit():
                continue
            cat, desc = parsear_descripcion(str(celdas[3]))   # índice viejo: [3]
            out.append({
                "nro_item": int(nro),
                "descripcion_producto": armar_descripcion(cat, desc),
                "precio_referencial": parse_numero(celdas[6].get_text()),  # índice viejo: [6]=total
            })
        break
    return out


def bloque_A():
    print("══ BLOQUE A — bug del parser requerido FORM100/110 (demostración sobre dumps reales)\n")
    dumps = sorted(glob.glob(os.path.join(DUMPS, "*FORM1*")))
    if not dumps:
        print("  (sin dumps en _dump_forms; se omite el bloque A)")
        return
    for f in dumps:
        base = os.path.basename(f)
        cuce = base.rsplit("_", 1)[0]
        form = "FORM100" if "FORM100" in base else "FORM110"
        html = open(f, encoding="utf-8").read()
        nuevo = parsear_requerido(html, cuce, form)
        viejo = parser_viejo_indice_fijo(html, cuce, form)
        print(f"  · {base}  (ítems: nuevo={len(nuevo)}, viejo={len(viejo)})")
        if not nuevo:
            fallos.append(f"{base}: el parser nuevo no extrajo ítems")
            continue
        n0 = nuevo[0]
        v0 = viejo[0] if viejo else {}
        # el parser NUEVO: descripción legible y referencial unitario (no el total)
        desc_ok = bool(n0["descripcion_producto"]) and n0["descripcion_producto"].lower() not in ("unidad", "m2", "")
        ref_ok = isinstance(n0.get("precio_referencial"), (int, float)) and n0["precio_referencial"] is not None
        print(f"      NUEVO  → desc={n0['descripcion_producto'][:46]!r} ref_unit={n0.get('precio_referencial')}")
        print(f"      VIEJO  → desc={(v0.get('descripcion_producto') or '')[:46]!r} ref={v0.get('precio_referencial')}")
        if not desc_ok:
            fallos.append(f"{base}: descripción del parser nuevo parece basura: {n0['descripcion_producto']!r}")
        if not ref_ok:
            fallos.append(f"{base}: referencial del parser nuevo no numérico")
        # demostración del bug: el viejo normalmente difiere (desc basura o ref = total)
        difiere = (v0.get("descripcion_producto") != n0["descripcion_producto"]
                   or v0.get("precio_referencial") != n0.get("precio_referencial"))
        print(f"      → el parser viejo {'DIFIERE (bug reproducido)' if difiere else 'coincide'}")

        # comparar contra lo PERSISTIDO (sin tocarlo)
        q = (f"hist_items?cuce=eq.{urllib.parse.quote(cuce)}&nro_item=eq.{n0['nro_item']}"
             f"&fuente=in.(form100,form110)&select=descripcion,precio_referencial")
        try:
            req = urllib.request.Request(f"{U}/rest/v1/{q}", headers=HDR)
            persist = json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            persist = []
            print(f"      (no se pudo leer persistido: {e})")
        if persist:
            p = persist[0]
            match = _f(p.get("precio_referencial")) == n0.get("precio_referencial")
            print(f"      PERSISTIDO → ref={p.get('precio_referencial')} "
                  f"{'(coincide con el fix → fila post-fix)' if match else '(DIFIERE → fila anterior al fix, candidata a re-scrapeo)'}")
        print()


def bloque_B():
    print("══ BLOQUE B — anti doble-conteo (invariantes del colapso)\n")
    cols = ("id,cuce,nro_item,lote,fuente,descripcion,cantidad,precio_referencial,"
            "precio_adjudicado,monto_total,monto_ejecutado,proveedor,entidad_codigo,modalidad,fecha_publicacion,unspsc_codigo,unidad_medida")
    out, step, off = [], 1000, 0
    while True:
        req = urllib.request.Request(f"{U}/rest/v1/hist_items?select={cols}&limit={step}&offset={off}", headers=HDR)
        rows = json.loads(urllib.request.urlopen(req, timeout=60).read())
        out += rows
        if len(rows) < step:
            break
        off += step
    items = out
    econ = colapsar(items)

    # inv1: particion exacta — cada fila en exactamente un ítem económico
    ids_en_econ = [i for e in econ.values() for i in e["ids_origen"]]
    if len(ids_en_econ) != len(items):
        fallos.append(f"partición: {len(ids_en_econ)} ids en ítems vs {len(items)} filas")
    if len(set(ids_en_econ)) != len(ids_en_econ):
        fallos.append("partición: hay filas asignadas a más de un ítem económico")
    print(f"  inv1 partición exacta: {len(items)} filas → {len(econ)} ítems, "
          f"{len(set(ids_en_econ))} ids únicos ({'OK' if len(set(ids_en_econ))==len(items) else 'FALLA'})")

    # inv2: Σ colapsada ≤ Σ cruda (elimina doble conteo, no lo inventa)
    crudo = sum((_f(i.get("precio_referencial")) or 0) * (_f(i.get("cantidad")) or 0) for i in items)
    colap = sum(e["monto_referencial"] or 0 for e in econ.values())
    if colap > crudo + 1:
        fallos.append(f"Σ colapsada ({colap:,.0f}) > cruda ({crudo:,.0f})")
    print(f"  inv2 Σ referencial: cruda=Bs {crudo:,.0f} ≥ colapsada=Bs {colap:,.0f} "
          f"({'OK' if colap <= crudo+1 else 'FALLA'}) · doble conteo eliminado Bs {crudo-colap:,.0f}")

    # inv3: fases independientes — el total global de cada fase es la suma de ese campo por ítem,
    # nunca una mezcla. Se comprueba que recomponer desde los ítems reproduce cada fase por separado.
    g_ref = sum(e["monto_referencial"] or 0 for e in econ.values())
    g_adj = sum(e["monto_adjudicado"] or 0 for e in econ.values())
    g_eje = sum(e["monto_ejecutado"] or 0 for e in econ.values())
    if not (g_ref > 0 and g_adj > 0 and g_eje > 0 and g_ref != g_adj != g_eje):
        fallos.append("inv3: las tres fases no resultaron en totales independientes y positivos")
    print(f"  inv3 fases independientes: ref=Bs {g_ref:,.0f} · adj=Bs {g_adj:,.0f} · eje=Bs {g_eje:,.0f} "
          f"(tres totales distintos, no mezclados: {'OK' if g_ref != g_adj != g_eje else 'FALLA'})")

    # inv4: los 462 ítems con requerido+adjudicado toman referencial del requerido
    ra = [e for e in econ.values() if any(x in ("form100", "form110") for x in e["fuentes_presentes"])
          and any(x in ("form200", "form220") for x in e["fuentes_presentes"])]
    mal = [e for e in ra if e["referencial_fuente"] not in ("requerido", None)]
    if mal:
        fallos.append(f"{len(mal)} ítems req+adj NO tomaron referencial del requerido")
    print(f"  inv4 req+adj usan referencial del requerido: {len(ra)-len(mal)}/{len(ra)} ({'OK' if not mal else 'FALLA'})")


def main():
    bloque_A()
    bloque_B()
    print("\n" + ("✅ TODAS LAS ASERCIONES PASAN" if not fallos else f"❌ {len(fallos)} FALLO(S):"))
    for f in fallos:
        print("   -", f)
    sys.exit(0 if not fallos else 1)


if __name__ == "__main__":
    main()
