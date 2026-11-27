#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalizador GENERICO de descripciones -> clave de agrupacion canonica.

Objetivo: colapsar el siloing de commodities sin reglas por familia. Opera sobre
hist_items.descripcion (que trae "<etiqueta UNSPSC> <requerimiento>") y produce una
clave robusta a: prefijo UNSPSC variable, medidas en mil formatos, ruido, mayus/acentos.

No reemplaza la FIRMA ESTRUCTURADA de consumibles con SKU (toner/part-number): esa sigue
mandando en recablear. Esto es el fallback para todo lo demas.
"""
import re, unicodedata

def strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

# sinonimos de familia (1a palabra significativa) — reutiliza criterio de recablear_v3
FAM_SYN = {
 'toner':'toner','tonner':'toner','cartucho':'toner','cartuchos':'toner','refil':'toner','refill':'toner',
 'drum':'toner','tambor':'toner','fusor':'fusor',
 'papel':'papel','papeles':'papel','resma':'papel','resmas':'papel','hoja':'papel','hojas':'papel',
 'silla':'silla','sillas':'silla','sillon':'silla','butaca':'silla',
 'disco':'almacenamiento','discos':'almacenamiento','memoria':'memoria','memorias':'memoria',
 'boligrafo':'boligrafo','boligrafos':'boligrafo','pluma':'boligrafo',
 'folder':'folder','folders':'folder','archivador':'archivador','archivadores':'archivador',
 'cable':'cable','cables':'cable','foco':'foco','focos':'foco','panel':'panel','paneles':'panel',
 'escoba':'escoba','trapo':'trapo','trapos':'trapo','franela':'franela',
}
# palabras-etiqueta UNSPSC y ruido que NO distinguen producto
STOP = {
 'de','para','con','color','tipo','material','tamano','medida','medidas','numero','familia',
 'presentacion','envase','contenido','aproximado','marca','modelo','la','el','los','las','del','al',
 'un','una','y','o','por','aprox','caja','cajas','unidad','unidades','pieza','piezas','paquete',
 'mts','cms','cm','mm','plg','pulg','pulgadas','grs','gr','gramaje','juego','juegos','jgs','global',
 'formas','continuas','continua','impresion','impresiones','impresora','impresoras','fotocopiadora',
 'computadores','computadoras','computador','offset','acuerdo','especificaciones','tecnicas','segun',
 'blanco','negro','surtido','original','originales','nuevo','sellado','troquelado','autocopiativo',
 'autocopiante','termico','termica','quimico','quimica','copiante','auto','en','e',
}

def _canon_medida(t):
    """Colapsa cualquier 'A x B x C (x D)' con numeros/fracciones a un token 'AxBxC'.
    Maneja ½, 1/2, separadores x/X/*/por, y 'plg/pulg' sueltos."""
    t = t.replace('½', '1/2').replace('¼', '1/4').replace('¾', '3/4')
    # unifica separadores de medida a 'x'
    t = re.sub(r'\s*[\*×]\s*', 'x', t)
    t = re.sub(r'(\d)\s+x\s+(\d)', r'\1x\2', t)
    t = re.sub(r'(\d)\s*(?:por)\s*(\d)', r'\1x\2', t)
    # numero con fraccion opcional: 9, 9.5, 9 1/2
    num = r'\d+(?:[.,]\d+)?(?:\s*\d/\d)?'
    def repl(m):
        parts = re.split(r'x', m.group(0))
        out = []
        for p in parts:
            p = p.strip().replace(' ', '').replace(',', '.')
            # 9 1/2 -> 9.5
            mm = re.match(r'^(\d+)(\d/\d)$', p)
            if mm:
                a = int(mm.group(1)); fr = mm.group(2)
                p = str(a + {'1/2': .5, '1/4': .25, '3/4': .75}.get(fr, 0))
            out.append(p)
        return 'MED' + 'x'.join(out)
    t = re.sub(rf'{num}(?:x{num}){{1,3}}', repl, t)
    return t

def clave(desc):
    """Clave de agrupacion canonica generica. Devuelve (familia, clave) o (None, None)."""
    t = strip_acc((desc or '').lower())
    t = _canon_medida(t)
    t = re.sub(r'[^a-z0-9/.]+', ' ', t)        # deja letras, digitos, / y . (medidas)
    toks = [w for w in t.split() if w]
    # familia = 1a palabra significativa no-stop
    fam = None
    for w in toks:
        base = re.sub(r'[0-9/.]', '', w)
        if len(base) >= 3 and base not in STOP:
            fam = FAM_SYN.get(base, base); break
    if not fam:
        return None, None
    # atributos significativos: medidas (MED...), numeros+unidad, palabras >=3 no-stop
    attrs = set()
    for w in toks:
        if w.startswith('med') and any(c.isdigit() for c in w):
            attrs.add(w)                        # medida canonica
        elif re.fullmatch(r'\d+[a-z]*', w):     # 56gr, 1000, 220v
            attrs.add(w)
        else:
            base = re.sub(r'[0-9/.]', '', w)
            if len(base) >= 3 and base not in STOP and base != fam:
                attrs.add(FAM_SYN.get(base, base))
    k = fam + '|' + '|'.join(sorted(attrs)) if attrs else fam
    return fam, k

if __name__ == '__main__':
    import sys
    for line in sys.stdin:
        line = line.strip()
        if line:
            print(clave(line), '<-', line[:70])
