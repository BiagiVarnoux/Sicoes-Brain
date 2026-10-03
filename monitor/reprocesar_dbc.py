"""
Reprocesa los DBC ya descargados localmente para las convocatorias RELEVANTES:
convierte Word→PDF (si LibreOffice está disponible), renombra según la convención
y los sube a Supabase Storage, guardando las URLs en dbc_archivos.

Idempotente: se puede re-correr (p.ej. una vez instalado LibreOffice) y re-sube
con upsert, actualizando los que faltaban convertir.

Uso:
  ../scraper/venv/bin/python reprocesar_dbc.py
"""
import os
import json
import urllib.request
import urllib.parse

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import dbc_store
import db

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_DBC = os.path.join(AQUI, "dbc")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def relevantes() -> list[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/convocatorias_radar?select=cuce,modalidad&relevante=eq.true",
        headers=H)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def main():
    rows = relevantes()
    print(f"Relevantes a reprocesar: {len(rows)}")
    total_sub = 0
    for r in rows:
        cuce = r["cuce"]
        carpeta = os.path.join(DIR_DBC, cuce.replace("/", "_"))
        if not os.path.isdir(carpeta):
            print(f"  · {cuce}: sin carpeta local (no se descargó); skip")
            continue
        # tomar archivos locales (ignorar pdfs ya convertidos duplicados se maneja en upsert)
        files = [f for f in sorted(os.listdir(carpeta))
                 if os.path.isfile(os.path.join(carpeta, f)) and not f.startswith(".")]
        locales = [{"ruta": os.path.join(carpeta, f), "nombre": ""} for f in files]
        subidos = dbc_store.procesar(cuce, r.get("modalidad", ""), locales) if locales else []
        if subidos:
            db.marcar_dbc(cuce, carpeta, subidos)
            total_sub += len(subidos)
        print(f"  · {cuce}: {len(locales)} local(es) → {len(subidos)} subido(s)  "
              + ", ".join(s["nombre"] for s in subidos))
    print(f"\nTotal archivos subidos: {total_sub}")


if __name__ == "__main__":
    main()
