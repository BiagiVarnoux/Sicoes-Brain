"""
SICOES Items Scraper — CDP Edition v2
======================================
Abre TODOS los formularios disponibles por proceso (FORM200, FORM220, FORM110,
FORM100, FORM170, FORM500) en lugar de solo uno.

ANTES DE CORRER:
  1. Cerrar Chrome completamente.
  2. Abrir Chrome con debugging habilitado:
       /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
         --remote-debugging-port=9222
         --user-data-dir="/tmp/chrome-sicoes"
  3. Navegar manualmente a:
       https://www.sicoes.gob.bo/portal/index.php
     Cerrar el popup de comunicados si aparece.
     Ir al tab "Búsqueda Avanzada" y dejar la página lista.
  4. Correr este script:
       python3 scraper/sicoes_items_cdp.py --max-paginas 2 --anio 2024

DEPENDENCIAS:
  pip install playwright beautifulsoup4 lxml python-dotenv
  playwright install chromium
"""

import asyncio
import re
import json
import argparse
import os
import random
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

CDP_URL = "http://localhost:9222"

ENTIDADES_PRUEBA = [
    {"codigo": "0905-09", "nombre": "Hospital Daniel Bracamonte"},
]

ANIO = 2024
DELAY_PAGINA = (3.0, 6.0)
DELAY_FORM   = (5.0, 12.0)
DELAY_RETRY  = (90.0, 150.0)

# Formularios que queremos procesar (simplificado — solo contratados):
#   ANPE/ANPP → FORM200 (detalle de ítems adjudicados)
#   CM        → FORM220 (detalle de ítems adjudicados)
#   Todos     → FORM500 (recepción/ejecución del contrato)
# Se descartan FORM100 (requerimiento), FORM110 (requeridos CM) y FORM170.
FORMS_ITEMS      = {"FORM200", "FORM220"}
FORMS_RECEPCION  = {"FORM500"}
TODOS_LOS_FORMS  = FORMS_ITEMS | FORMS_RECEPCION

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def _headers(extra: dict = {}) -> dict:
    base = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    base.update(extra)
    return base

def supabase_get(path: str) -> list:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except:
        return []

def supabase_post(tabla: str, rows: list, prefer: str = "resolution=ignore-duplicates,return=minimal") -> dict:
    if not rows:
        return {"count": 0}
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{tabla}",
        data=json.dumps(rows).encode(),
        method="POST",
        headers=_headers({"Prefer": prefer}),
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
            return {"status": r.status, "count": len(rows), "data": json.loads(body) if body else []}
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}

def supabase_patch(tabla: str, filters: str, payload: dict) -> None:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{tabla}?{filters}",
        data=json.dumps(payload).encode(),
        method="PATCH",
        headers=_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except:
        pass

def nombre_proveedor_valido(nombre: str) -> str | None:
    """Normaliza y valida un nombre de proveedor. Devuelve None si no es usable
    (vacío, solo símbolos, o menos de 3 caracteres alfanuméricos)."""
    if not nombre:
        return None
    limpio = limpiar(nombre)
    alfanum = sum(c.isalnum() for c in limpio)
    if alfanum < 3:
        return None
    # Descartar placeholders comunes
    if limpio.lower() in {"n/a", "na", "s/n", "sin nombre", "-", "---", "."}:
        return None
    return limpio

def supabase_upsert_proveedor(nombre: str) -> int | None:
    nombre = nombre_proveedor_valido(nombre)
    if not nombre:
        return None
    res = supabase_post("proveedores", [{"nombre": nombre}],
                        prefer="resolution=merge-duplicates,return=representation")
    if "data" in res and res["data"]:
        return res["data"][0]["id"]
    # Fallback: buscar por nombre
    rows = supabase_get(f"proveedores?nombre=eq.{urllib.parse.quote(nombre)}&select=id&limit=1")
    return rows[0]["id"] if rows else None

def supabase_guardar_html_crudo(cuce: str, tipo_formulario: str, token: str, html: str) -> bool:
    """Guarda el HTML crudo de un formulario en formularios_descargados.
    Una fila por (cuce, tipo_formulario) — upsert. Permite reprocesar/parsear
    después con IA sin volver a SICOES. Se llama ANTES de parsear, así el HTML
    queda guardado aunque el parser falle."""
    row = {
        "cuce": cuce,
        "tipo_formulario": tipo_formulario,
        "token": token,
        "html_crudo": html,
        "longitud_html": len(html) if html else 0,
        "descargado": True,
        "fecha_descarga": datetime.now(timezone.utc).isoformat(),
    }
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/formularios_descargados?on_conflict=cuce,tipo_formulario",
        data=json.dumps([row]).encode(),
        method="POST",
        headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
    )
    try:
        with urllib.request.urlopen(req, timeout=20):
            return True
    except urllib.error.HTTPError as e:
        print(f"        ⚠ html crudo no guardado: {e.read().decode()[:120]}")
        return False
    except Exception as e:
        print(f"        ⚠ html crudo no guardado: {e}")
        return False

def supabase_forms_procesados(cuce: str) -> set:
    rows = supabase_get(f"procesos?cuce=eq.{urllib.parse.quote(cuce)}&select=forms_procesados&limit=1")
    if rows and rows[0].get("forms_procesados"):
        return set(rows[0]["forms_procesados"])
    return set()

def supabase_marcar_form(cuce: str, form_name: str) -> None:
    """Agrega form_name al array forms_procesados del proceso."""
    # Usar RPC array append para evitar race conditions
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/append_form_procesado",
        data=json.dumps({"p_cuce": cuce, "p_form": form_name}).encode(),
        method="POST",
        headers=_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except:
        # Fallback: leer, agregar, escribir
        forms = list(supabase_forms_procesados(cuce))
        if form_name not in forms:
            forms.append(form_name)
            supabase_patch("procesos", f"cuce=eq.{urllib.parse.quote(cuce)}",
                          {"forms_procesados": forms, "items_procesados": True})

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def limpiar(texto) -> str:
    return re.sub(r'\s+', ' ', str(texto).strip()) if texto else ""

def codigo_unspsc_valido(codigo: str) -> str | None:
    if not codigo or len(codigo) != 8 or all(c == '0' for c in codigo):
        return None
    return codigo

def parse_numero(texto) -> float | None:
    if not texto:
        return None
    texto = re.sub(r'[^\d.]', '', str(texto).replace(',', '.'))
    partes = texto.split('.')
    if len(partes) > 2:
        texto = ''.join(partes[:-1]) + '.' + partes[-1]
    try:
        v = float(texto)
        return v if v > 0 else None
    except:
        return None

def parse_fecha(texto) -> str | None:
    """Convierte 'dd/mm/yyyy' a 'yyyy-mm-dd' para Postgres."""
    if not texto:
        return None
    texto = limpiar(texto)
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', texto)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    return None

def parsear_descripcion(celda_html: str) -> tuple[str, str]:
    soup = BeautifulSoup(celda_html, "lxml")
    bold = soup.find("b")
    categoria = limpiar(bold.get_text()) if bold else ""
    texto_completo = limpiar(soup.get_text(separator=" "))
    descripcion = texto_completo.replace(categoria, "").strip()
    return categoria, descripcion

def armar_descripcion(categoria: str, descripcion: str) -> str:
    if categoria and descripcion:
        return f"{categoria} — {descripcion}"
    return categoria or descripcion or ""

# ─── PARSERS ──────────────────────────────────────────────────────────────────

def extraer_contratos_form200(soup: BeautifulSoup) -> dict:
    """Devuelve {nro_contrato: nombre_proveedor} desde la tabla de sección 3 de FORM200."""
    contratos = {}
    tabla_moneda = soup.find("table", id="tablaMoneda")
    if not tabla_moneda:
        return contratos
    tabla = tabla_moneda.find_next_sibling("table")
    if not tabla:
        return contratos
    for fila in tabla.find_all("tr"):
        celdas = fila.find_all("td")
        if len(celdas) < 5:
            continue
        if not limpiar(celdas[0].get_text()).isdigit():
            continue
        nombre = limpiar(celdas[1].get_text())
        nro_doc = limpiar(celdas[4].get_text())
        if nro_doc and nombre:
            contratos[nro_doc] = nombre
    return contratos

def parsear_form200_100(html: str, cuce: str, form_name: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    es_200 = form_name == "FORM200"
    contratos_200 = extraer_contratos_form200(soup) if es_200 else {}

    for tabla in soup.find_all("table"):
        if "DETALLE DE BIENES" not in tabla.get_text().upper():
            continue
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all("td")
            if len(celdas) < 5:
                continue
            nro_text = limpiar(celdas[0].get_text())
            if not nro_text.isdigit():
                continue
            codigo = limpiar(celdas[1].get_text()).zfill(8)
            if es_200:
                if len(celdas) < 10:
                    continue
                # [0]=Nro [1]=Código [2]=Partida [3]=Descripción [4]=Nro.Contrato
                # [5]=Unidad [6]=P.Unit [7]=TipoQty [8]=Cantidad [9]=Monto [10]=Origen
                cat, desc = parsear_descripcion(str(celdas[3]))
                nro_contrato = limpiar(celdas[4].get_text())
                proveedor = contratos_200.get(nro_contrato)
                val5 = limpiar(celdas[5].get_text()) if len(celdas) > 5 else ""
                # Detectar layout CNC: celdas[5] contiene nombre del proveedor (no numérico ni unidad corta)
                # Layout estándar: [5]=Unidad [6]=P.Unit [7]=TipoQty [8]=Cantidad [9]=Monto
                # Layout CNC:      [5]=Proveedor [6]=P.Unit [7]=Unidad [8]=Cantidad [9]=Monto
                es_layout_cnc = (parse_numero(val5) is None and len(val5) > 6
                                 and any(c.isalpha() for c in val5))
                if es_layout_cnc:
                    unidad_val = limpiar(celdas[7].get_text()) if len(celdas) > 7 else ""
                    # Si la unidad tampoco parece una unidad (es numérica), dejarla vacía
                    if parse_numero(unidad_val) is not None:
                        unidad_val = ""
                    if not proveedor:
                        proveedor = val5  # usar celdas[5] como proveedor si no se extrajo antes
                else:
                    unidad_val = val5
                item = {
                    "cuce": cuce,
                    "nro_item": int(nro_text),
                    "unspsc_codigo": codigo_unspsc_valido(codigo),
                    "descripcion_producto": armar_descripcion(cat, desc),
                    "unidad_medida": unidad_val,
                    "precio_adjudicado": parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None,
                    "cantidad": parse_numero(celdas[8].get_text()) if len(celdas) > 8 else None,
                    "monto_total": parse_numero(celdas[9].get_text()) if len(celdas) > 9 else None,
                    "origen": limpiar(celdas[10].get_text()) if len(celdas) > 10 else None,
                    "nro_contrato": nro_contrato or None,
                    "estado_item": "adjudicado",
                    "fuente_formulario": form_name,
                }
                if proveedor:
                    item["_proveedor_nombre"] = proveedor
                items.append(item)
            else:
                # FORM100 desierto: [0]=Nro [1]=Código [2]=Obj.Gasto [3]=Descripción
                #                   [4]=Unidad [5]=Cantidad [6]=P.Ref [7]=Monto
                if len(celdas) < 6:
                    continue
                cat, desc = parsear_descripcion(str(celdas[3]))
                items.append({
                    "cuce": cuce,
                    "nro_item": int(nro_text),
                    "unspsc_codigo": codigo_unspsc_valido(codigo),
                    "descripcion_producto": armar_descripcion(cat, desc),
                    "unidad_medida": limpiar(celdas[4].get_text()) if len(celdas) > 4 else "",
                    "cantidad": parse_numero(celdas[5].get_text()) if len(celdas) > 5 else None,
                    "precio_referencial": parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None,
                    "monto_total": parse_numero(celdas[7].get_text()) if len(celdas) > 7 else None,
                    "estado_item": "desierto",
                    "fuente_formulario": form_name,
                })
        break
    return items

def parsear_form220_110(html: str, cuce: str, form_name: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    es_220 = form_name == "FORM220"

    for tabla in soup.find_all("table"):
        texto = tabla.get_text().upper()
        es_contratados  = "CONTRATADOS" in texto and "NO CONTRATADOS" not in texto and "REQUERIDOS" not in texto
        es_no_cont      = "NO CONTRATADOS" in texto
        es_requeridos   = "REQUERIDOS" in texto
        if not (es_contratados or es_no_cont or es_requeridos):
            continue

        estado_item = "adjudicado" if es_contratados else "requerido" if es_requeridos else "desierto"

        # FORM110 requeridos:
        #   [0]=# [1]=Código [2]=Obj.Gasto [3]=Descripción [4]=Unidad [5]=Cantidad [6]=P.Unit [7]=P.Total
        # FORM220 contratados/no-contratados:
        #   [0]=Nro [1]=Código [2]=Partida [3]=Descripción [4]=Unidad [5]=P.Presel [6]=Proveedor ...
        # Ambos tienen desc en [3] y unidad en [4] — la diferencia es lo que viene después
        desc_idx   = 3
        unidad_idx = 4

        for fila in tabla.find_all("tr"):
            celdas = fila.find_all("td")
            if len(celdas) < 5:
                continue
            nro_text = limpiar(celdas[0].get_text())
            if not nro_text.isdigit():
                continue
            codigo = limpiar(celdas[1].get_text()).zfill(8)
            cat, desc = parsear_descripcion(str(celdas[desc_idx]))
            row = {
                "cuce": cuce,
                "nro_item": int(nro_text),
                "unspsc_codigo": codigo_unspsc_valido(codigo),
                "descripcion_producto": armar_descripcion(cat, desc),
                "unidad_medida": limpiar(celdas[unidad_idx].get_text()) if len(celdas) > unidad_idx else "",
                "estado_item": estado_item,
                "fuente_formulario": form_name,
            }
            if es_220 and es_contratados and len(celdas) > 9:
                # [5]=P.Presel [6]=Proveedor [7]=P.Adj [8]=Cantidad [9]=Monto
                row["precio_preseleccionado"] = parse_numero(celdas[5].get_text())
                row["precio_referencial"]     = parse_numero(celdas[5].get_text())
                row["_proveedor_nombre"]      = limpiar(celdas[6].get_text())
                row["precio_adjudicado"]      = parse_numero(celdas[7].get_text())
                row["cantidad"]               = parse_numero(celdas[8].get_text())
                row["monto_total"]            = parse_numero(celdas[9].get_text())
            elif es_requeridos:
                # FORM110: [5]=Cantidad [6]=P.Unit.Presel
                row["cantidad"]           = parse_numero(celdas[5].get_text()) if len(celdas) > 5 else None
                row["precio_referencial"] = parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None
            else:
                # FORM220 no contratados: [5]=P.Presel [6]=Cantidad
                row["precio_referencial"] = parse_numero(celdas[5].get_text()) if len(celdas) > 5 else None
                row["cantidad"]           = parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None
            items.append(row)
    return items

def parsear_form170(html: str, cuce: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    # Procesar secciones adjudicados y desiertos por separado para evitar
    # que tablas contenedoras dupliquen filas con el mismo nro_item.
    seen_adj = set()
    seen_des = set()
    for tabla in soup.find_all("table"):
        texto = tabla.get_text().upper()
        # Detectar qué tipo de tabla es por su TÍTULO (primer texto de la tabla),
        # no por contenido completo, para evitar que la tabla padre englobe a ambas.
        header_text = " ".join(tabla.find("tr").get_text().upper().split()) if tabla.find("tr") else ""
        es_adj = "ADJUDICADOS" in header_text
        es_des = "DESIERTOS" in header_text and not es_adj
        # Fallback: si el header no distingue, usar texto completo pero solo si
        # la tabla no contiene otras tablas (no es contenedora).
        if not (es_adj or es_des) and not tabla.find("table"):
            es_adj = "ADJUDICADOS" in texto and "DESIERTOS" not in texto
            es_des = "DESIERTOS" in texto and not es_adj
        if not (es_adj or es_des):
            continue
        estado_item = "adjudicado" if es_adj else "desierto"
        seen = seen_adj if es_adj else seen_des
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all("td")
            if len(celdas) < 5:
                continue
            nro_text = limpiar(celdas[0].get_text())
            if not nro_text.isdigit():
                continue
            nro = int(nro_text)
            if nro in seen:
                continue
            seen.add(nro)
            codigo = limpiar(celdas[1].get_text()).zfill(8)
            cat, desc = parsear_descripcion(str(celdas[3]))
            val4 = limpiar(celdas[4].get_text()) if len(celdas) > 4 else ""
            # Detectar layout por contenido de celdas[4]:
            # - LP/CNC: celdas[4] es precio unitario referencial (numérico)
            #   → [4]=P.Unit.Ref [5]=Unidad [6]=P.Unit.Adj [7]=Qty [8]=Monto [9]=Proveedor
            # - ANPE/CD: celdas[4] es unidad de medida (texto)
            #   → [4]=Unidad [5]=P.Ref [6]=Proveedor [7]=P.Adj [8]=Qty [9]=Monto
            es_layout_lp = parse_numero(val4) is not None
            row = {
                "cuce": cuce,
                "nro_item": nro,
                "unspsc_codigo": codigo_unspsc_valido(codigo),
                "descripcion_producto": armar_descripcion(cat, desc),
                "estado_item": estado_item,
                "fuente_formulario": "FORM170",
            }
            if es_adj and len(celdas) > 9:
                if es_layout_lp:
                    # LP/CNC: precio en [4], unidad en [5], p.adj en [6], qty en [7], monto en [8], proveedor en [9]
                    row["unidad_medida"]      = limpiar(celdas[5].get_text()) if len(celdas) > 5 else ""
                    row["precio_referencial"] = parse_numero(val4)
                    row["precio_adjudicado"]  = parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None
                    row["cantidad"]           = parse_numero(celdas[7].get_text()) if len(celdas) > 7 else None
                    row["monto_total"]        = parse_numero(celdas[8].get_text()) if len(celdas) > 8 else None
                    row["_proveedor_nombre"]  = limpiar(celdas[9].get_text()) if len(celdas) > 9 else None
                else:
                    # ANPE/CD: unidad en [4], p.ref en [5], proveedor en [6], p.adj en [7], qty en [8], monto en [9]
                    row["unidad_medida"]      = val4
                    row["precio_referencial"] = parse_numero(celdas[5].get_text()) if len(celdas) > 5 else None
                    row["precio_adjudicado"]  = parse_numero(celdas[7].get_text()) if len(celdas) > 7 else None
                    row["cantidad"]           = parse_numero(celdas[8].get_text()) if len(celdas) > 8 else None
                    row["monto_total"]        = parse_numero(celdas[9].get_text()) if len(celdas) > 9 else None
                    row["_proveedor_nombre"]  = limpiar(celdas[6].get_text()) if len(celdas) > 6 else None
            else:
                row["unidad_medida"] = "" if es_layout_lp else val4
                row["cantidad"]      = parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None
            items.append(row)
    return items

def parsear_form500(html: str, cuce: str) -> list[dict]:
    """
    FORM500 — Recepción de bienes.
    Sección 3 columnas:
    [0]=# [1]=Nro.contrato [2]=Fecha firma [3]=Proveedor [4]=Descripción
    [5]=Estado recepción [6]=Cant.solicitada [7]=Cant.recepcionada
    [8]=Fecha recep.según contrato [9]=Fecha recep.provisional [10]=Fecha recep.definitiva
    [11]=Monto ejecutado
    """
    soup = BeautifulSoup(html, "lxml")
    recepciones = []
    for tabla in soup.find_all("table"):
        texto = tabla.get_text().upper()
        # Buscar por columnas únicas de sección 3 — más robusto que buscar título con acento
        if "CANTIDAD SOLICITADA" not in texto and "CANTIDAD RECEPCIONADA" not in texto:
            continue
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all("td")
            if len(celdas) < 8:
                continue
            nro_text = limpiar(celdas[0].get_text())
            if not nro_text.isdigit():
                continue
            cat, desc = parsear_descripcion(str(celdas[4]))
            rec = {
                "cuce": cuce,
                "nro_contrato": limpiar(celdas[1].get_text()) or None,
                "fecha_firma_contrato": parse_fecha(celdas[2].get_text()),
                "descripcion_bien": armar_descripcion(cat, desc),
                "estado_recepcion": limpiar(celdas[5].get_text()) or None,
                "cantidad_solicitada": parse_numero(celdas[6].get_text()),
                "cantidad_recepcionada": parse_numero(celdas[7].get_text()),
                "fecha_recepcion_contrato": parse_fecha(celdas[8].get_text()) if len(celdas) > 8 else None,
                "fecha_recepcion_provisional": parse_fecha(celdas[9].get_text()) if len(celdas) > 9 else None,
                "fecha_recepcion_definitiva": parse_fecha(celdas[10].get_text()) if len(celdas) > 10 else None,
                "monto_ejecutado": parse_numero(celdas[11].get_text()) if len(celdas) > 11 else None,
                "fuente_formulario": "FORM500",
            }
            proveedor = limpiar(celdas[3].get_text())
            if proveedor:
                rec["_proveedor_nombre"] = proveedor
            recepciones.append(rec)
        break
    return recepciones

# ─── INSERCIÓN ────────────────────────────────────────────────────────────────

def procesar_e_insertar_items(items_raw: list) -> int:
    if not items_raw:
        return 0
    items_limpios = []
    for item in items_raw:
        row = {k: v for k, v in item.items() if not k.startswith("_")}
        prov = item.get("_proveedor_nombre")
        if prov and prov.strip():
            prov_id = supabase_upsert_proveedor(prov.strip())
            if prov_id:
                row["proveedor_id"] = prov_id
            else:
                print(f"        ⚠ proveedor no insertado: {prov[:40]}")
        items_limpios.append(row)

    # Deduplicar por (cuce, nro_item, fuente_formulario) antes de insertar.
    seen_keys = set()
    deduped = []
    for row in items_limpios:
        key = (row.get("cuce"), row.get("nro_item"), row.get("fuente_formulario"))
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(row)
    items_limpios = deduped

    # Supabase exige que todas las filas del batch tengan exactamente las mismas claves
    # (PGRST102). Unificar con None para las claves que faltan en algunas filas.
    todas_claves = set().union(*[r.keys() for r in items_limpios])
    items_limpios = [{k: r.get(k, None) for k in todas_claves} for r in items_limpios]

    result = supabase_post("items", items_limpios)
    if "error" in result:
        print(f"        ✗ insert error: {result['error'][:120]}")
        return 0
    return result.get("count", 0)

def procesar_e_insertar_recepciones(recs_raw: list) -> int:
    if not recs_raw:
        return 0
    recs_limpias = []
    for rec in recs_raw:
        row = {k: v for k, v in rec.items() if not k.startswith("_")}
        prov = rec.get("_proveedor_nombre")
        if prov and prov.strip():
            prov_id = supabase_upsert_proveedor(prov.strip())
            if prov_id:
                row["proveedor_id"] = prov_id
        recs_limpias.append(row)
    todas_claves = set().union(*[r.keys() for r in recs_limpias])
    recs_limpias = [{k: r.get(k, None) for k in todas_claves} for r in recs_limpias]

    result = supabase_post("recepciones", recs_limpias)
    if "error" in result:
        print(f"        ✗ recepcion insert error: {result['error'][:120]}")
        return 0
    return result.get("count", 0)

# ─── NAVEGACIÓN ───────────────────────────────────────────────────────────────

async def ir_a_buscador(page):
    await page.evaluate("""
        () => {
            document.querySelectorAll("button.close[data-dismiss='modal']").forEach(b => b.click());
            document.querySelectorAll(".modal").forEach(m => {
                m.style.display = 'none'; m.classList.remove('show','in');
            });
            document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
            if (window.$) window.$.fn.modal = function() { return this; };
        }
    """)
    await page.wait_for_timeout(500)
    await page.evaluate("irLink('/portal/contrataciones/busqueda/convocatorias.php?tipo=convNacional')")
    await page.wait_for_timeout(2500)
    await page.evaluate("document.querySelector('a[href=\"#f-avanzada\"]').click()")
    await page.wait_for_timeout(800)

async def buscar(page, cuce2, cuce3, anio, estado_val="2C"):
    await page.evaluate("""
        () => {
            var tab = document.querySelector('a[href="#f-avanzada"]');
            if (tab) tab.click();
            document.querySelectorAll('#f-avanzada input[type="text"], #f-avanzada input[type="number"]')
                .forEach(el => el.value = '');
            ['codigoModalidad','r1','codigoContrato','codigoDpto','codigoNormativa']
                .forEach(n => { var el = document.getElementById(n); if (el) el.value = ''; });
        }
    """)
    await page.wait_for_timeout(300)
    await page.evaluate("""
        (args) => {
            var tab = document.querySelector('#f-avanzada') || document;
            var f = sel => tab.querySelectorAll(sel);
            var c1 = f('[name="cuce1"]'); if (c1[0]) c1[0].value = args.anio;
            var c2 = f('[name="cuce2"]'); if (c2[0]) c2[0].value = args.cuce2;
            var c3 = f('[name="cuce3"]'); if (c3[0]) c3[0].value = args.cuce3;
            var ct = document.getElementById('codigoContrato'); if (ct) ct.value = 'B';
            var est = document.getElementById('r1'); if (est) est.value = args.estado_val;
        }
    """, {"anio": str(anio)[2:], "cuce2": cuce2, "cuce3": cuce3, "estado_val": estado_val})
    await page.wait_for_timeout(400)
    await page.evaluate("""
        () => {
            for (var b of document.querySelectorAll('.btn-primary, button[type="submit"]')) {
                if (b.offsetParent !== null && b.textContent.includes('Buscar')) { b.click(); return; }
            }
        }
    """)
    try:
        await page.wait_for_selector("table tbody tr td", timeout=12000)
        await page.wait_for_timeout(800)
    except:
        await page.wait_for_timeout(4000)

async def ir_pagina(page, n):
    await page.evaluate(f"busquedadraw('{n}')")
    await page.wait_for_timeout(1000)
    try:
        await page.wait_for_selector("table tbody tr td", timeout=8000)
        await page.wait_for_timeout(300)
    except:
        await page.wait_for_timeout(2000)

async def descargar_archivo_cualquiera(page) -> bool:
    """Dispara una descarga REAL de un documento desde la página de resultados.
    Este request de archivo es lo que reactiva la sesión de SICOES (descubierto
    empíricamente: abrir el modal del formulario no alcanza — hay que bajar un
    archivo para que el servidor renueve el token).

    En SICOES la columna 'Archivos' tiene links:
        <a onclick="descargarArchivo('TOKEN')">Convocatoria</a>
    Llamamos a la función JS directamente con el primer token disponible."""
    token = await page.evaluate(r"""
        () => {
            const a = document.querySelector('a[onclick*="descargarArchivo"]');
            if (!a) return null;
            const m = (a.getAttribute('onclick') || '').match(/descargarArchivo\('([^']+)'\)/);
            return m ? m[1] : null;
        }
    """)
    if not token:
        print("        ⚠ No se encontró archivo descargable (sin descargarArchivo en la página)")
        return False

    print("        ⬇ Descargando archivo (keep-alive)...", end=" ", flush=True)
    paginas_antes = set(page.context.pages)
    try:
        async with page.expect_download(timeout=20000) as di:
            await page.evaluate(f"descargarArchivo('{token}')")
        download = await di.value
        ruta = f"/tmp/sicoes_keepalive_{download.suggested_filename or 'archivo'}"
        await download.save_as(ruta)
        print(f"OK ({download.suggested_filename})")
        ok = True
    except Exception:
        # No disparó evento de descarga (quizá abrió pestaña o respondió inline).
        # El request al servidor igual se hizo → la sesión queda renovada.
        print("request enviado (sin evento download)")
        ok = True
    finally:
        # Cerrar cualquier pestaña nueva que se haya abierto (visor de PDF, etc.)
        for p_extra in list(page.context.pages):
            if p_extra is not page and p_extra not in paginas_antes:
                try:
                    await p_extra.close()
                except Exception:
                    pass
    return ok

async def activar_sesion_con_formulario(page) -> bool:
    """Fallback: abre y cierra el primer formulario visible para renovar el token.
    Se usa solo si no se encontró ningún archivo descargable."""
    try:
        primer_token = await page.evaluate(r"""
            () => {
                const links = document.querySelectorAll('a[onclick*="verFormulario"]');
                if (!links.length) return null;
                const m = (links[0].getAttribute('onclick') || '').match(/verFormulario\('([^']+)'\)/);
                return m ? m[1] : null;
            }
        """)
        if not primer_token:
            return False
        print("        🔑 Activando sesión con formulario (fallback)...", end=" ", flush=True)
        await page.evaluate(f"verFormulario('{primer_token}')")
        await page.wait_for_timeout(4000)
        await page.evaluate("""
            () => {
                document.querySelectorAll('.modal').forEach(m => {
                    m.style.display='none'; m.classList.remove('show','in');
                });
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
            }
        """)
        await page.wait_for_timeout(1500)
        print("OK")
        return True
    except Exception as e:
        print(f"fallo ({e})")
        return False

async def _cerrar_modales(page):
    await page.evaluate("""
        () => {
            document.querySelectorAll('.modal').forEach(m => {
                m.style.display='none'; m.classList.remove('show','in');
            });
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
        }
    """)

async def recuperar_sesion(page, cuce2, cuce3, anio, estado_val, pag) -> bool:
    """Recupera la sesión de SICOES. Estrategia en dos niveles:

    NIVEL 1 (preferido — no pierde el filtro):
      La página de resultados sigue cargada con la entidad correcta. Solo
      cerramos el modal trabado, esperamos 90s y descargamos un archivo de
      la página actual para renovar el token. Reintentamos la MISMA página.

    NIVEL 2 (fallback, solo si la página actual ya no tiene resultados):
      reload → cerrar popup → convocatorias → re-filtrar → descargar archivo
      → volver a la página `pag`. Verifica que los resultados sean de la
      entidad correcta antes de dar éxito.

    Devuelve True si logró renovar la sesión sobre la página correcta."""
    print(f"\n    ♻️  Posible sesión expirada — esperando 90s...", flush=True)
    await asyncio.sleep(90)

    # ── NIVEL 1: descargar desde la página actual (sin re-navegar) ──────────
    try:
        await _cerrar_modales(page)
        await page.wait_for_timeout(1000)
        hay_archivos = await page.query_selector('a[onclick*="descargarArchivo"]')
        primera_celda = await page.evaluate(
            "() => { const td = document.querySelector('#tablaAvanzada tbody tr td'); return td ? td.innerText.trim() : ''; }"
        )
        # La página actual sirve si todavía muestra resultados de la entidad.
        # El código de entidad (CUCE2-CUCE3) aparece dentro del CUCE: aa-CUCE2-CUCE3-...
        ent_codigo = f"{cuce2}-{cuce3}"
        en_entidad = bool(primera_celda) and ent_codigo in primera_celda
        if hay_archivos and en_entidad:
            print(f"    ♻️  Recuperando en la página actual (pág {pag}, {primera_celda[:24]})...", flush=True)
            if await descargar_archivo_cualquiera(page):
                await page.wait_for_timeout(2000)
                print("    ✓ Sesión recuperada (sin re-navegar)\n", flush=True)
                return True
    except Exception as e:
        print(f"    · nivel 1 no aplicable ({e})", flush=True)

    # ── NIVEL 2: reload completo + re-filtrar + volver a la página ──────────
    print(f"    ♻️  Recuperación completa (reload + re-filtrar, objetivo pág {pag})...", flush=True)
    try:
        try:
            await page.reload(wait_until="domcontentloaded", timeout=60000)
        except Exception:
            await page.goto("https://www.sicoes.gob.bo/portal/index.php",
                            wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2500)

        await ir_a_buscador(page)
        await buscar(page, cuce2, cuce3, anio, estado_val)
        await page.evaluate("busquedadraw('1')")
        await page.wait_for_timeout(2500)
        # Selector específico de la tabla de resultados (no cualquier tabla)
        await page.wait_for_selector("#tablaAvanzada tbody tr td", timeout=15000)
        await page.wait_for_timeout(800)

        # Verificar que el filtro se aplicó (primer CUCE de la entidad correcta)
        primera_celda = await page.evaluate(
            "() => { const td = document.querySelector('#tablaAvanzada tbody tr td'); return td ? td.innerText.trim() : ''; }"
        )
        ent_codigo = f"{cuce2}-{cuce3}"
        if ent_codigo not in (primera_celda or ""):
            print(f"    ✗ El filtro no se aplicó (primer resultado: {primera_celda[:24]}) — reintentando búsqueda", flush=True)
            await buscar(page, cuce2, cuce3, anio, estado_val)
            await page.evaluate("busquedadraw('1')")
            await page.wait_for_timeout(2500)
            await page.wait_for_selector("#tablaAvanzada tbody tr td", timeout=15000)

        # Descargar archivo para renovar token
        if not await descargar_archivo_cualquiera(page):
            await activar_sesion_con_formulario(page)
        await page.wait_for_timeout(1500)

        # Volver a la página donde estábamos
        if pag > 1:
            await ir_pagina(page, pag)
        await page.wait_for_selector("#tablaAvanzada tbody tr td", timeout=15000)
        await page.wait_for_timeout(1000)
        print("    ✓ Sesión recuperada (recuperación completa)\n", flush=True)
        return True
    except Exception as e:
        print(f"    ✗ No se pudo recuperar sesión: {e}\n", flush=True)
        return False

async def detectar_total_paginas(page) -> int:
    """Lee el paginador de SICOES y devuelve el número real de páginas."""
    try:
        max_pag = await page.evaluate(r"""
            () => {
                let max = 1;
                document.querySelectorAll('[onclick*="busquedadraw"]').forEach(el => {
                    const m = (el.getAttribute('onclick') || '').match(/busquedadraw\('(\d+)'\)/);
                    if (m) max = Math.max(max, parseInt(m[1]));
                });
                return max;
            }
        """)
        return int(max_pag)
    except:
        return 1

# ─── EXTRACCIÓN DE TOKENS ─────────────────────────────────────────────────────

def extraer_tokens(td_html: str) -> dict:
    tokens = {}
    for token, label in re.findall(r"verFormulario\('([^']+)'\)[^>]*>([^<]+)</a>", td_html):
        key = label.strip().replace(" ", "").upper()
        tokens[key] = token
    return tokens

async def extraer_filas(page, ent_codigo: str) -> list[dict]:
    filas_data = []
    try:
        filas = await page.query_selector_all("table tbody tr")
        for fila in filas:
            celdas = await fila.query_selector_all("td")
            if len(celdas) < 9:
                continue
            cuce = limpiar(await celdas[0].inner_text())
            if not cuce or len(cuce) < 5:
                continue
            partes = cuce.split("-")
            if len(partes) >= 3 and f"{partes[1]}-{partes[2]}" != ent_codigo:
                continue
            modalidad = limpiar(await celdas[3].inner_text())
            estado = limpiar(await celdas[8].inner_text())
            if not any(s in estado.lower() for s in ["contratado", "desierto", "adjudicado"]):
                continue
            tokens = {}
            for i in range(9, min(len(celdas), 12)):
                html_celda = await celdas[i].inner_html()
                if "verFormulario" in html_celda:
                    tokens = extraer_tokens(html_celda)
                    break
            if not tokens:
                continue
            print(f"      {cuce}: {list(tokens.keys())} [{estado}]")
            filas_data.append({"cuce": cuce, "modalidad": modalidad, "estado": estado, "tokens": tokens})
    except Exception as e:
        print(f"    Error extrayendo filas: {e}")
    return filas_data

# ─── ABRIR FORMULARIO ─────────────────────────────────────────────────────────

async def _abrir_form_intento(page, token: str, timeout_ms: int) -> str:
    """Un intento de abrir el formulario. Devuelve el HTML interno o '' si no cargó."""
    # Limpiar cualquier modal previo antes de abrir (evita interferencia entre forms)
    await _cerrar_modales(page)
    await page.wait_for_timeout(500)

    await page.evaluate(f"verFormulario('{token}')")
    try:
        await page.wait_for_selector("#visualizarformulario0 table", timeout=timeout_ms)
        await page.wait_for_timeout(400)
    except Exception:
        return ""
    html = await page.evaluate("""
        () => { var el = document.getElementById('visualizarformulario0'); return el ? el.innerHTML : ''; }
    """)
    return html or ""

async def abrir_formulario(page, token: str, form_name: str, cuce: str) -> tuple[list, list]:
    """Devuelve (items, recepciones).
    Reintenta una vez si el formulario no carga a tiempo — muchos 'sin contenido'
    son falsos negativos (el form tarda más en cargar de lo esperado)."""
    print(f"        {form_name}...", end=" ", flush=True)

    # Intento 1 (25s). Si falla, cerrar, esperar y reintentar con más tiempo (30s).
    html = await _abrir_form_intento(page, token, 25000)
    if not html or len(html) < 100:
        await _cerrar_modales(page)
        await page.wait_for_timeout(random.uniform(2.0, 4.0) * 1000)
        print("reintentando...", end=" ", flush=True)
        html = await _abrir_form_intento(page, token, 30000)

    if not html or len(html) < 100:
        print("sin contenido (tras reintento)")
        await _cerrar_modales(page)
        return [], []

    # Guardar el HTML crudo SIEMPRE antes de parsear — así queda disponible para
    # reprocesar con IA aunque el parser tenga un bug o cambie el layout.
    supabase_guardar_html_crudo(cuce, form_name, token, html)

    items, recepciones = [], []
    try:
        if form_name in ("FORM200", "FORM100"):
            items = parsear_form200_100(html, cuce, form_name)
        elif form_name in ("FORM220", "FORM110"):
            items = parsear_form220_110(html, cuce, form_name)
        elif form_name == "FORM170":
            items = parsear_form170(html, cuce)
        elif form_name == "FORM500":
            recepciones = parsear_form500(html, cuce)
    except Exception as e:
        print(f"(parse falló: {e}) ", end="")

    # Pausa antes de cerrar — simula lectura humana, reduce detección
    await asyncio.sleep(random.uniform(2.5, 5.0))

    # Cerrar modal
    await page.evaluate("""
        () => {
            var btn = document.querySelector('#modalFormulario .close, .modal.in .close');
            if (btn) btn.click();
            else {
                document.querySelectorAll('.modal').forEach(m => {
                    m.style.display='none'; m.classList.remove('show','in');
                });
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
            }
        }
    """)
    await page.wait_for_timeout(random.randint(800, 1800))

    if form_name == "FORM500":
        print(f"{len(recepciones)} recepciones")
    else:
        print(f"{len(items)} ítems")

    return items, recepciones

# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def scraping(entidades: list, anio: int, max_paginas: int):
    total_items = 0
    total_recepciones = 0
    total_procesos = 0

    async with async_playwright() as p:
        print(f"Conectando a Chrome en {CDP_URL}...")
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"\n❌ No se pudo conectar: {e}")
            print("\nAsegurate de que Chrome esté abierto con:")
            print('  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
            print('    --remote-debugging-port=9222 \\')
            print('    --user-data-dir="/tmp/brave-sicoes"')
            return

        print("✓ Conectado")
        contexts = browser.contexts
        if not contexts:
            print("❌ Chrome no tiene contexto activo.")
            return

        context = contexts[0]
        page = None
        for p_tab in context.pages:
            if "sicoes" in p_tab.url:
                page = p_tab
                print(f"✓ Usando pestaña: {p_tab.url[:60]}")
                break
        if not page:
            page = await context.new_page()
            await page.goto("https://www.sicoes.gob.bo/portal/index.php",
                           wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

        print("Navegando al buscador...")
        await ir_a_buscador(page)
        cap_str = f"cap {max_paginas} págs" if max_paginas else "sin límite"
        print(f"✓ Buscador listo | Entidades: {len(entidades)} | Año: {anio} | {cap_str}")
        print("=" * 60)

        for ent in entidades:
            cuce2, cuce3 = ent["codigo"].split("-")
            print(f"\n[{ent['codigo']}] {ent['nombre']}")

            for estado_label, estado_val in [("Contratados", "2C")]:
                print(f"  → {estado_label}")
                await buscar(page, cuce2, cuce3, anio, estado_val)
                await page.evaluate("busquedadraw('1')")
                await page.wait_for_timeout(1000)
                try:
                    await page.wait_for_selector("table tbody tr td", timeout=10000)
                    await page.wait_for_timeout(600)
                except:
                    await page.wait_for_timeout(3000)

                paginas_reales = await detectar_total_paginas(page)
                paginas_a_recorrer = min(paginas_reales, max_paginas) if max_paginas else paginas_reales
                print(f"    → {paginas_reales} página(s) detectada(s)", end="")
                if max_paginas and paginas_reales > max_paginas:
                    print(f" (cap: {max_paginas})", end="")
                print()

                paginas_vacias = 0
                pag = 1
                recuperaciones_pag = 0   # intentos de recuperación en la pág actual

                while pag <= paginas_a_recorrer:
                    print(f"    Página {pag}/{paginas_a_recorrer}...", end=" ", flush=True)
                    filas = await extraer_filas(page, ent["codigo"])
                    print(f"{len(filas)} procesos con tokens")

                    if not filas:
                        paginas_vacias += 1
                        if paginas_vacias >= 2:
                            print("    → 2 páginas vacías seguidas, saliendo")
                            break
                    else:
                        paginas_vacias = 0

                    items_pagina = 0
                    recs_pagina  = 0
                    vacios_consecutivos = 0
                    exitos_pagina = 0          # forms con contenido en esta página
                    repetir_pagina = False     # se setea si recuperamos sesión

                    for fila in filas:
                        cuce = fila["cuce"]
                        tokens = fila["tokens"]
                        forms_ya_hechos = supabase_forms_procesados(cuce)

                        # Determinar qué forms de esta fila todavía no procesamos
                        forms_disponibles = set(tokens.keys()) & TODOS_LOS_FORMS
                        forms_pendientes  = forms_disponibles - forms_ya_hechos

                        if not forms_pendientes:
                            print(f"        ↩ {cuce}: todos los forms ya procesados {sorted(forms_ya_hechos)}")
                            continue

                        print(f"        {cuce}: pendientes={sorted(forms_pendientes)} ya={sorted(forms_ya_hechos)}")

                        for form_name in sorted(forms_pendientes):
                            token = tokens[form_name]
                            items, recepciones = await abrir_formulario(page, token, form_name, cuce)

                            if items:
                                vacios_consecutivos = 0
                                exitos_pagina += 1
                                insertados = procesar_e_insertar_items(items)
                                items_pagina += insertados
                                total_items  += insertados
                                supabase_marcar_form(cuce, form_name)
                            elif recepciones:
                                vacios_consecutivos = 0
                                exitos_pagina += 1
                                insertados = procesar_e_insertar_recepciones(recepciones)
                                recs_pagina       += insertados
                                total_recepciones += insertados
                                supabase_marcar_form(cuce, form_name)
                            else:
                                # Vacío. Solo lo marcamos como procesado si la sesión
                                # está viva (ya hubo éxitos en esta página) o si ya
                                # intentamos recuperar la sesión sin éxito (vacío real).
                                vacios_consecutivos += 1
                                sesion_viva = exitos_pagina > 0 or recuperaciones_pag >= 2
                                if sesion_viva and vacios_consecutivos < 3:
                                    supabase_marcar_form(cuce, form_name)
                                elif vacios_consecutivos >= 3:
                                    if recuperaciones_pag >= 2:
                                        # Ya recuperamos 2 veces y sigue vacío:
                                        # son formularios genuinamente vacíos → marcar.
                                        print(f"        ⚠️ {cuce}: vacío persistente, marcando")
                                        supabase_marcar_form(cuce, form_name)
                                        vacios_consecutivos = 0
                                    else:
                                        # Probable sesión muerta → recuperar y repetir
                                        ok = await recuperar_sesion(
                                            page, cuce2, cuce3, anio, estado_val, pag)
                                        recuperaciones_pag += 1
                                        if ok:
                                            repetir_pagina = True
                                        else:
                                            pausa = random.uniform(*DELAY_RETRY)
                                            print(f"        ⏸ pausa {pausa:.0f}s...")
                                            await asyncio.sleep(pausa)
                                        vacios_consecutivos = 0
                                        break

                            await asyncio.sleep(random.uniform(*DELAY_FORM))

                        if repetir_pagina:
                            break
                        total_procesos += 1

                    if repetir_pagina:
                        # No avanzamos: re-extraemos la página con tokens frescos
                        print(f"    ↻ Repitiendo página {pag} tras recuperar sesión")
                        await asyncio.sleep(random.uniform(*DELAY_PAGINA))
                        continue

                    print(f"    → {items_pagina} ítems + {recs_pagina} recepciones en pág {pag}")
                    pag += 1
                    recuperaciones_pag = 0
                    if pag <= paginas_a_recorrer:
                        await ir_pagina(page, pag)
                        await asyncio.sleep(random.uniform(*DELAY_PAGINA))

        print(f"\n{'='*60}")
        print(f"COMPLETADO — Procesos: {total_procesos} | Ítems: {total_items} | Recepciones: {total_recepciones}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SICOES Items Scraper v2 (CDP)")
    parser.add_argument("--max-paginas", type=int, default=0,
                        help="Cap de páginas por estado/entidad (default: 0 = sin límite, usa paginador real)")
    parser.add_argument("--anio", type=int, default=2024,
                        help="Año CUCE a scrapear (default: 2024)")
    args = parser.parse_args()

    cap = f"cap {args.max_paginas} págs" if args.max_paginas else "sin límite de páginas"
    print(f"SICOES Items Scraper v2 — año {args.anio} | {cap}")
    asyncio.run(scraping(ENTIDADES_PRUEBA, args.anio, args.max_paginas))
