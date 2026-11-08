#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRENTE 3 — AGREGADOR DE DEMANDA ECONÓMICA (anti doble-conteo). SOLO LECTURA.
=============================================================================================
Colapsa las filas de `hist_items` en ÍTEMS ECONÓMICOS y separa las fases de la demanda sin
sumarlas como si fueran compras distintas. NO escribe en la BD, NO migra, NO toca producción.

CLAVE DE IDENTIDAD DEL ÍTEM ECONÓMICO
-------------------------------------
    clave = (cuce, nro_item, lote)
`lote` hoy es NULL en el 100% de hist_items (verificado 2026-11-07), así que en la práctica la
clave es (cuce, nro_item). Se conserva `lote` en la clave por robustez futura (LP agrupa por lote).

Por qué NO (cuce, descripcion): el SICOES numera los ítems de forma estable DENTRO de un proceso
y el scraper ya fusiona requerido↔adjudicado por descripción al escribir (scraper/historico.py
_fusionar_items). Dos filas con el mismo (cuce, nro_item) son el MISMO ítem visto desde formularios
distintos (una desde el requerido FORM100/110, otra desde el adjudicado FORM200/220).

FASES (no se suman entre sí)
----------------------------
Cada fila trae una `fuente` ∈ {form100, form110, form200, form220}. Mapa:
    REQUERIDO  (demanda solicitada / referencial de la entidad) → form100, form110
    ADJUDICADO (lo efectivamente contratado)                    → form200, form220
    EJECUTADO  (recepción real, FORM500)                        → campo monto_ejecutado (viaja en la
                                                                   fila adjudicada)
Por ítem económico se produce UN valor por fase:
  · referencial: precio_referencial del REQUERIDO si existe; si no, el del adjudicado (fallback).
                 (Verificado: cuando ambos existen difieren en 365/462 casos → el requerido manda.)
  · adjudicado : precio_adjudicado / monto_total del ADJUDICADO.
  · ejecutado  : monto_ejecutado del ADJUDICADO (FORM500).
La cantidad de demanda = cantidad del requerido si existe; si no, la del adjudicado.

ANTI DOBLE-CONTEO
-----------------
Sumar las 7.441 filas crudas infla el referencial ~7.5% (Bs 10,2M) porque los 462 ítems con
requerido+adjudicado cuentan el referencial dos veces. Colapsar a 1 fila por clave lo elimina.

TRAZABILIDAD
------------
Cada ítem económico conserva: cuce, nro_item, entidad, fuentes_presentes (lista), y el id de
hist_items de cada fila de origen (procedencia hasta el ítem original).

CORRESPONDENCIA INCIERTA (se marca, no se oculta)
-------------------------------------------------
  · colision_misma_fuente: >1 fila de la MISMA fuente para una clave (33 claves). El parser emitió
    filas repetidas; se conserva la primera no nula por campo y se marca `incierto=True`.
  · referencial_discrepante: requerido y adjudicado traen referencial distinto (365 casos) → se usa
    el del requerido y se registra `ref_adjudicado` para auditoría.

Correr (desde monitor/):
  ../scraper/venv/bin/python canonicalizacion/demanda/agregador_demanda.py            # reporte + JSON
  ../scraper/venv/bin/python canonicalizacion/demanda/agregador_demanda.py --resumen  # solo consola
"""
import os, sys, json, argparse, urllib.request
from collections import defaultdict
from dotenv import load_dotenv

AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv("/Users/fabriziocuellar/Sicoes-Brain/monitor/.env")
U = os.environ["SUPABASE_URL"].rstrip("/")
K = os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}"}

REQUERIDO = {"form100", "form110"}
ADJUDICADO = {"form200", "form220"}

ITEM_COLS = ("id,cuce,nro_item,lote,fuente,descripcion,unspsc_codigo,unidad_medida,cantidad,"
             "precio_referencial,precio_adjudicado,monto_total,monto_ejecutado,proveedor,"
             "entidad_codigo,modalidad,fecha_publicacion")


def _get_all(table, select):
    out, step, off = [], 1000, 0
    while True:
        req = urllib.request.Request(f"{U}/rest/v1/{table}?select={select}&limit={step}&offset={off}", headers=H)
        rows = json.loads(urllib.request.urlopen(req, timeout=60).read())
        out += rows
        if len(rows) < step:
            break
        off += step
    return out


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def clave_economica(row):
    """(cuce, nro_item, lote). lote NULL → '' para que la clave sea hashable y estable."""
    return (row.get("cuce"), row.get("nro_item"), row.get("lote") or "")


def colapsar(items):
    """Lista de filas hist_items → dict clave→ítem económico colapsado.
    Determinista y re-ejecutable. No muta las filas de entrada."""
    porclave = defaultdict(list)
    for it in items:
        porclave[clave_economica(it)].append(it)

    econ = {}
    for clave, filas in porclave.items():
        req = [f for f in filas if (f.get("fuente") or "") in REQUERIDO]
        adj = [f for f in filas if (f.get("fuente") or "") in ADJUDICADO]
        fuentes = sorted({(f.get("fuente") or "∅") for f in filas})

        # incertidumbre: misma fuente repetida en una clave
        n_por_fuente = defaultdict(int)
        for f in filas:
            n_por_fuente[f.get("fuente")] += 1
        colision = any(n > 1 for n in n_por_fuente.values())

        def primero(cands, campo):
            for f in cands:
                v = _f(f.get(campo))
                if v is not None:
                    return v, f.get("id")
            return None, None

        # REFERENCIAL: requerido manda; fallback adjudicado
        ref_req, ref_req_id = primero(req, "precio_referencial")
        ref_adj, ref_adj_id = primero(adj, "precio_referencial")
        referencial = ref_req if ref_req is not None else ref_adj
        referencial_src = ("requerido" if ref_req is not None else
                           ("adjudicado(fallback)" if ref_adj is not None else None))
        ref_discrepante = (ref_req is not None and ref_adj is not None
                           and abs(ref_req - ref_adj) > 0.01)

        # CANTIDAD de demanda: requerido manda; fallback adjudicado
        cant_req, _ = primero(req, "cantidad")
        cant_adj, _ = primero(adj, "cantidad")
        cantidad = cant_req if cant_req is not None else cant_adj

        # ADJUDICADO
        p_adj, _ = primero(adj, "precio_adjudicado")
        monto_adj, _ = primero(adj, "monto_total")
        # EJECUTADO (FORM500, viaja en la fila adjudicada)
        ejecutado, _ = primero(adj, "monto_ejecutado")

        # metadatos descriptivos (del requerido preferentemente; si no, cualquiera)
        base = (req or adj or filas)[0]
        proveedor = next((f.get("proveedor") for f in adj if f.get("proveedor")), None)

        econ[clave] = {
            "cuce": clave[0],
            "nro_item": clave[1],
            "lote": clave[2] or None,
            "entidad_codigo": base.get("entidad_codigo"),
            "modalidad": base.get("modalidad"),
            "descripcion": base.get("descripcion"),
            "unspsc_codigo": base.get("unspsc_codigo"),
            "unidad_medida": base.get("unidad_medida"),
            "fecha_publicacion": base.get("fecha_publicacion"),
            "fuentes_presentes": fuentes,
            "ids_origen": [f.get("id") for f in filas],
            # fases (NO se suman entre sí)
            "cantidad": cantidad,
            "referencial_unitario": referencial,
            "referencial_fuente": referencial_src,
            "monto_referencial": (referencial * cantidad) if (referencial is not None and cantidad is not None) else None,
            "precio_adjudicado": p_adj,
            "monto_adjudicado": monto_adj if monto_adj is not None else ((p_adj * cantidad) if (p_adj is not None and cantidad is not None) else None),
            "proveedor": proveedor,
            "monto_ejecutado": ejecutado,
            # banderas de incertidumbre (se marcan, no se ocultan)
            "incierto_colision_fuente": colision,
            "incierto_referencial_discrepante": ref_discrepante,
            "ref_adjudicado_auditoria": ref_adj if ref_discrepante else None,
        }
    return econ


def resumen(econ):
    tot_ref = sum(e["monto_referencial"] or 0 for e in econ.values())
    tot_adj = sum(e["monto_adjudicado"] or 0 for e in econ.values())
    tot_eje = sum(e["monto_ejecutado"] or 0 for e in econ.values())
    con_req = sum(1 for e in econ.values() if e["referencial_fuente"] == "requerido")
    con_adj = sum(1 for e in econ.values() if e["precio_adjudicado"] is not None)
    con_eje = sum(1 for e in econ.values() if e["monto_ejecutado"] is not None)
    incierto = sum(1 for e in econ.values() if e["incierto_colision_fuente"] or e["incierto_referencial_discrepante"])
    return {"items_economicos": len(econ), "monto_referencial": tot_ref, "monto_adjudicado": tot_adj,
            "monto_ejecutado": tot_eje, "con_referencial_requerido": con_req,
            "con_adjudicado": con_adj, "con_ejecutado": con_eje, "items_inciertos": incierto}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumen", action="store_true", help="solo imprime resumen, no escribe JSON")
    args = ap.parse_args()

    items = _get_all("hist_items", ITEM_COLS)
    econ = colapsar(items)
    r = resumen(econ)

    # comparación anti doble-conteo (crudo vs colapsado)
    crudo_ref = sum((_f(i.get("precio_referencial")) or 0) * (_f(i.get("cantidad")) or 0) for i in items)

    print(f"filas hist_items: {len(items)}")
    print(f"ítems económicos (colapsados): {r['items_economicos']}")
    print(f"Σ referencial CRUDA (doble conteo): Bs {crudo_ref:,.0f}")
    print(f"Σ referencial COLAPSADA:            Bs {r['monto_referencial']:,.0f}")
    print(f"doble conteo eliminado:             Bs {crudo_ref - r['monto_referencial']:,.0f} "
          f"({100*(crudo_ref - r['monto_referencial'])/max(r['monto_referencial'],1):.1f}%)")
    print(f"Σ adjudicado: Bs {r['monto_adjudicado']:,.0f} | Σ ejecutado: Bs {r['monto_ejecutado']:,.0f}")
    print(f"con referencial(requerido): {r['con_referencial_requerido']} | con adjudicado: {r['con_adjudicado']} "
          f"| con ejecutado: {r['con_ejecutado']} | inciertos: {r['items_inciertos']}")

    if args.resumen:
        return

    # JSON versionado (para auditoría y como fuente de verdad del reporte; el dashboard
    # reimplementa el mismo colapso en TS sobre datos vivos — ver app/src/lib/demanda.ts)
    out_dir = os.path.join(AQUI, "salida")
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "generado_en": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "clave_identidad": "(cuce, nro_item, lote)",
        "filas_origen": len(items),
        "resumen": r,
        "doble_conteo_referencial_bs": round(crudo_ref - r["monto_referencial"], 2),
    }
    with open(os.path.join(out_dir, "demanda_resumen.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    # muestra de ítems inciertos para revisión
    inciertos = [e for e in econ.values() if e["incierto_colision_fuente"] or e["incierto_referencial_discrepante"]]
    with open(os.path.join(out_dir, "demanda_items_inciertos.json"), "w", encoding="utf-8") as fh:
        json.dump(inciertos[:200], fh, ensure_ascii=False, indent=2)
    print(f"\n→ escrito {out_dir}/demanda_resumen.json ({len(inciertos)} ítems inciertos en demanda_items_inciertos.json)")


if __name__ == "__main__":
    main()
