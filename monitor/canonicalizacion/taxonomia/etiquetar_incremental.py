#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRENTE 1 — ETIQUETADOR INCREMENTAL robusto y recuperable (LLM, solo los PENDIENTES).
=============================================================================================
Etiqueta SOLO las descripciones que faltan (taxonomia_pendientes.json), nunca re-procesa el corpus
completo. Cada descripción lleva un ID ESTABLE ligado a su texto (sha1 del texto normalizado).
Robustez:
  · ID estable por texto (no por posición global).
  · Validación estricta: si el LLM devuelve menos ítems de los enviados, se identifican los IDs
    AUSENTES y se reintentan SOLO esos (no se re-piden los ya resueltos).
  · Detección de IDs duplicados (se conserva el primero, se cuenta el resto).
  · Checkpoint persistente SEPARADO (taxonomia_pendientes_checkpoint.jsonl) — NO toca el checkpoint
    histórico. Reanudación segura: al reiniciar, salta los IDs ya resueltos.
  · Presupuesto de tokens: si Groq responde "sin cupo diario" (TPD) en todas las keys, GUARDA el
    progreso y termina limpio (no bloquea el resto del proyecto).
  · Reporte de fallos (taxonomia_pendientes_fallos.json).

Correr (desde monitor/):
  ../scraper/venv/bin/python canonicalizacion/taxonomia/etiquetar_incremental.py --probe   # 1 lote, prueba cupo
  ../scraper/venv/bin/python canonicalizacion/taxonomia/etiquetar_incremental.py            # todos los pendientes
"""
import os, sys, json, time, hashlib, argparse, unicodedata, re
AQUI = os.path.dirname(os.path.abspath(__file__))
MON = "/Users/fabriziocuellar/Sicoes-Brain/monitor"
sys.path.insert(0, MON)
import canonicalizar_taxonomia as T   # reusa SYSTEM, _groq_chat, _extraer_json, failover y TPD

PENDIENTES = os.path.join(AQUI, "taxonomia_pendientes.json")
CK = os.path.join(AQUI, "taxonomia_pendientes_checkpoint.jsonl")
FALLOS = os.path.join(AQUI, "taxonomia_pendientes_fallos.json")
LOTE = 30


def sid(desc):
    n = unicodedata.normalize("NFD", desc or "")
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
    n = re.sub(r"\s+", " ", n).strip()
    return hashlib.sha1(n.encode()).hexdigest()[:12]


def cargar_resueltos():
    """IDs ya etiquetados en el checkpoint incremental (reanudación)."""
    resueltos = {}
    if not os.path.exists(CK):
        return resueltos
    for ln in open(CK, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        for e in o.get("etiquetas", []):
            if isinstance(e, dict) and e.get("id"):
                resueltos.setdefault(e["id"], e)
    return resueltos


def etiquetar_lote(trozo):
    """trozo: lista de {id,desc}. Devuelve (ok:list[etiqueta], faltantes:list[{id,desc}]).
    Liga por POSICIÓN cuando el conteo coincide; si no, por longitud mínima y marca el resto faltante."""
    numeradas = "\n".join(f"{i}. {t['desc']}" for i, t in enumerate(trozo))
    res = T.llamar(T.SYSTEM, numeradas)
    if res is None:
        return None, trozo  # None = sin cupo / fallo duro → el caller decide
    if not isinstance(res, list):
        return [], trozo
    ok = []
    usados = min(len(res), len(trozo))
    for pos in range(usados):
        et = res[pos]
        if not isinstance(et, dict):
            continue
        et = dict(et)
        et["id"] = trozo[pos]["id"]
        et["desc"] = trozo[pos]["desc"]   # texto ligado al id (no por índice global)
        ok.append(et)
    faltantes = trozo[usados:] if len(res) < len(trozo) else []
    # si hubo huecos (dict inválido) dentro del rango, también son faltantes
    ids_ok = {e["id"] for e in ok}
    faltantes += [t for t in trozo[:usados] if t["id"] not in ids_ok]
    return ok, faltantes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="solo 1 lote (prueba de cupo)")
    ap.add_argument("--max-lotes", type=int, default=None)
    args = ap.parse_args()

    data = json.load(open(PENDIENTES, encoding="utf-8"))
    pend = data["pendientes"]
    # dedup por id estable
    porid = {}
    for d in pend:
        porid.setdefault(sid(d), d)
    resueltos = cargar_resueltos()
    cola = [{"id": i, "desc": d} for i, d in porid.items() if i not in resueltos]
    print(f"pendientes: {len(porid)} únicos | ya resueltos: {len(resueltos)} | por etiquetar: {len(cola)}")
    if not cola:
        print("nada que etiquetar. ✓")
        return

    lotes = [cola[i:i + LOTE] for i in range(0, len(cola), LOTE)]
    if args.probe:
        lotes = lotes[:1]
    elif args.max_lotes:
        lotes = lotes[:args.max_lotes]

    fallos = []
    sin_cupo = False
    nuevos = 0
    ck = open(CK, "a", encoding="utf-8")
    for li, trozo in enumerate(lotes, 1):
        ok, faltantes = etiquetar_lote(trozo)
        if ok is None:   # sin cupo diario / fallo duro
            print(f"  lote {li}/{len(lotes)}: sin cupo o fallo duro → GUARDO progreso y corto")
            sin_cupo = True
            fallos += trozo
            break
        # reintento ÚNICO de faltantes (solo esos)
        if faltantes:
            ok2, faltan2 = etiquetar_lote(faltantes)
            if ok2:
                ok += ok2
            if ok2 is None:
                sin_cupo = True
                fallos += faltantes
            else:
                fallos += faltan2
        if ok:
            ck.write(json.dumps({"b": li, "etiquetas": ok}, ensure_ascii=False) + "\n")
            ck.flush()
            nuevos += len(ok)
        print(f"  lote {li}/{len(lotes)}: +{len(ok)} etiquetas"
              + (f" · {len(faltantes)} faltantes reintentados" if faltantes else ""))
        if sin_cupo:
            break
        time.sleep(1)
    ck.close()
    if fallos:
        json.dump({"total": len(fallos), "fallos": fallos}, open(FALLOS, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    resueltos = cargar_resueltos()
    print(f"\nnuevas etiquetas: {nuevos} | total resueltos ahora: {len(resueltos)} | "
          f"pendientes restantes: {len(porid) - len(resueltos)}")
    if sin_cupo:
        print("⚠ Se agotó el cupo diario de Groq (TPD). Progreso guardado; reanudar tras el reset "
              "(~20:00 Bolivia) corriendo el mismo comando. No bloquea los demás frentes.")
    if fallos:
        print(f"⚠ {len(fallos)} descripciones en taxonomia_pendientes_fallos.json para reintento.")


if __name__ == "__main__":
    main()
