"""Etapa 3 — extracción de especificaciones técnicas del DBC con LLM (Groq).

Recorre los DBC del corpus, recorta hacia la sección de specs (dbc_llm.clip_region),
extrae ítems+especificaciones con el LLM, y si el LLM devuelve 0 ítems cae al parser
determinista del docx (dbc.extract_blocks). Guarda un store JSONL reanudable.

Robusto a cortes (PC apagada, API caída, terminal cerrada):
- Escribe el resultado de CADA DBC al store de inmediato (append + fsync). Si se
  corta, lo ya hecho queda en disco; la siguiente corrida saltea lo completado y
  sigue. Una línea a medio escribir (crash en pleno write) se detecta y se re-hace.
- Rotación round-robin de las 4 cuentas Groq con cooldown ante 429 (bloqueo corto):
  si una cuenta se bloquea, sigue con las otras y vuelve a ella cuando enfría. Un
  429 por límite DIARIO (TPD) solo pausa hasta que esa cuenta reviva.
- Progreso consultable: imprime [hechos/total] y escribe progreso_specs.json.

Uso:
  python -m procesamiento.historico.extraer_specs --run <salida_etapa2>
  python -m procesamiento.historico.extraer_specs --run <salida_etapa2> --estado   # solo mostrar progreso
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Cargar monitor/.env ANTES de importar clasificador_ia (ahí lee las keys).
for _line in (ROOT / "monitor" / ".env").read_text().splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line and _line[0].isalpha():
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

sys.path.insert(0, str(ROOT / "monitor"))
import clasificador_ia as cia  # noqa: E402
from . import dbc, dbc_llm      # noqa: E402

CHUNK, SOLAPA, MAXC = 13000, 600, 7   # trozos grandes: la mayoría de DBC en 1 request
                                      # (menos repeticiones del prompt y menos cortes)
PACE_SECONDS = 1.2        # pausa mínima entre requests (repartida entre 4 cuentas)
COOLDOWN_429 = 60         # segundos que una cuenta queda en enfriamiento tras un 429


class KeyPool:
    """Round-robin de keys Groq con cooldown corto (TPM) y marca de agotada-por-hoy (TPD)."""
    def __init__(self, keys):
        self.keys = list(keys)
        self.cool = {k: 0.0 for k in self.keys}   # fin de cooldown corto (TPM)
        self.exhausted = set()                     # cuentas sin cupo diario (TPD)
        self.i = 0

    def mark_exhausted(self, key):
        self.exhausted.add(key)

    def all_exhausted(self):
        return len(self.exhausted) >= len(self.keys)

    def next_key(self, max_wait=90):
        """Siguiente cuenta con cupo. Si TODAS están agotadas por hoy (TPD) devuelve
        None AL INSTANTE (no espera). Para bloqueos cortos (TPM) espera hasta
        `max_wait`s a que alguna enfríe; si no, None."""
        avail = [k for k in self.keys if k not in self.exhausted]
        if not avail:
            return None
        deadline = time.monotonic() + max_wait
        n = len(self.keys)
        while True:
            for _ in range(n):
                k = self.keys[self.i % n]; self.i += 1
                if k in self.exhausted:
                    continue
                if time.monotonic() >= self.cool[k]:
                    return k
            soonest = min(self.cool[k] for k in avail)
            if soonest > deadline:
                return None
            time.sleep(max(0.0, min(soonest, deadline) - time.monotonic()) + 0.1)

    def penalize(self, key, seconds):
        self.cool[key] = time.monotonic() + seconds


# Groq va detrás de Cloudflare: sin un User-Agent de navegador devuelve 403 (1010).
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
COOLDOWN_TPD = 3600  # cupo diario agotado: parquear la cuenta hasta el reset (20:00 Bolivia)


def groq_chat(pool, region_chunk, prefer_key=None, timeout=60):
    """Una llamada de chat a Groq; nunca re-lanza (devuelve None si no logra
    respuesta tras probar las cuentas). `prefer_key`: cuenta fija del DBC en curso;
    solo se cambia si esa cuenta está bloqueada (429)."""
    payload = {"model": cia.GROQ_MODEL, "temperature": 0,
               "messages": [{"role": "system", "content": cia.DBC_SYSTEM},
                            {"role": "user", "content": "Texto del DBC / fichas técnicas:\n" + region_chunk}]}
    data = json.dumps(payload).encode()
    for attempt in range(len(pool.keys) * 3):
        if (attempt == 0 and prefer_key is not None and prefer_key not in pool.exhausted
                and time.monotonic() >= pool.cool.get(prefer_key, 0)):
            key = prefer_key
        else:
            key = pool.next_key()
            if key is None:        # ninguna cuenta con cupo → avisar al caller
                return None
        req = urllib.request.Request(cia.GROQ_URL, data=data, method="POST",
                                     headers={"Authorization": f"Bearer {key}",
                                              "Content-Type": "application/json", "User-Agent": _UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            cuerpo = ""
            try:
                cuerpo = e.read().decode()[:300]
            except Exception:
                pass
            if e.code == 429:
                try:
                    es_tpd = cia._es_tpd(cuerpo)
                except Exception:
                    es_tpd = False
                if es_tpd:                 # cupo DIARIO probado por Groq → agotada hoy
                    pool.mark_exhausted(key)
                else:                      # bloqueo por minuto (TPM) → se libera solo
                    pool.penalize(key, COOLDOWN_429)
                continue
            if e.code in (500, 502, 503):
                time.sleep(2); continue
            # 403/401/otros: transitorio (UA/Cloudflare/red) → cooldown corto y rotar,
            # NO marcar agotada por el día (puede recuperarse en segundos).
            pool.penalize(key, COOLDOWN_429)
            print(f"      ⚠ Groq HTTP {e.code}; cooldown corto y roto. {cuerpo[:100]}", flush=True)
            continue
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(2); continue
    return None


def extract_llm(pool, region):
    """Devuelve (items, responded). responded=False si la API no dio NINGUNA respuesta
    (cuota/red) → el DBC debe quedar PENDIENTE, nunca marcarse como vacío."""
    items, i, n, responded = [], 0, 0, False
    key = pool.next_key()        # UNA cuenta para todo este DBC (rota por proceso)
    if key is None:
        return [], False
    while i < len(region) and n < MAXC:
        content = groq_chat(pool, region[i:i + CHUNK], prefer_key=key)
        if content is None:      # API caída/sin cupo en pleno DBC → abortar sin falso vacío
            return cia._dedup_items(items), responded
        responded = True
        try:
            items += cia._parse_array(content)
        except Exception:
            pass
        i += CHUNK - SOLAPA; n += 1
        time.sleep(PACE_SECONDS)
    return cia._dedup_items(items), responded


def extract_docx(folder, doc_key, doc, cuce):
    """Fallback determinista: lee las celdas reales del docx."""
    v = next((v for v in reversed(doc.get("versions", [])) if v.get("valid")), None)
    if not v:
        return []
    original = folder / v["path"]
    md = folder / v.get("markdown", "")
    if not original.is_file():
        return []
    try:
        blocks, _ = dbc.extract_blocks(original, md.read_text(encoding="utf-8-sig") if md.is_file() else "",
                                       cuce, doc_key)
    except Exception:
        return []
    out = []
    for b in blocks:
        specs = [r.get("text", "") for r in b.get("requirements", []) if r.get("text")]
        out.append({"item": b.get("number"), "descripcion": b.get("title"),
                    "especificaciones": specs, "cantidad": b.get("quantity"), "unidad": b.get("unit")})
    return out


def dbc_list(run_dir):
    """DBC a procesar: (cuce, folder, doc_key, doc, md_path). Ordenado estable."""
    base = ROOT / "scraper/historico_local/data"
    import glob, re
    out = []
    for m in sorted(glob.glob(str(base) + "/historico_http_paginas_*/*/manifest.json")):
        if not re.search(r"/\d{2}-\d{4}-\d{2}-", m):
            continue
        d = json.loads(Path(m).read_text()); folder = Path(m).parent; cuce = d.get("cuce")
        for k, doc in (d.get("documents") or {}).items():
            if doc.get("kind") != "DBC":
                continue
            v = next((v for v in reversed(doc.get("versions", [])) if v.get("valid")), None)
            if not v or not v.get("markdown"):
                continue
            md = folder / v["markdown"]
            if md.is_file() and md.stat().st_size > 50:   # tamaño, sin leer todo (rápido)
                out.append((cuce, folder, k, doc, md)); break
    return out


def count_done(store):
    """Cuenta DBC completados sin modificar el store (para --estado, solo lectura)."""
    if not store.exists():
        return 0
    n = 0
    for line in store.read_bytes().splitlines():
        try:
            json.loads(line); n += 1
        except Exception:
            break
    return n


def load_done(store):
    """CUCE completados EXCLUYENDO el último (se re-hace por si quedó incompleto, como
    pide el flujo de continuar otro día). Trunca el store hasta antes de ese último
    válido + cualquier cola corrupta. Devuelve (done:set, redo:cuce|None)."""
    if not store.exists():
        return set(), None
    recs, pos = [], 0   # (cuce, offset_fin_de_linea)
    for line in store.read_bytes().splitlines(keepends=True):
        try:
            rec = json.loads(line)
        except Exception:
            break  # línea a medio escribir: cortar desde acá
        pos += len(line)
        recs.append((rec["cuce"], pos))
    if not recs:
        with open(store, "r+b") as fh:
            fh.truncate(0)
        return set(), None
    keep = recs[-2][1] if len(recs) >= 2 else 0   # dejar fuera el último válido
    redo = recs[-1][0]
    with open(store, "r+b") as fh:
        fh.truncate(keep)
    return set(c for c, _ in recs[:-1]), redo


def write_progress(prog_path, total, done, last_cuce, metodos):
    prog_path.write_text(json.dumps({
        "etapa": "3 — extraccion specs DBC (LLM)", "total": total, "hechos": done,
        "pendientes": total - done, "porcentaje": round(100 * done / max(1, total), 1),
        "ultimo_cuce": last_cuce, "metodos": metodos,
        "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="carpeta de salida de la etapa 2 (acquisitions)")
    ap.add_argument("--estado", action="store_true", help="solo mostrar progreso y salir")
    args = ap.parse_args()
    run_dir = Path(args.run)
    store = run_dir / "especificaciones_llm.jsonl"
    prog = run_dir / "progreso_specs.json"

    if args.estado:   # solo lectura, no toca el store (rápido, sin escanear markdown)
        print(prog.read_text() if prog.exists() else f"{count_done(store)} DBC hechos")
        return

    print("Revisando el corpus de DBC...", flush=True)
    todos = dbc_list(run_dir)
    total = len(todos)

    if not cia.GROQ_API_KEYS:
        print("ERROR: sin keys Groq (monitor/.env)", file=sys.stderr); sys.exit(1)
    done, redo = load_done(store)
    pool = KeyPool(cia.GROQ_API_KEYS)
    print(f"Etapa 3 — specs DBC. Total {total} DBC | ya hechos {len(done)} | "
          f"pendientes {total - len(done)} | cuentas Groq {len(pool.keys)}", flush=True)
    if redo:
        print(f"Reanudando: re-hago el último por si quedó incompleto → {redo}", flush=True)

    metodos = {"llm": 0, "docx": 0, "vacio": 0}
    hechos = len(done)
    sin_respuesta = 0   # DBC seguidos sin respuesta de la API → señal de cupo agotado
    for idx, (cuce, folder, dkey, doc, md) in enumerate(todos, 1):
        if cuce in done:
            continue
        v = next((vv for vv in reversed(doc.get("versions", [])) if vv.get("valid")), None)
        original = folder / v["path"] if v else None
        region = dbc_llm.region_for_llm(original, md.read_text(encoding="utf-8-sig"))
        items, responded = extract_llm(pool, region)
        if not responded:
            # La API no dio respuesta: NO marcar, queda pendiente. Si Groq confirmó
            # cupo DIARIO agotado en TODAS las cuentas, cortar al instante (probado, no
            # supuesto). Si fue algo transitorio en varias seguidas, también cortar.
            sin_respuesta += 1
            agotadas = pool.all_exhausted()
            motivo = "sin cupo diario (TPD) confirmado por Groq" if agotadas else "sin respuesta (transitorio)"
            print(f"[{hechos}/{total}] {cuce} → {motivo}; queda pendiente", flush=True)
            if agotadas or sin_respuesta >= max(4, len(pool.keys)):
                print(f"\n⏸  Groq sin cupo por hoy. Avance guardado: {hechos}/{total}.\n"
                      f"   Ya podés CERRAR esta ventana. Mañana (tras el reset de las "
                      f"20:00 Bolivia) volvé a correr este mismo comando y continúa solo.",
                      flush=True)
                break
            continue
        sin_respuesta = 0
        metodo = "llm"
        if not items:                       # el LLM respondió pero sin ítems → fallback docx
            items = extract_docx(folder, dkey, doc, cuce)
            metodo = "docx" if items else "vacio"
        metodos[metodo] += 1
        rec = {"cuce": cuce, "metodo": metodo, "n_items": len(items),
               "items": items, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(store, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush(); os.fsync(fh.fileno())
        hechos += 1
        write_progress(prog, total, hechos, cuce, metodos)
        print(f"[{hechos}/{total}] {cuce} → {metodo} ({len(items)} ítems)", flush=True)

    if hechos >= total:
        print(f"\n✅ ETAPA 3 COMPLETA: {hechos}/{total} DBC | métodos {metodos}", flush=True)
    else:
        print(f"\nPausado en {hechos}/{total} | métodos {metodos} | "
              f"relanzá el comando para continuar.", flush=True)


if __name__ == "__main__":
    main()
