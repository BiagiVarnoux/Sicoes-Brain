"""
Re-clasifica convocatorias YA guardadas con la lógica de clasificación ACTUAL
(diccionario + exclusión + IA por contexto), sin volver a scrapear el SICOES.

Por defecto re-evalúa SOLO las de HOY (creado_en = hoy). Se puede pasar una fecha:
  ../scraper/venv/bin/python reclasificar.py            # las de hoy
  ../scraper/venv/bin/python reclasificar.py 2026-10-06 # las creadas ese día

Actualiza match_dicc / match_dicc_terminos / match_ia / match_ia_razon / relevante.
NO toca visto / descartado / motivos / dbc.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import date

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import radar  # reutiliza la misma lógica clasificar()

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def _get(path: str) -> list:
    req = urllib.request.Request(f"{URL}/rest/v1/{path}", headers=H)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _patch(cuce: str, payload: dict) -> None:
    req = urllib.request.Request(
        f"{URL}/rest/v1/convocatorias_radar?cuce=eq.{urllib.parse.quote(cuce)}",
        data=json.dumps(payload).encode(), method="PATCH",
        headers={**H, "Prefer": "return=minimal"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def main():
    fecha = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    print(f"Re-clasificando convocatorias creadas el {fecha}...")
    rows = _get(f"convocatorias_radar?select=cuce,objeto"
                f"&creado_en=gte.{fecha}T00:00:00&creado_en=lt.{fecha}T23:59:59.999")
    if not rows:
        print("No hay convocatorias creadas en esa fecha.")
        return
    print(f"  {len(rows)} convocatorias a re-evaluar.")

    candidatas = [{"cuce": r["cuce"], "objeto": r.get("objeto", "")} for r in rows]
    radar.clasificar(candidatas, usar_ia=True)

    nuevas_relev = 0
    por_ia = 0
    for c in candidatas:
        _patch(c["cuce"], {
            "match_dicc": c["_match_dicc"],
            "match_dicc_terminos": c["_dicc_terms"],
            "match_ia": c["_match_ia"],
            "match_ia_razon": c["_ia_razon"],
            "relevante": c["_relevante"],
        })
        if c["_relevante"]:
            nuevas_relev += 1
        if c["_match_ia"] and not c["_match_dicc"]:
            por_ia += 1

    print(f"\n✅ Re-clasificadas {len(candidatas)}. Relevantes: {nuevas_relev} "
          f"(de ellas, {por_ia} nuevas por IA/contexto).")


if __name__ == "__main__":
    main()
