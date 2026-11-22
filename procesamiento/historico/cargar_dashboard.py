"""Cargador de fichas (etapa 2) → Supabase para el dashboard histórico.

Toma una corrida de `acquisitions.py` (fichas.jsonl + observaciones.jsonl) y arma
las filas planas que lee el front (`hist_procesos` + `hist_items`). Mantiene las
columnas que el dashboard ya consume; moderniza SOLO cómo se llenan desde la ficha
nueva. `especificaciones` (DBC) y `producto_canonico_id` quedan NULL por ahora
(se actualizan en etapa 3 y etapa 6).

Por defecto NO escribe (dry-run): arma todo, valida y muestra una muestra + conteos.
Con --write reemplaza hist_items/hist_procesos (borra lo viejo e inserta lo nuevo).

Uso:
  python -m procesamiento.historico.cargar_dashboard --run procesamiento/historico/data/<salida>
  python -m procesamiento.historico.cargar_dashboard --run <salida> --write   # escribe de verdad
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_env():
    """SUPABASE_URL / SUPABASE_KEY desde el entorno o monitor/.env (misma fuente
    que el scraper). No imprime valores."""
    url = os.environ.get("SUPABASE_URL"); key = os.environ.get("SUPABASE_KEY")
    envf = ROOT / "monitor" / ".env"
    if (not url or not key) and envf.is_file():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line.startswith("SUPABASE_URL=") and not url:
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("SUPABASE_KEY=") and not key:
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    return url, key


def fval(obs, name):
    for f in obs.get("fields", []):
        if f.get("name") == name:
            return (f.get("normalized") or {}).get("value") or f.get("visible") or f.get("raw")
    return None


def num(x):
    if x in (None, ""):
        return None
    s = re.sub(r"[^\d.\-]", "", str(x))
    if s in ("", "-", ".", "-."):
        return None
    try:
        v = float(s)
        return int(v) if v.is_integer() else v
    except ValueError:
        return None


def iso_date(s):
    """dd/mm/yyyy → yyyy-mm-dd; deja None si no calza."""
    if not s:
        return None
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(s))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def build_rows(run_dir):
    run_dir = Path(run_dir)
    obs = {}
    with open(run_dir / "observaciones.jsonl") as fh:
        for line in fh:
            o = json.loads(line)
            obs[o["observation_id"]] = o
    procesos = {}
    items = []
    with open(run_dir / "fichas.jsonl") as fh:
        for line in fh:
            fi = json.loads(line)
            cuce = fi["cuce"]
            pm = fi.get("process_metadata") or {}
            oid = fi.get("observation_ids") or []
            myobs = [obs[i] for i in oid if i in obs]
            rec = next((o for o in myobs if o.get("stage") == "recepcion"), None)
            con = next((o for o in myobs if o.get("stage") == "contratacion"), None)
            spine = rec or con
            if spine is None:
                continue
            descripcion = (spine.get("description_visible") or "").strip() or None
            cant_rec = num(fval(rec, "cantidad_reportada_recepcion")) if rec else None
            monto_ej = num(fval(rec, "monto_real_ejecutado")) if rec else None
            precio_adj = num(fval(con, "precio_unitario_adjudicado")) if con else None
            importe_adj = num(fval(con, "importe_total_adjudicado")) if con else None
            unidad = (fval(con, "unidad_medida") if con else None) or (fval(rec, "unidad_medida") if rec else None)
            proveedor = (fval(rec, "proveedor_documentado") if rec else None) or (fval(con, "proveedor_documentado") if con else None)
            estado = fval(rec, "estado_recepcion") if rec else None
            unspsc = (fval(spine, "codigo_catalogo") or fval(spine, "unspsc") or
                      fval(spine, "codigo_unspsc"))
            fecha_pub = iso_date(pm.get("fecha_pub"))
            items.append({
                "cuce": cuce,
                "nro_item": num(fval(spine, "nro_item_documento")),
                "unspsc_codigo": (str(unspsc) if unspsc else None),
                "descripcion": descripcion,
                "unidad_medida": unidad,
                "cantidad": cant_rec,
                "precio_referencial": None,
                "precio_adjudicado": precio_adj,
                "monto_total": importe_adj if importe_adj is not None else monto_ej,
                "proveedor": proveedor,
                "estado_recepcion": estado,
                "cantidad_recibida": cant_rec,
                "monto_ejecutado": monto_ej,
                "fecha_entrega": None,
                "entidad_codigo": fi.get("entity"),
                "modalidad": pm.get("modalidad"),
                "fecha_publicacion": fecha_pub,
                "especificaciones": None,            # etapa 3 (DBC LLM)
                "producto_canonico_id": None,        # etapa 6 (canonización)
            })
            p = procesos.setdefault(cuce, {
                "cuce": cuce,
                "entidad_codigo": fi.get("entity"),
                "entidad_nombre": fi.get("entity_name") or pm.get("entidad"),
                "modalidad": pm.get("modalidad"),
                "objeto": pm.get("objeto"),
                "cuce_anio": fi.get("year"),
                "fecha_publicacion": fecha_pub,
                "fecha_firma_contrato": None,
                "fecha_entrega": None,
                "monto_adjudicado": 0,
                "tiene_dbc": fi.get("dbc_status") not in (None, "SIN_DBC_LOCAL"),
            })
            if items[-1]["monto_total"]:
                p["monto_adjudicado"] = (p["monto_adjudicado"] or 0) + items[-1]["monto_total"]
    return list(procesos.values()), items


def _req(url, key, path, method="GET", body=None, prefer=None):
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{url}/rest/v1/{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_canonico_actual(url, key):
    """Mapa (cuce,nro_item) → (producto_canonico_id, especificaciones) de hist_items.
    El reload reemplaza todo; esto permite re-pegar la canonicalización (etapa 6) y
    las specs (etapa 3) para no perderlas. Claves con varias filas se omiten (no se
    adivina cuál canónico va). Lee paginado."""
    from collections import defaultdict
    pids = defaultdict(set); especs = defaultdict(set); offset = 0
    while True:
        raw = _req(url, key, "hist_items?select=cuce,nro_item,producto_canonico_id,"
                   f"especificaciones&limit=1000&offset={offset}")
        rows = json.loads(raw)
        for r in rows:
            k = (r["cuce"], r["nro_item"])
            if r.get("producto_canonico_id") is not None:
                pids[k].add(r["producto_canonico_id"])
            if r.get("especificaciones"):
                especs[k].add(r["especificaciones"])
        if len(rows) < 1000:
            break
        offset += len(rows)
    out = {}
    # Se preserva solo cuando el valor es inequívoco (una sola opción para la clave).
    for k in set(pids) | set(especs):
        pid = next(iter(pids[k])) if len(pids[k]) == 1 else None
        espec = next(iter(especs[k])) if len(especs[k]) == 1 else None
        if pid is not None or espec is not None:
            out[k] = (pid, espec)
    return out


def write_supabase(url, key, procesos, items, batch=500, preservar_canonico=True):
    # Preserva producto_canonico_id/especificaciones (etapas 3 y 6) a través del
    # reemplazo total: se re-pegan por (cuce,nro_item) antes de reinsertar.
    if preservar_canonico:
        prev = fetch_canonico_actual(url, key)
        reasig = 0
        for it in items:
            k = (it["cuce"], it["nro_item"])
            if k in prev:
                pid, espec = prev[k]
                if pid is not None and not it.get("producto_canonico_id"):
                    it["producto_canonico_id"] = pid; reasig += 1
                if espec and not it.get("especificaciones"):
                    it["especificaciones"] = espec
        print(f"  preservando canónicos: {reasig} ítems re-pegados por (cuce,nro_item)", flush=True)
    # Orden por FK: items dependen de procesos. Reemplazo total del histórico.
    print("  borrando hist_items…", flush=True)
    _req(url, key, "hist_items?id=gt.0", method="DELETE", prefer="return=minimal")
    print("  borrando hist_procesos…", flush=True)
    _req(url, key, "hist_procesos?cuce=neq.__none__", method="DELETE", prefer="return=minimal")
    print(f"  insertando {len(procesos)} hist_procesos…", flush=True)
    for i in range(0, len(procesos), batch):
        _req(url, key, "hist_procesos", method="POST", body=procesos[i:i+batch], prefer="return=minimal")
    print(f"  insertando {len(items)} hist_items…", flush=True)
    for i in range(0, len(items), batch):
        _req(url, key, "hist_items", method="POST", body=items[i:i+batch], prefer="return=minimal")
    print("  OK", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="carpeta de salida de acquisitions.py")
    ap.add_argument("--write", action="store_true", help="escribe a Supabase (si no, dry-run)")
    args = ap.parse_args()

    procesos, items = build_rows(args.run)
    # Resumen de cobertura de campos clave
    def pct(field):
        n = sum(1 for it in items if it.get(field) not in (None, ""))
        return f"{n} ({100*n//max(1,len(items))}%)"
    print(f"hist_procesos: {len(procesos)}  |  hist_items: {len(items)}")
    print("cobertura de campos en hist_items:")
    for f in ("descripcion", "proveedor", "cantidad", "monto_ejecutado", "monto_total",
              "estado_recepcion", "unidad_medida", "fecha_publicacion", "unspsc_codigo"):
        print(f"   {f}: {pct(f)}")
    print("\nmuestra de 3 hist_items:")
    for it in items[:3]:
        print("  ", json.dumps({k: it[k] for k in ("cuce", "nro_item", "descripcion", "cantidad",
              "monto_ejecutado", "proveedor", "estado_recepcion", "modalidad")}, ensure_ascii=False)[:160])

    if not args.write:
        print("\n[dry-run] no se escribió nada. Agregá --write para cargar a Supabase.")
        return
    url, key = load_env()
    if not url or not key:
        print("ERROR: faltan SUPABASE_URL / SUPABASE_KEY (monitor/.env o entorno)", file=sys.stderr)
        sys.exit(1)
    write_supabase(url, key, procesos, items)


if __name__ == "__main__":
    main()
