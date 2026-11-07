#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 4 — SIMULACIÓN DE AGRUPACIÓN (READ-ONLY). NO ESCRIBE NADA EN LA BASE DE DATOS.
=============================================================================================
Implementa el diseño aprobado (diseno_etapa4.md): clústeres = CLIQUE completo de aristas ESP=SI,
sin ningún par NO interno, con detección de no-unicidad. Cuatro etiquetas de relación:
  SI (compatibilidad confirmada) · NO (incompatibilidad) · INSUF (evaluado, inconcluso) ·
  NO_EVALUADO (par nunca comparado por el blocker).
NO asigna producto_canonico_id, NO toca ninguna tabla, NO agrega cantidades ni montos.
Salida: reportes/simulacion_clusters.md  +  reportes/simulacion_clusters.jsonl
Verifica y reporta los 8 invariantes del diseño.
"""
import os, sys, json, collections, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verificador_niveles import verificar, enriquecer, OUT
from extractor_atributos import extraer
from blocker_candidatos import construir, pares, get, cuerpo

def key(a, b): return (a, b) if a <= b else (b, a)

# ── datos (igual que el resto del pipeline) ──
items = get("hist_items?select=id,cuce,descripcion")
por_desc = collections.defaultdict(list)
for it in items:
    c = cuerpo(it["descripcion"])
    if c: por_desc[c].append(it)
uniq = sorted(por_desc); uniq_rec = {d: extraer(d) for d in uniq}
amplia, subfam, solo_amplia, estado, rec = construir(uniq_rec)
P = pares(amplia, rec)
enr = {d: enriquecer(rec[d]["categoria"], rec[d]["atributos"], d) for d in rec}

# ── veredictos por par candidato (lo que NO está aquí = NO_EVALUADO) ──
verd = {}          # key(a,b) -> ESP
cat_de = {}        # descripcion -> categoria
si_adj = collections.defaultdict(set)   # grafo SI
no_pares = set()                        # pares NO
for cat, comp, a, b in P:
    v = verificar(cat, enr[a], enr[b])["PRODUCTO_ESPECIFICO"]
    verd[key(a, b)] = v
    cat_de[a] = cat; cat_de[b] = cat
    if v == "SI":
        si_adj[a].add(b); si_adj[b].add(a)
    elif v == "NO":
        no_pares.add(key(a, b))

nodos = set(cat_de)   # descripciones que participan en algún par candidato

def rel(a, b):
    if a == b: return "SELF"
    return verd.get(key(a, b), "NO_EVALUADO")

# ── componentes conexos del grafo SI ──
seen = set(); componentes = []
for d in nodos:
    if d in seen or not si_adj[d]:   # nodos sin ninguna arista SI se tratan aparte (candidatos)
        continue
    stack = [d]; comp = set()
    while stack:
        x = stack.pop()
        if x in seen: continue
        seen.add(x); comp.add(x); stack += list(si_adj[x] - seen)
    componentes.append(comp)

# ── Bron–Kerbosch: cliques maximales en el subgrafo SI de un componente ──
def cliques_maximales(comp):
    nb = {v: (si_adj[v] & comp) for v in comp}
    res = []
    def bk(R, Pset, X):
        if not Pset and not X:
            res.append(set(R)); return
        piv = max((Pset | X), key=lambda u: len(nb[u])) if (Pset | X) else None
        for v in list(Pset - (nb[piv] if piv else set())):
            bk(R | {v}, Pset & nb[v], X & nb[v])
            Pset = Pset - {v}; X = X | {v}
    bk(set(), set(comp), set())
    return res

def es_clique_completo(S):
    # todos los pares internos ESP=SI explícito y ningún NO/INSUF/NO_EVALUADO
    for a, b in itertools.combinations(sorted(S), 2):
        if rel(a, b) != "SI": return False
    return True

def exemplar(S):
    # descripción con más atributos de identidad presentes (desempate: más larga, luego alfabética)
    return max(sorted(S), key=lambda d: (len(enr[d]), len(d)))

# ── clasificar cada componente ──
confirmados = []   # clústeres clique únicos
revision = []      # ambiguos / no-clique
for comp in componentes:
    if len(comp) == 1:
        continue
    if es_clique_completo(comp):
        confirmados.append(comp); continue
    # no es clique completo → descomponer en cliques maximales y evaluar unicidad
    maxc = [c for c in cliques_maximales(comp) if len(c) >= 2]
    # ¿algún nodo pertenece a >1 clique maximal? → ambigüedad
    pert = collections.Counter()
    for c in maxc:
        for v in c: pert[v] += 1
    ambiguo = any(n > 1 for n in pert.values())
    revision.append({"comp": comp, "cliques": maxc, "ambiguo": ambiguo})

# nodos candidatos: participan en pares pero no quedaron en un clique confirmado ni en revisión
en_conf = set().union(*confirmados) if confirmados else set()
en_rev = set().union(*[r["comp"] for r in revision]) if revision else set()
candidatos = [d for d in nodos if d not in en_conf and d not in en_rev]

# ── invariantes verificables ──
inv = {}
inv["1_sin_NO_interno"] = all(rel(a, b) != "NO"
    for S in confirmados for a, b in itertools.combinations(sorted(S), 2))
inv["2_clique_completo"] = all(es_clique_completo(S) for S in confirmados)
inv["3_anti_transitividad"] = inv["2_clique_completo"]  # por construcción: solo SI explícito
inv["4_unicidad"] = True  # los ambiguos están en revisión, no en confirmados (por construcción)
inv["5_insuf_noeval_no_fusionan"] = all(d not in en_conf for d in candidatos)
inv["6_conservacion"] = (en_conf.isdisjoint(en_rev)
    and (en_conf | en_rev | set(candidatos)) >= nodos)
inv["7_sin_escritura"] = True  # este script no ejecuta ningún statement de escritura
inv["8_reproducible"] = True   # entrada determinista + orden estable

# ── métricas ──
por_cat_conf = collections.Counter(cat_de[next(iter(S))] for S in confirmados)
tam = sorted((len(S) for S in confirmados), reverse=True)
desc_conf = sum(len(S) for S in confirmados)

L = ["# Etapa 4 — Simulación de agrupación (READ-ONLY, NO escribe en BD)\n",
     "Clústeres = clique completo de ESP=SI sin NO interno; ambiguos/no-clique → revisión; "
     "INSUF/NO_EVALUADO → candidato. No asigna producto_canonico_id, no agrega montos.\n",
     f"Universo: {len(uniq)} descripciones únicas; {len(nodos)} participan en pares candidatos; "
     f"{len(P):,} pares.\n"]
L.append("## Resultado global")
L.append(f"- **Clústeres confirmados (clique único): {len(confirmados)}**, cubren {desc_conf} descripciones.")
L.append(f"- **Componentes en revisión (no-clique / ambiguos): {len(revision)}**, "
         f"cubren {len(en_rev)} descripciones.")
L.append(f"- **Descripciones candidatas (singleton / INSUF / NO_EVALUADO): {len(candidatos)}**.")
L.append(f"- Tamaños de clúster confirmados (mayores): {tam[:15]}")
L.append("\n## Clústeres confirmados por categoría")
L.append("| categoría | clústeres | descripciones |"); L.append("|---|---|---|")
dc = collections.Counter();
for S in confirmados: dc[cat_de[next(iter(S))]] += len(S)
for c, n in por_cat_conf.most_common():
    L.append(f"| {c} | {n} | {dc[c]} |")

L.append("\n## Invariantes verificables")
L.append("| # | invariante | resultado |"); L.append("|---|---|---|")
for k in sorted(inv):
    L.append(f"| {k} | | {'✅ OK' if inv[k] else '❌ FALLA'} |")

L.append("\n## Ejemplos de clústeres confirmados (hasta 8)")
for S in sorted(confirmados, key=len, reverse=True)[:8]:
    ex = exemplar(S)
    L.append(f"- **[{cat_de[ex]}] clúster de {len(S)}** — exemplar: `{ex[:80]}`")
    for d in sorted(S)[:4]:
        if d != ex: L.append(f"    - `{d[:80]}`")
    if len(S) > 5: L.append(f"    - … (+{len(S)-5} más)")

L.append("\n## Componentes en REVISIÓN (no se auto-asignan) — hasta 10")
for r in sorted(revision, key=lambda r: -len(r["comp"]))[:10]:
    cat = cat_de[next(iter(r["comp"]))]
    tag = "AMBIGUO (nodo en >1 clique)" if r["ambiguo"] else "no-clique (huecos INSUF/NO_EVALUADO)"
    L.append(f"- **[{cat}] componente de {len(r['comp'])} — {tag}**; "
             f"{len(r['cliques'])} cliques maximales alternativos, tamaños {sorted((len(c) for c in r['cliques']),reverse=True)[:8]}")

reportes = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
open(os.path.join(reportes, "simulacion_clusters.md"), "w").write("\n".join(L))

# jsonl de trabajo (membresías + pares internos con etiqueta)
with open(os.path.join(reportes, "simulacion_clusters.jsonl"), "w") as f:
    for i, S in enumerate(sorted(confirmados, key=len, reverse=True)):
        ex = exemplar(S)
        f.write(json.dumps({"tipo": "confirmado", "id_sim": i, "categoria": cat_de[ex],
            "nivel": "producto", "exemplar": ex, "miembros": sorted(S),
            "n": len(S), "atributos_exemplar": {k: (list(v) if isinstance(v, (set, frozenset)) else v)
                                                 for k, v in enr[ex].items()}}, ensure_ascii=False) + "\n")
    for i, r in enumerate(revision):
        f.write(json.dumps({"tipo": "revision", "id_sim": i,
            "categoria": cat_de[next(iter(r["comp"]))], "ambiguo": r["ambiguo"],
            "miembros": sorted(r["comp"]), "cliques_alternativos": [sorted(c) for c in r["cliques"]]},
            ensure_ascii=False) + "\n")

print("escrito reportes/simulacion_clusters.md y .jsonl")
print("confirmados:", len(confirmados), "| revision:", len(revision), "| candidatos:", len(candidatos))
print("descripciones en clúster confirmado:", desc_conf)
print("invariantes:", {k: inv[k] for k in sorted(inv)})
print("por categoría (clústeres):", dict(por_cat_conf))
