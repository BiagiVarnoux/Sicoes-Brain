"""
Backfill: re-descarga TODOS los archivos de cada convocatoria RELEVANTE con la
lógica corregida (captura también los PDF que se abren inline, y espera el guard
del sitio para no perder archivos cuando hay varios — p.ej. en los CM, donde está
la "Oferta del Proveedor" además de la "Declaración Jurada").

Busca cada CUCE fresco por su 4º grupo (tokens nuevos), baja todos los archivos,
convierte Word→PDF, renombra y sube a Storage, y actualiza dbc_archivos.

Requiere Brave/Chrome abierto con --remote-debugging-port=9222 (igual que radar.py).

Uso:
  ../scraper/venv/bin/python redescargar_dbc.py
"""
import os
import json
import asyncio
import urllib.request

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from playwright.async_api import async_playwright
import sicoes_nav as nav
import dbc_store
import db

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_DBC = os.path.join(AQUI, "dbc")
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def relevantes() -> list[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/convocatorias_radar?select=cuce,modalidad&relevante=eq.true&order=cuce",
        headers=H)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def cuce4(cuce: str) -> str:
    p = cuce.split("-")
    return p[3] if len(p) >= 4 else cuce


async def main():
    import sys
    rows = relevantes()
    # Filtro opcional: pasar uno o más fragmentos de CUCE (p.ej. el 4º grupo) como args
    filtros = [a for a in sys.argv[1:] if not a.startswith("-")]
    if filtros:
        rows = [r for r in rows if any(f in r["cuce"] for f in filtros)]
        print(f"Filtrando a {len(rows)} por: {filtros}")
    print(f"Relevantes a re-descargar: {len(rows)}")
    async with async_playwright() as p:
        try:
            browser, page = await nav.conectar(p)
        except Exception as e:
            print(f"❌ No se pudo conectar a Brave/Chrome (¿abierto con --remote-debugging-port=9222?): {e}")
            return
        await nav.ir_a_buscador(page)

        async def reconectar():
            """Si Brave se cerró/hipó, reconectar y volver al buscador."""
            nonlocal browser, page
            print("    ↻ reconectando a Brave...", flush=True)
            await page.wait_for_timeout(2000)
            browser, page = await nav.conectar(p)
            await nav.ir_a_buscador(page)

        for i, r in enumerate(rows, 1):
            cuce = r["cuce"]
            modalidad = r.get("modalidad", "")
            print(f"\n[{i}/{len(rows)}] {cuce} ({modalidad})", flush=True)
            filas = None
            for intento in range(2):
                try:
                    await nav.buscar_por_cuce4(page, cuce4(cuce))
                    filas = await nav.leer_tabla(page)
                    break
                except Exception as e:
                    print(f"    ✗ búsqueda falló: {e}", flush=True)
                    if intento == 0 and ("closed" in str(e).lower() or "crash" in str(e).lower()):
                        try:
                            await reconectar()
                        except Exception as e2:
                            print(f"    ✗ no se pudo reconectar: {e2}", flush=True)
                            break
                    else:
                        break
            if filas is None:
                continue
            fila = next((f for f in filas if f.get("cuce") == cuce), None)
            if not fila:
                # si no hay match exacto, usar la primera con ese cuce4
                fila = filas[0] if filas else None
            if not fila or not fila.get("archivos"):
                print("    · sin archivos", flush=True)
                continue
            carpeta = os.path.join(DIR_DBC, cuce.replace("/", "_"))
            # limpiar carpeta vieja para no mezclar con descargas previas parciales
            if os.path.isdir(carpeta):
                for f in os.listdir(carpeta):
                    try:
                        os.remove(os.path.join(carpeta, f))
                    except OSError:
                        pass
            objetivo = dbc_store.seleccionar_objetivo(modalidad, fila["archivos"])
            if not objetivo:
                print("    · no se encontró el documento objetivo "
                      f"({'Oferta' if modalidad=='CM' else 'DBC'}); archivos: "
                      + ", ".join(a.get('nombre','') for a in fila['archivos']), flush=True)
                continue
            ruta = await nav.descargar_token(page, objetivo["token"], carpeta, objetivo.get("nombre", ""))
            print(f"    {'✓' if ruta else '✗'} {objetivo.get('nombre','')}", flush=True)
            locales = [{"ruta": ruta, "nombre": objetivo.get("nombre", "")}] if ruta else []
            subidos = dbc_store.procesar(cuce, modalidad, locales) if locales else []
            if subidos:
                db.marcar_dbc(cuce, carpeta, subidos)
            print(f"    → {len(locales)} bajado(s), {len(subidos)} subido(s): "
                  + ", ".join(s["nombre"] for s in subidos), flush=True)

    print("\n✅ Backfill terminado.")


if __name__ == "__main__":
    asyncio.run(main())
