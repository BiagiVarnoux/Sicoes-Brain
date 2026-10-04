"""
Sincroniza (solo lectura) el historial de licitaciones del ERP "Contabilidad"
hacia el proyecto del radar ("Sicoes Brain"), para enriquecer el dashboard y
entrenar la IA con el catálogo REAL de lo que el usuario oferta.

Enlace: ERP `licitaciones.numero_sicoes` == radar `cuce4` (4º grupo del CUCE).

Copia SOLO campos no sensibles (sin costos/piso/margen) a las tablas
`erp_licitaciones` y `erp_productos` de Sicoes Brain.

Config en monitor/.env:
  ERP_SUPABASE_URL=https://glhflhqpsjlyrymquzsn.supabase.co
  ERP_SUPABASE_KEY=<key del ERP con permiso de LECTURA de licitaciones>
      (server-side; NO ponerla en el frontend ni en el proyecto Sicoes Brain)
  SUPABASE_URL / SUPABASE_KEY  → ya existentes (destino Sicoes Brain)

Uso:
  ../scraper/venv/bin/python erp_sync.py
"""
import os
import json
import urllib.request
import urllib.parse

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ERP_URL = os.environ.get("ERP_SUPABASE_URL", "").rstrip("/")
ERP_KEY = os.environ.get("ERP_SUPABASE_KEY", "")
DEST_URL = os.environ["SUPABASE_URL"].rstrip("/")
DEST_KEY = os.environ["SUPABASE_KEY"]


def _get(url: str, key: str) -> list:
    req = urllib.request.Request(url, headers={
        "apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _send(method: str, path: str, rows=None, prefer: str = "") -> None:
    data = json.dumps(rows).encode() if rows is not None else None
    headers = {"apikey": DEST_KEY, "Authorization": f"Bearer {DEST_KEY}",
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(f"{DEST_URL}/rest/v1/{path}", data=data,
                                 method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def main():
    if not ERP_URL or not ERP_KEY:
        print("❌ Falta ERP_SUPABASE_URL / ERP_SUPABASE_KEY en monitor/.env")
        return

    # 1) leer del ERP: licitaciones con numero_sicoes + sus productos (embebidos)
    sel = ("numero_sicoes,nombre,entidad,tipo_proceso,estado,fecha_presentacion,"
           "licitacion_productos(orden,nombre,especificacion,cantidad,precio_entidad,precio_ofertado)")
    url = (f"{ERP_URL}/rest/v1/licitaciones?select={urllib.parse.quote(sel)}"
           f"&numero_sicoes=neq.&order=numero_sicoes")
    licis = _get(url, ERP_KEY)
    print(f"ERP: {len(licis)} licitaciones con numero_sicoes")

    GANADA = {"ADJUDICADA", "ENTREGADA", "COBRADA"}
    lic_rows, prod_rows = [], []
    for l in licis:
        ns = (l.get("numero_sicoes") or "").strip()
        if not ns:
            continue
        lic_rows.append({
            "numero_sicoes": ns,
            "nombre": l.get("nombre"),
            "entidad": l.get("entidad"),
            "tipo_proceso": l.get("tipo_proceso"),
            "estado": l.get("estado"),
            "ganada": (l.get("estado") or "") in GANADA,
            "fecha_presentacion": l.get("fecha_presentacion"),
        })
        for p in (l.get("licitacion_productos") or []):
            prod_rows.append({
                "numero_sicoes": ns,
                "orden": p.get("orden"),
                "nombre": p.get("nombre"),
                "especificacion": p.get("especificacion"),
                "cantidad": p.get("cantidad"),
                "precio_entidad": p.get("precio_entidad"),
                "precio_ofertado": p.get("precio_ofertado"),
            })

    # 2) escribir en Sicoes Brain: upsert licitaciones, reemplazar productos
    if lic_rows:
        _send("POST", "erp_licitaciones?on_conflict=numero_sicoes", lic_rows,
              "resolution=merge-duplicates,return=minimal")
    # productos: borrar los de las licitaciones sincronizadas y reinsertar
    ns_list = ",".join(f'"{r["numero_sicoes"]}"' for r in lic_rows)
    if ns_list:
        _send("DELETE", f"erp_productos?numero_sicoes=in.({ns_list})")
    if prod_rows:
        _send("POST", "erp_productos", prod_rows, "return=minimal")

    print(f"✓ Sincronizado: {len(lic_rows)} licitaciones, {len(prod_rows)} productos → Sicoes Brain")


if __name__ == "__main__":
    main()
