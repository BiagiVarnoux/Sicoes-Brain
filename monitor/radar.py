"""
RADAR DE CONVOCATORIAS SICOES
=============================
Revisa el SICOES por RANGO DE FECHAS de publicación y detecta oportunidades
abiertas de los rubros del usuario (computación + etiquetas), descarga sus DBC
y las guarda en Supabase para verlas en el dashboard.

Pre-filtros estructurales (local):
  - Tipo de contratación = Bienes
  - Modalidad en {CM, LP, ANPE, ANPP}
  - Estado = Vigente
  - Fecha de presentación >= hoy  (sigue abierta: aún puedo presentarme)

Clasificación por rubro (DOBLE FILTRO en paralelo, lógica OR):
  - Filtro A: diccionario de términos (rubros.py)
  - Filtro B: IA vía Groq (clasificador_ia.py)
  relevante = A or B

ANTES DE CORRER (igual que el scraper viejo):
  1. Cerrar Chrome completamente.
  2. Abrir Chrome con debugging:
       /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
         --remote-debugging-port=9222 --user-data-dir="/tmp/chrome-sicoes"
  3. Entrar a https://www.sicoes.gob.bo/portal/index.php (cerrar popup).
  4. Correr:
       python3 monitor/radar.py --desde 01/10/2026
       (sin --desde, usa los últimos 7 días)
"""
import os
import csv
import sys
import argparse
import asyncio
from datetime import datetime, date, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from playwright.async_api import async_playwright

import rubros
import clasificador_ia
import db
import sicoes_nav as nav

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR_DBC = os.path.join(AQUI, "dbc")
DIR_SALIDAS = os.path.join(AQUI, "salidas")
ARCHIVO_ULTIMA = os.path.join(AQUI, ".ultima_corrida")

MODALIDADES_OK = {"CM", "LP", "ANPE", "ANPP"}
KEEPALIVE_CADA = 5  # páginas


# ─── Memoria de la última corrida (modo --auto) ─────────────────────────────────
def leer_ultima_corrida() -> date | None:
    """Fecha de la última corrida guardada, o None si nunca corrió en --auto."""
    try:
        with open(ARCHIVO_ULTIMA, encoding="utf-8") as fh:
            return datetime.strptime(fh.read().strip(), "%Y-%m-%d").date()
    except (FileNotFoundError, ValueError):
        return None


def guardar_ultima_corrida(d: date) -> None:
    with open(ARCHIVO_ULTIMA, "w", encoding="utf-8") as fh:
        fh.write(d.isoformat())


# ─── Utilidades de fecha ───────────────────────────────────────────────────────
def parse_fecha_sicoes(texto: str) -> date | None:
    """'26/10/2026' o '26/10/2026 15:30' → date."""
    if not texto:
        return None
    t = texto.strip().split()[0]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    return None


def iso(texto: str) -> str | None:
    d = parse_fecha_sicoes(texto)
    return d.isoformat() if d else None


def modalidad_ok(cel: str) -> bool:
    c = (cel or "").strip().upper()
    return any(c == m or c.startswith(m) for m in MODALIDADES_OK)


# ─── Pipeline ──────────────────────────────────────────────────────────────────
async def recolectar(page, max_paginas: int) -> list[dict]:
    """Recorre todas las páginas de resultados y junta las filas crudas."""
    total_reg = await nav.total_registros(page)
    total_pag = await nav.detectar_total_paginas(page)
    pags = min(total_pag, max_paginas) if max_paginas else total_pag
    print(f"  → {total_reg} registros, {total_pag} páginas (recorro {pags})", flush=True)

    todas = []
    for n in range(1, pags + 1):
        if n > 1:
            await nav.ir_pagina(page, n)
        filas = await nav.leer_tabla(page)
        todas.extend(filas)
        print(f"    · pág {n}/{pags}: {len(filas)} filas (acum {len(todas)})", flush=True)
        if n % KEEPALIVE_CADA == 0 and n < pags:
            await nav.keepalive(page)
    return todas


def pre_filtrar(filas: list[dict], hoy: date) -> list[dict]:
    """Aplica los pre-filtros estructurales."""
    out = []
    for f in filas:
        if (f.get("tipo_contratacion") or "").strip().lower() != "bienes":
            continue
        if not modalidad_ok(f.get("modalidad")):
            continue
        if (f.get("estado") or "").strip().lower() != "vigente":
            continue
        fp = parse_fecha_sicoes(f.get("fecha_presentacion"))
        if fp is None or fp < hoy:
            continue
        out.append(f)
    return out


def clasificar(candidatas: list[dict], usar_ia: bool) -> list[dict]:
    """Agrega match_dicc / match_ia / relevante a cada candidata."""
    objetos = [c.get("objeto", "") for c in candidatas]

    # Filtro A — diccionario
    for c in candidatas:
        terms = rubros.match_rubros(c.get("objeto", ""))
        c["_dicc_terms"] = terms
        c["_match_dicc"] = len(terms) > 0

    # Filtro B — IA (con few-shot del criterio real del usuario: relevantes que
    # dejó + descartes por 'producto')
    if usar_ia and candidatas:
        pos, neg = db.ejemplos_entrenamiento()
        extra = f" | ejemplos: {len(pos)}✓ / {len(neg)}✗" if (pos or neg) else ""
        print(f"  → Clasificando {len(candidatas)} objetos con IA (Groq){extra}...", flush=True)
        veredictos = clasificador_ia.clasificar_lote(objetos, ejemplos_pos=pos, ejemplos_neg=neg)
    else:
        veredictos = [{"relevante": False, "razon": "IA desactivada"} for _ in candidatas]

    for c, v in zip(candidatas, veredictos):
        c["_match_ia"] = bool(v.get("relevante"))
        c["_ia_razon"] = v.get("razon", "")
        c["_relevante"] = c["_match_dicc"] or c["_match_ia"]
    return candidatas


def exportar_objetos_csv(candidatas: list[dict], hoy: date) -> str:
    """Exporta todas las candidatas (Bienes/modalidad/vigentes/abiertas) con sus
    veredictos → para refinar el diccionario de rubros."""
    os.makedirs(DIR_SALIDAS, exist_ok=True)
    ruta = os.path.join(DIR_SALIDAS, f"objetos_{hoy.isoformat()}.csv")
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cuce", "modalidad", "estado", "fecha_presentacion",
                    "dicc", "dicc_terminos", "ia", "ia_razon", "relevante", "objeto"])
        for c in candidatas:
            w.writerow([
                c.get("cuce"), c.get("modalidad"), c.get("estado"),
                c.get("fecha_presentacion"),
                "SI" if c["_match_dicc"] else "no",
                "|".join(c["_dicc_terms"]),
                "SI" if c["_match_ia"] else "no",
                c["_ia_razon"],
                "SI" if c["_relevante"] else "no",
                c.get("objeto"),
            ])
    return ruta


def fila_para_db(c: dict) -> dict:
    return {
        "cuce": c.get("cuce"),
        "entidad": c.get("entidad"),
        "objeto": c.get("objeto"),
        "modalidad": (c.get("modalidad") or "").strip().upper()[:10],
        "tipo_contratacion": c.get("tipo_contratacion"),
        "fecha_publicacion": iso(c.get("fecha_publicacion")),
        "fecha_presentacion": iso(c.get("fecha_presentacion")),
        "fecha_presentacion_raw": c.get("fecha_presentacion"),
        "estado": c.get("estado"),
        "match_dicc": c["_match_dicc"],
        "match_dicc_terminos": c["_dicc_terms"],
        "match_ia": c["_match_ia"],
        "match_ia_razon": c["_ia_razon"],
        "relevante": c["_relevante"],
        "archivos": c.get("archivos", []),
    }


async def descargar_dbcs(page, relevantes: list[dict]):
    """Descarga los archivos de cada convocatoria relevante, los convierte a PDF
    (los Word), los renombra según la convención y los sube a Supabase Storage."""
    import dbc_store
    print(f"\n  ⬇ Descargando + subiendo DBC de {len(relevantes)} convocatorias relevantes...", flush=True)
    for c in relevantes:
        cuce = c.get("cuce")
        modalidad = c.get("modalidad", "")
        archivos = c.get("archivos", [])
        if not archivos:
            print(f"    · {cuce}: sin archivos", flush=True)
            continue
        carpeta = os.path.join(DIR_DBC, cuce.replace("/", "_"))
        # Un solo documento objetivo por convocatoria:
        #   ANPE/ANPP/LP → Documento Base de Contratación; CM → Oferta del Proveedor
        objetivo = dbc_store.seleccionar_objetivo(modalidad, archivos)
        if not objetivo:
            print(f"    · {cuce}: no se encontró el documento objetivo "
                  f"({'Oferta' if modalidad=='CM' else 'DBC'})", flush=True)
            continue
        ruta = await nav.descargar_token(page, objetivo["token"], carpeta, objetivo.get("nombre", ""))
        locales = [{"ruta": ruta, "nombre": objetivo.get("nombre", "")}] if ruta else []
        subidos = dbc_store.procesar(cuce, modalidad, locales) if locales else []
        if subidos:
            db.marcar_dbc(cuce, carpeta, subidos)
        print(f"    · {cuce}: {objetivo.get('nombre','')} → {len(subidos)} archivo(s) a Storage", flush=True)


async def correr(desde: str, hasta: str, max_paginas: int, usar_ia: bool, descargar: bool,
                 marcar_corrida: bool = False):
    hoy = date.today()
    async with async_playwright() as p:
        print(f"Conectando a Chrome ({nav.CDP_URL})...", flush=True)
        try:
            browser, page = await nav.conectar(p)
        except Exception as e:
            print(f"\n❌ No se pudo conectar: {e}")
            print("\nAbrí Chrome con:")
            print('  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
            print('    --remote-debugging-port=9222 --user-data-dir="/tmp/chrome-sicoes"')
            return
        print("✓ Conectado. Navegando al buscador...", flush=True)
        await nav.ir_a_buscador(page)

        print(f"\n🔎 Buscando Bienes publicados {desde} → {hasta} (Vigentes)", flush=True)
        await nav.buscar_por_fechas(page, desde, hasta)

        filas = await recolectar(page, max_paginas)
        print(f"\n  Total filas leídas: {len(filas)}", flush=True)

        candidatas = pre_filtrar(filas, hoy)
        print(f"  Pre-filtradas (Bienes/CM-LP-ANPE-ANPP/Vigente/abiertas): {len(candidatas)}", flush=True)
        if not candidatas:
            print("\n  Nada que clasificar. Fin.", flush=True)
            return

        candidatas = clasificar(candidatas, usar_ia)
        relevantes = [c for c in candidatas if c["_relevante"]]
        solo_dicc = sum(1 for c in candidatas if c["_match_dicc"] and not c["_match_ia"])
        solo_ia = sum(1 for c in candidatas if c["_match_ia"] and not c["_match_dicc"])
        ambos = sum(1 for c in candidatas if c["_match_dicc"] and c["_match_ia"])

        csv_ruta = exportar_objetos_csv(candidatas, hoy)

        print(f"\n  📊 Relevantes: {len(relevantes)}  "
              f"(solo dicc: {solo_dicc} | solo IA: {solo_ia} | ambos: {ambos})", flush=True)
        print(f"  📄 Objetos exportados para refinar diccionario: {csv_ruta}", flush=True)

        # Guardar TODAS las candidatas en Supabase (con sus veredictos)
        rows = [fila_para_db(c) for c in candidatas]
        res = db.upsert(rows)
        if res.get("error"):
            print(f"  ⚠ Error guardando en Supabase: {res['error'][:200]}", flush=True)
        else:
            print(f"  ✓ Guardadas {res.get('count')} convocatorias en Supabase", flush=True)

        if descargar and relevantes:
            await descargar_dbcs(page, relevantes)

        if marcar_corrida:
            guardar_ultima_corrida(hoy)
            print(f"  🗓  Última corrida guardada: {hoy.isoformat()}", flush=True)

        print("\n✅ Radar terminado.", flush=True)


def main():
    hoy = date.today()
    ap = argparse.ArgumentParser(description="Radar de convocatorias SICOES")
    ap.add_argument("--desde", type=str, default=(hoy - timedelta(days=7)).strftime("%d/%m/%Y"),
                    help="Fecha publicación desde (dd/mm/yyyy). Default: hace 7 días.")
    ap.add_argument("--hasta", type=str, default=hoy.strftime("%d/%m/%Y"),
                    help="Fecha publicación hasta (dd/mm/yyyy). Default: hoy.")
    ap.add_argument("--max-paginas", type=int, default=0, help="Límite de páginas (0 = todas).")
    ap.add_argument("--no-ia", action="store_true", help="Desactivar filtro IA (solo diccionario).")
    ap.add_argument("--no-descargar", action="store_true", help="No descargar DBC.")
    ap.add_argument("--auto", action="store_true",
                    help="Corre desde la última corrida guardada hasta AYER (ignora el día actual). "
                         "Al terminar guarda la fecha de hoy. Ignora --desde/--hasta.")
    args = ap.parse_args()

    desde, hasta, marcar = args.desde, args.hasta, False
    if args.auto:
        marcar = True
        ayer = hoy - timedelta(days=1)
        ultima = leer_ultima_corrida()
        if ultima is None:
            # Primera corrida en --auto: arranca una semana atrás.
            ultima = hoy - timedelta(days=7)
            print(f"ℹ Sin corrida previa registrada. Arranco desde {ultima.strftime('%d/%m/%Y')}.", flush=True)
        if ultima > ayer:
            # Ya corrió hoy (o en el futuro): no hay días completos nuevos que revisar.
            print(f"✓ Ya se corrió el {ultima.strftime('%d/%m/%Y')}. "
                  f"No hay días nuevos cerrados para revisar. Nada que hacer.", flush=True)
            return
        desde = ultima.strftime("%d/%m/%Y")
        hasta = ayer.strftime("%d/%m/%Y")
        print(f"🤖 Modo auto: desde {desde} hasta {hasta} (sin incluir hoy).", flush=True)

    asyncio.run(correr(
        desde=desde, hasta=hasta, max_paginas=args.max_paginas,
        usar_ia=not args.no_ia, descargar=not args.no_descargar,
        marcar_corrida=marcar,
    ))


if __name__ == "__main__":
    main()
