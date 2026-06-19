"""
Restaura la tabla `procesos` desde procesos_import.csv.
Usa las credenciales REST del scraper (.env). Inserta en lotes con upsert.
"""
import csv, json, os, sys, urllib.request, urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

CSV_PATH = os.path.expanduser("~/Downloads/procesos_import.csv")
BATCH = 500

INT_COLS = {"cuce_anio", "cuce_convocatoria", "cuce_version"}
DATE_COLS = {"fecha_publicacion", "fecha_presentacion"}

def post_batch(rows):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/procesos",
        data=json.dumps(rows).encode(),
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

def clean(row):
    out = {}
    for k, v in row.items():
        if v is None or v == "":
            out[k] = None
        elif k in INT_COLS:
            try: out[k] = int(v)
            except: out[k] = None
        else:
            out[k] = v
    return out

def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ No existe {CSV_PATH}")
        sys.exit(1)

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [clean(r) for r in reader]

    print(f"Leídas {len(rows)} filas de {CSV_PATH}")
    total_ok = 0
    for i in range(0, len(rows), BATCH):
        lote = rows[i:i+BATCH]
        status, err = post_batch(lote)
        if err:
            print(f"  ✗ lote {i//BATCH+1}: HTTP {status} — {err}")
        else:
            total_ok += len(lote)
            print(f"  ✓ lote {i//BATCH+1}: {total_ok}/{len(rows)}", flush=True)

    print(f"\n✓ COMPLETADO — {total_ok} procesos restaurados")

if __name__ == "__main__":
    main()
