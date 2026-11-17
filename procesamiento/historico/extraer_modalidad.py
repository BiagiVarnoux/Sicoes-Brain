"""Etapa 3b — forma de adjudicación (por el total / por ítems / por lotes / por tramos).

Dato AUTORITATIVO para la auditoría de conteo: un proceso 'por el total' exige que
el nº de ítems extraídos == nº de fichas (todo o nada); 'por ítems'/'por lotes'
admite ítems desiertos (DBC > fichas legítimo). Sin este flag no se puede distinguir
un error de extracción de una diferencia legítima.

Fuente: el HTML del FORM_100 (y FORM_110 como respaldo), donde el valor viene como
texto estructurado:
    <td class="FormularioEtiqueta">Forma de adjudicación</td> : <td class="FormularioDato">Por el Total</td>
NO se usa el Markdown del DBC: ahí la opción marcada es una casilla 'X' cuya posición
no permite saber a qué etiqueta liga (se verificó que liga a la SIGUIENTE, no la
anterior, invirtiendo el resultado) — el HTML no tiene esa ambigüedad.

Store reanudable: forma_adjudicacion.jsonl en el run_dir, una línea por CUCE
    {cuce, forma, fuente, valor_crudo, ts}
donde forma ∈ {total, items, lotes, tramos, otro, sin_html}. Reanuda salteando los
CUCE ya resueltos; con --rehacer-sin-html reintenta solo los 'sin_html' (p.ej. tras
ampliar la búsqueda de formularios). Lectura 100% local, sin red ni Groq.

Uso:
  python -m procesamiento.historico.extraer_modalidad --run <salida_etapa2>
  python -m procesamiento.historico.extraer_modalidad --run <salida_etapa2> --estado
  python -m procesamiento.historico.extraer_modalidad --run <salida_etapa2> --rehacer-sin-html
"""
import argparse
import datetime
import glob
import json
import os
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "scraper/historico_local/data"

# formularios donde aparece el campo, en orden de preferencia
FORM_GLOBS = ("crudos/FORM_100*.html", "http/FORM_100*.html",
              "crudos/FORM_110*.html", "http/FORM_110*.html")
_VALMAP = (("total", re.compile(r"por el total")), ("items", re.compile(r"por [ií]tem")),
           ("lotes", re.compile(r"por lote")), ("tramos", re.compile(r"por tramo")))


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def procesos_list():
    """(cuce, folder) de cada proceso del corpus, orden estable. Sin leer HTML."""
    out = []
    for m in sorted(glob.glob(str(CORPUS) + "/historico_http_paginas_*/*/manifest.json")):
        if not re.search(r"/\d{2}-\d{4}-\d{2}-", m):
            continue
        try:
            cuce = json.loads(Path(m).read_text()).get("cuce")
        except Exception:
            continue
        if cuce:
            out.append((cuce, Path(m).parent))
    return out


def leer_forma(folder):
    """Devuelve (forma, fuente, valor_crudo). Busca 'Forma de adjudicación' en el HTML
    del FORM_100/110 y toma el FormularioDato de la MISMA fila."""
    for pat in FORM_GLOBS:
        for f in folder.glob(pat):
            try:
                html = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "adjudicaci" not in html.lower():
                continue
            soup = BeautifulSoup(html, "html.parser")
            for td in soup.find_all("td"):
                if not _norm(td.get_text()).startswith("forma de adjudicaci"):
                    continue
                tr = td.find_parent("tr")
                if not tr:
                    continue
                celdas = tr.find_all("td")
                crudo = _norm(celdas[-1].get_text()) if celdas else ""
                for name, pr in _VALMAP:
                    if pr.search(crudo):
                        return name, f.name.split("__")[0], crudo
                # Hay formularios (FORM_110) con un campo homónimo cuyo valor es un
                # booleano 'si'/'no' — NO es la modalidad; se ignora y se sigue buscando.
    return "sin_html", None, None


def cargar_store(store):
    """{cuce: forma} de lo ya hecho (última línea gana). Trunca cola corrupta."""
    if not store.exists():
        return {}
    recs, pos = [], 0
    for line in store.read_bytes().splitlines(keepends=True):
        try:
            r = json.loads(line)
        except Exception:
            break
        pos += len(line)
        recs.append((r["cuce"], r.get("forma"), pos))
    if recs:
        with open(store, "r+b") as fh:   # corta cualquier basura al final
            fh.truncate(recs[-1][2])
    return {c: forma for c, forma, _ in recs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="carpeta de salida de la etapa 2 (acquisitions)")
    ap.add_argument("--estado", action="store_true", help="solo mostrar progreso y salir")
    ap.add_argument("--rehacer-sin-html", action="store_true",
                    help="reintenta solo los CUCE que quedaron 'sin_html'")
    args = ap.parse_args()
    run_dir = Path(args.run)
    store = run_dir / "forma_adjudicacion.jsonl"

    hecho = cargar_store(store)
    if args.estado:
        from collections import Counter
        dist = Counter(hecho.values())
        print(f"forma_adjudicacion.jsonl: {len(hecho)} CUCE")
        for k, v in dist.most_common():
            print(f"  {v:>5}  {k}")
        return

    procesos = procesos_list()
    saltar = set(hecho)
    if args.rehacer_sin_html:
        saltar = {c for c, forma in hecho.items() if forma != "sin_html"}
    pend = [(c, fo) for c, fo in procesos if c not in saltar]
    print(f"procesos: {len(procesos)} | ya hechos: {len(saltar)} | a procesar: {len(pend)}")

    from collections import Counter
    dist = Counter()
    with open(store, "a") as fh:
        for i, (cuce, folder) in enumerate(pend, 1):
            forma, fuente, crudo = leer_forma(folder)
            fh.write(json.dumps({"cuce": cuce, "forma": forma, "fuente": fuente,
                                 "valor_crudo": crudo,
                                 "ts": datetime.datetime.now().isoformat(timespec="seconds")},
                                ensure_ascii=False) + "\n")
            dist[forma] += 1
            if i % 200 == 0:
                fh.flush(); os.fsync(fh.fileno())
                print(f"  [{i}/{len(pend)}] {dict(dist)}")
        fh.flush(); os.fsync(fh.fileno())
    print(f"LISTO. nuevos: {dict(dist)}")
    print("Distribución total:")
    for k, v in Counter(cargar_store(store).values()).most_common():
        print(f"  {v:>5}  {k}")


if __name__ == "__main__":
    main()
