"""Conciliación: ítems ESPERADOS (de los formularios) vs ítems EXTRAÍDOS del DBC
por la API, por proceso. Marca dónde no cuadran, para revisar extracciones
incompletas o infladas.

- Esperados = nº de fichas (líneas de producto) del proceso en la etapa 2.
- Extraídos = nº de ítems que la API/LLM sacó del DBC (store especificaciones_llm.jsonl).

Uso:
  python -m procesamiento.historico.conciliar_specs --run <salida_etapa2>
"""
import argparse
import collections
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--full", action="store_true", help="listar todos los desajustes, no solo el top")
    args = ap.parse_args()
    run = Path(args.run)

    # Esperados: fichas por CUCE (líneas de producto reales del proceso)
    esperados = collections.Counter()
    with open(run / "fichas.jsonl") as fh:
        for line in fh:
            esperados[json.loads(line)["cuce"]] += 1

    store = run / "especificaciones_llm.jsonl"
    if not store.exists():
        print("Aún no hay store de specs."); return
    rows = [json.loads(l) for l in open(store)]

    out = []
    for r in rows:
        cuce = r["cuce"]; exp = esperados.get(cuce, 0); got = r["n_items"]
        estado = ("SIN_FICHAS" if exp == 0 else
                  "OK" if got == exp else
                  "VACIO" if got == 0 else
                  "FALTAN" if got < exp else "SOBRAN")
        out.append({"cuce": cuce, "esperados": exp, "extraidos": got,
                    "metodo": r["metodo"], "diff": got - exp, "estado": estado})

    resumen = collections.Counter(o["estado"] for o in out)
    cubiertos = sum(min(o["extraidos"], o["esperados"]) for o in out)
    total_esp = sum(o["esperados"] for o in out)
    print(f"Procesos con DBC procesado: {len(out)}")
    print(f"Estados: {dict(resumen)}")
    print(f"Cobertura de ítems (extraídos∩esperados / esperados): {cubiertos}/{total_esp} "
          f"({100*cubiertos//max(1,total_esp)}%)")
    desaj = [o for o in out if o["estado"] in ("FALTAN", "VACIO", "SOBRAN")]
    desaj.sort(key=lambda o: abs(o["diff"]), reverse=True)
    muestra = desaj if args.full else desaj[:15]
    print(f"\nDesajustes ({len(desaj)}{' — top 15' if not args.full else ''}):")
    for o in muestra:
        print(f"  {o['cuce']}  esperados {o['esperados']} / extraídos {o['extraidos']}"
              f"  ({o['estado']}, {o['metodo']})")

    rep = run / "conciliacion_specs.jsonl"
    rep.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out))
    print(f"\nReporte: {rep}")


if __name__ == "__main__":
    main()
