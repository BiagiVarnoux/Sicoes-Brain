#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consolidación de hojas LOCAL (sin LLM, sin Groq).
=================================================
Toma `taxonomia_propuesta.json` (ya con categorías consolidadas) y fusiona las
HOJAS que son el mismo producto, con un normalizador curado a mano:

  * COLAPSA ruido que NO discrimina: subcategoría, prefijo de marca
    (HP/Brother/Canon/…), palabras de relleno ("de","para","tipo","unidad"…),
    separadores, tildes, mayúsculas, el genérico "toner/cartucho".
  * PRESERVA lo que SÍ discrimina: números, medidas (62mm≠102mm, 8x8≠8x7),
    gramaje (75g), capacidad (8GB), generación (DDR3≠DDR4), color (BK/C/M/Y),
    y palabras como "ancho/medio", "sin aceite", "doble".
  * Tabla de EQUIVALENCIAS de códigos (criterio de dominio): HP 78A = CE278A,
    12A = Q2612A, 26A = CF226A, 30A = CF230A, 83A = CF283A, 85A = CE285A,
    05A = CE505A, 35A = CB435A, 36A = CB436A, 80A = CF280, 80X = CF280X.
  * NO fusiona distintos: 78A≠78B≠78X, TN-217≠TN-221≠TN-225, color≠color.

Regla de oro: ante la duda, NO fusiona (deja la hoja aparte). El usuario cura
el remanente una sola vez.

Salida: reescribe taxonomia_propuesta.{json,md} y deja un reporte de los
grupos fusionados en consolidacion_local_reporte.txt para revisar.
"""
import json
import re
import unicodedata
import sys
from collections import defaultdict

JSON_IN = "taxonomia_propuesta.json"

# --- categorías que son sinónimos y deben unirse (criterio de dominio) ---
CAT_ALIAS = {
    "Switch de red": "Switches",
    "Switches de red": "Switches",
    "Conmutadores de red": "Switches",
    "Switch de red ": "Switches",
    "Switches POE": "Switch PoE",
    "Switch POE": "Switch PoE",
    "Switches POE ": "Switch PoE",
    "Dispositivos de almacenamiento": "Almacenamiento",
    "Productos de higiene": "Higiene personal",
}

# marcas y genéricos que NO discriminan al producto (se quitan del texto)
MARCAS = {
    "hp", "brother", "canon", "lexmark", "epson", "samsung", "konica",
    "minolta", "ricoh", "pantum", "kyocera", "xerox", "toner", "tóner",
    "cartucho", "cartuchos",
}
# palabras de relleno que no discriminan
STOP = {
    "de", "del", "la", "el", "los", "las", "para", "con", "y", "a", "en",
    "un", "una", "uno", "unidad", "und", "u", "tipo", "color",
}
# ruido de ROL/MÁQUINA en la subcategoría de consumibles (no es el producto):
# "Fotocopiadora :: TN3479" es el mismo tóner que "Tóner :: TN3479".
# Solo se quita dentro de "Consumibles de impresión" para no romper otras cats.
NOISE_SUB_CONSUMIBLES = {
    "fotocopiadora", "fotocopiadoras", "impresora", "impresoras",
    "laserjet", "laser", "multifuncional", "equipo",
}
# equivalencias de código de consumible (se aplican sobre el texto normalizado,
# más largas primero para no romper prefijos)
EQUIV = [
    ("ce278a", "78a"), ("ce278", "78a"),
    ("q2612a", "12a"),
    ("cf226a", "26a"), ("cf226", "26a"),
    ("cf230a", "30a"), ("cf230", "30a"),
    ("cf283a", "83a"), ("cf83a", "83a"),
    ("ce285a", "85a"), ("ce285", "85a"),
    ("ce505a", "05a"),
    ("cb435a", "35a"), ("cb436a", "36a"),
    ("cf280x", "80x"), ("cf280", "80a"),
]


def _sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                    if unicodedata.category(c) != "Mn")


def _tok(texto, quitar):
    texto = _sin_acentos(texto or "").lower()
    texto = texto.replace("×", "x").replace("‑", "-").replace("–", "-")
    toks = re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?", texto)
    return [t for t in toks if t not in quitar]


def clave(cat, sub, prod):
    """Llave de fusión por PRODUCTO (la subcategoría suele ser ruido: Clips /
    Plástico / Bulldog son la misma familia). Colapsa marca/relleno/separadores
    pero preserva números, medidas, color, gramaje, generación.

    Excepción: si el producto es GENÉRICO (vacío o "(genérico)"), la info está
    en la subcategoría (Tambor/Tinta/Tóner), así que ahí SÍ se usa el tipo —
    quitando marca y relleno — para no mezclar tambor con tinta."""
    quitar = set(MARCAS) | set(STOP)
    base_toks = _tok(prod, quitar)
    base = "".join(base_toks)
    es_generico = (base == "" or "generico" in base or len(base) < 3)
    if es_generico:
        sub_toks = _tok(sub, quitar | NOISE_SUB_CONSUMIBLES)
        base = "".join(sub_toks) + base
    for a, b in EQUIV:
        base = base.replace(a, b)
    return base or "(vacio)"


def main():
    data = json.load(open(JSON_IN, encoding="utf-8"))

    # 1) aplanar a hojas, aplicando alias de categoría
    #    hoja: (cat, sub, prod, n, attrs:set, ejemplos:list)
    hojas = []
    for c in data["categorias"]:
        cat = CAT_ALIAS.get(c["categoria"], c["categoria"])
        for s in c["subcategorias"]:
            for p in s["productos"]:
                hojas.append({
                    "cat": cat,
                    "sub": s["subcategoria"],
                    "prod": p["producto_canonico"],
                    "n": p["n_items"],
                    "attrs": set(p.get("atributos_discriminantes", [])),
                    "ej": list(p.get("ejemplos", [])),
                })

    # 2) agrupar por (categoría, clave de fusión)
    grupos = defaultdict(list)
    for h in hojas:
        grupos[(h["cat"], clave(h["cat"], h["sub"], h["prod"]))].append(h)

    # 3) construir árbol consolidado + reporte de fusiones
    arbol = {}           # cat -> sub -> prod -> {n, attrs, ej}
    fusiones = []        # (cat, canonico, [miembros])
    for (cat, k), miembros in grupos.items():
        # representante: mayor n; empate -> string más largo (más descriptivo)
        rep = sorted(miembros, key=lambda m: (-m["n"], -len(m["prod"] or "")))[0]
        sub_rep = rep["sub"]
        # si el representante tiene sub null pero otro miembro tiene sub, usar esa
        if not sub_rep:
            for m in sorted(miembros, key=lambda m: -m["n"]):
                if m["sub"]:
                    sub_rep = m["sub"]
                    break
        prod_rep = rep["prod"]
        n = sum(m["n"] for m in miembros)
        attrs = set().union(*[m["attrs"] for m in miembros]) if miembros else set()
        ej = []
        for m in sorted(miembros, key=lambda m: -m["n"]):
            for e in m["ej"]:
                if e not in ej:
                    ej.append(e)
        ej = ej[:3]
        nodo = arbol.setdefault(cat, {}).setdefault(sub_rep, {})
        if prod_rep in nodo:  # colisión rara: distinta clave, mismo nombre -> sumar
            nodo[prod_rep]["n"] += n
            nodo[prod_rep]["attrs"].update(attrs)
        else:
            nodo[prod_rep] = {"n": n, "attrs": attrs, "ej": ej}
        if len(miembros) > 1:
            fusiones.append((cat, f"{sub_rep or 'null'} :: {prod_rep}",
                             sorted({f"{m['sub'] or 'null'} :: {m['prod']}" for m in miembros})))

    # 4) serializar igual que el script original
    cats = []
    for cat in sorted(arbol):
        subs = []
        n_cat = 0
        for sub in sorted(arbol[cat], key=lambda x: (x is None, x or "")):
            prods = []
            for prod in sorted(arbol[cat][sub]):
                h = arbol[cat][sub][prod]
                n_cat += h["n"]
                prods.append({
                    "producto_canonico": prod,
                    "n_items": h["n"],
                    "atributos_discriminantes": sorted(h["attrs"]),
                    "ejemplos": h["ej"],
                })
            subs.append({"subcategoria": sub,
                         "n_items": sum(x["n_items"] for x in prods),
                         "productos": prods})
        cats.append({"categoria": cat, "n_items": n_cat, "subcategorias": subs})
    cats.sort(key=lambda c: c["n_items"], reverse=True)
    out = {"categorias": cats,
           "total_hojas": sum(len(s["productos"]) for c in cats for s in c["subcategorias"])}

    json.dump(out, open(JSON_IN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # markdown
    md = ["# Taxonomía propuesta (Pasada 1 — para CURAR)\n",
          f"_{len(out['categorias'])} categorías · {out['total_hojas']} productos canónicos (hojas)_\n",
          "> Revisá y editá: fusionar hojas que son el mismo producto, separar "
          "las que no, corregir atributos. Esto se cura UNA vez.\n"]
    for c in out["categorias"]:
        md.append(f"\n## {c['categoria']}  _(n={c['n_items']})_")
        for s in c["subcategorias"]:
            if s["subcategoria"]:
                md.append(f"\n### {s['subcategoria']}  _(n={s['n_items']})_")
            for p in s["productos"]:
                attr = (" · attrs: " + ", ".join(p["atributos_discriminantes"])) if p["atributos_discriminantes"] else ""
                md.append(f"- **{p['producto_canonico']}** _(n={p['n_items']})_{attr}")
                for ej in p["ejemplos"]:
                    md.append(f"    - _{ej[:120]}_")
    open("taxonomia_propuesta.md", "w", encoding="utf-8").write("\n".join(md) + "\n")

    # reporte de fusiones (para revisar que no sobre-fusione)
    fusiones.sort(key=lambda f: -len(f[2]))
    rep_lines = [f"FUSIONES: {len(fusiones)} grupos fusionaron ≥2 hojas\n"]
    for cat, canon, miembros in fusiones:
        rep_lines.append(f"[{cat}] → {canon}")
        for m in miembros:
            rep_lines.append(f"      · {m}")
    open("consolidacion_local_reporte.txt", "w", encoding="utf-8").write("\n".join(rep_lines) + "\n")

    print(f"total hojas: {data['total_hojas']} → {out['total_hojas']}")
    print(f"categorías: {len(data['categorias'])} → {len(out['categorias'])}")
    print(f"grupos fusionados (≥2 hojas): {len(fusiones)}")


if __name__ == "__main__":
    main()
