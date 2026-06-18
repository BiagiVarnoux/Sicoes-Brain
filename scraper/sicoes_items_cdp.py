"""
SICOES Items Scraper — CDP Edition
====================================
Conecta a un Chrome ya abierto por el usuario (via CDP) para evitar
que Cloudflare Turnstile detecte automatización. El Turnstile invisible
de verFormulario() se resuelve solo en un browser real.

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
       python3 scraper/sicoes_items_cdp.py --max-paginas 2

DEPENDENCIAS:
  pip install playwright beautifulsoup4 lxml
  playwright install chromium  (solo si no está instalado)
"""

import asyncio
import re
import json
import argparse
import os
import urllib.request
import urllib.error
import urllib.parse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
# Crea un archivo .env en el mismo directorio con:
#   SUPABASE_URL=https://....supabase.co
#   SUPABASE_KEY=sb_secret_...

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv opcional — también funciona con variables de entorno del sistema

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

CDP_URL = "http://localhost:9222"

# Entidades de prueba — para el completo reemplazar con la lista de 82
ENTIDADES_PRUEBA = [
    {"codigo": "0905-09", "nombre": "Hospital Daniel Bracamonte"},
]

ANIO = 2026
DELAY = 2.0          # entre páginas
DELAY_FORM = 3.0     # entre formularios (evita rate limit de SICOES)
DELAY_RETRY = 90.0   # pausa si hay 3 "sin contenido" seguidos

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def supabase_insert(tabla: str, rows: list) -> dict:
    if not rows:
        return {"count": 0}
    url = f"{SUPABASE_URL}/rest/v1/{tabla}"
    data = json.dumps(rows).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": resp.status, "count": len(rows)}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": body}

def supabase_upsert_proveedor(nombre: str) -> int | None:
    url = f"{SUPABASE_URL}/rest/v1/proveedores"
    payload = json.dumps([{"nombre": nombre}]).encode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data[0]["id"] if data else None
    except urllib.error.HTTPError as e:
        # Si ya existe (409 o similar), buscar por nombre
        pass
    params = f"?nombre=eq.{urllib.parse.quote(nombre)}&select=id&limit=1"
    req2 = urllib.request.Request(
        url + params,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
    )
    try:
        with urllib.request.urlopen(req2, timeout=10) as resp:
            data = json.loads(resp.read())
            return data[0]["id"] if data else None
    except:
        return None

def supabase_ya_procesado(cuce: str) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/procesos?cuce=eq.{urllib.parse.quote(cuce)}&select=items_procesados&limit=1"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            return bool(data and data[0].get("items_procesados"))
    except:
        return False

def supabase_marcar_procesado(cuce: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/procesos?cuce=eq.{urllib.parse.quote(cuce)}"
    payload = json.dumps({"items_procesados": True}).encode()
    req = urllib.request.Request(
        url, data=payload, method="PATCH",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except:
        pass

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def limpiar(texto) -> str:
    return re.sub(r'\s+', ' ', str(texto).strip()) if texto else ""

def codigo_unspsc_valido(codigo: str) -> str | None:
    # Rechaza vacíos, todo-ceros, y longitud incorrecta
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
        return float(texto)
    except:
        return None

def parsear_descripcion(celda_html: str) -> tuple[str, str]:
    soup = BeautifulSoup(celda_html, "lxml")
    bold = soup.find("b")
    categoria = limpiar(bold.get_text()) if bold else ""
    texto_completo = limpiar(soup.get_text(separator=" "))
    descripcion = texto_completo.replace(categoria, "").strip()
    return categoria, descripcion

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

# ─── PARSERS DE FORMULARIOS ───────────────────────────────────────────────────

def parsear_form200_100(html: str, cuce: str, form_name: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    es_200 = form_name == "FORM200"

    # FORM200: build contract→provider map from section 3 table
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
                # FORM200 cols: [0]=Nro [1]=Código [2]=Partida [3]=Descripción
                #               [4]=Nro.Contrato [5]=Unidad [6]=Precio unit
                #               [7]=La cantidad es [8]=Cantidad [9]=Monto [10]=Origen
                if len(celdas) < 10:
                    continue
                cat, desc = parsear_descripcion(str(celdas[3]))
                nro_contrato = limpiar(celdas[4].get_text())
                proveedor = contratos_200.get(nro_contrato)
                item = {
                    "cuce": cuce,
                    "nro_item": int(nro_text),
                    "unspsc_codigo": codigo_unspsc_valido(codigo),
                    "descripcion_producto": f"{cat} — {desc}".strip(" —"),
                    "unidad_medida": limpiar(celdas[5].get_text()) if len(celdas) > 5 else "",
                    "precio_adjudicado": parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None,
                    "cantidad": parse_numero(celdas[8].get_text()) if len(celdas) > 8 else None,
                    "monto_total": parse_numero(celdas[9].get_text()) if len(celdas) > 9 else None,
                    "origen": limpiar(celdas[10].get_text()) if len(celdas) > 10 else None,
                    "estado_item": "adjudicado",
                    "fuente_formulario": form_name,
                }
                if proveedor:
                    item["_proveedor_nombre"] = proveedor
                items.append(item)
            else:
                if len(celdas) < 6:
                    continue
                cat, desc = parsear_descripcion(str(celdas[2]))
                items.append({
                    "cuce": cuce,
                    "nro_item": int(nro_text),
                    "unspsc_codigo": codigo_unspsc_valido(codigo),
                    "descripcion_producto": f"{cat} — {desc}".strip(" —"),
                    "unidad_medida": limpiar(celdas[3].get_text()) if len(celdas) > 3 else "",
                    "cantidad": parse_numero(celdas[4].get_text()) if len(celdas) > 4 else None,
                    "precio_referencial": parse_numero(celdas[5].get_text()) if len(celdas) > 5 else None,
                    "monto_total": parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None,
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
        es_contratados = "CONTRATADOS" in texto and "NO CONTRATADOS" not in texto and "REQUERIDOS" not in texto
        es_no_cont = "NO CONTRATADOS" in texto
        es_requeridos = "REQUERIDOS" in texto  # FORM110: ítems referencia de CM desierto
        if not (es_contratados or es_no_cont or es_requeridos):
            continue

        if es_contratados:
            estado_item = "adjudicado"
        else:
            estado_item = "desierto"

        # FORM110 "REQUERIDOS": no tiene columna Partida
        #   [0]=# [1]=Código [2]=Descripción [3]=Unidad [4]=Cantidad [5]=P.Unit [6]=P.Total
        # FORM220 CONTRATADOS/NO CONTRATADOS: tiene Partida en [2]
        #   [0]=Nro [1]=Código [2]=Partida [3]=Descripción [4]=Unidad [5]=P.Presel [6]=Proveedor/Cantidad
        desc_idx = 2 if es_requeridos else 3
        unidad_idx = 3 if es_requeridos else 4

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
                "descripcion_producto": f"{cat} — {desc}".strip(" —"),
                "unidad_medida": limpiar(celdas[unidad_idx].get_text()) if len(celdas) > unidad_idx else "",
                "precio_referencial": parse_numero(celdas[5].get_text()) if len(celdas) > 5 else None,
                "estado_item": estado_item,
                "fuente_formulario": form_name,
            }
            if es_220 and es_contratados and len(celdas) > 9:
                row["_proveedor_nombre"] = limpiar(celdas[6].get_text())
                row["precio_adjudicado"] = parse_numero(celdas[7].get_text())
                row["cantidad"] = parse_numero(celdas[8].get_text())
                row["monto_total"] = parse_numero(celdas[9].get_text())
            elif es_requeridos:
                row["cantidad"] = parse_numero(celdas[4].get_text()) if len(celdas) > 4 else None
            else:
                row["cantidad"] = parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None
            items.append(row)
    return items

def parsear_form170(html: str, cuce: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for tabla in soup.find_all("table"):
        texto = tabla.get_text().upper()
        es_adj = "ADJUDICADOS" in texto and "DESIERTOS" not in texto
        es_des = "DESIERTOS" in texto
        if not (es_adj or es_des):
            continue
        estado_item = "adjudicado" if es_adj else "desierto"
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all("td")
            if len(celdas) < 5:
                continue
            nro_text = limpiar(celdas[0].get_text())
            if not nro_text.isdigit():
                continue
            codigo = limpiar(celdas[1].get_text()).zfill(8)
            cat, desc = parsear_descripcion(str(celdas[3]))
            row = {
                "cuce": cuce,
                "nro_item": int(nro_text),
                "unspsc_codigo": codigo_unspsc_valido(codigo),
                "descripcion_producto": f"{cat} — {desc}".strip(" —"),
                "unidad_medida": limpiar(celdas[4].get_text()) if len(celdas) > 4 else "",
                "precio_referencial": parse_numero(celdas[5].get_text()) if len(celdas) > 5 else None,
                "estado_item": estado_item,
                "fuente_formulario": "FORM170",
            }
            if es_adj and len(celdas) > 9:
                row["_proveedor_nombre"] = limpiar(celdas[6].get_text())
                row["precio_adjudicado"] = parse_numero(celdas[7].get_text())
                row["cantidad"] = parse_numero(celdas[8].get_text())
                row["monto_total"] = parse_numero(celdas[9].get_text())
            else:
                row["cantidad"] = parse_numero(celdas[6].get_text()) if len(celdas) > 6 else None
            items.append(row)
    return items

def formulario_a_procesar(modalidad: str, estado: str, tokens: dict) -> tuple[str, str] | None:
    es_cm = modalidad == "CM"
    estado_l = estado.lower()
    if "contratado" in estado_l:
        form = "FORM220" if es_cm else "FORM200"
        return (form, tokens[form]) if form in tokens else None
    if "desierto" in estado_l or "anulado desde la convocatoria" in estado_l:
        form = "FORM110" if es_cm else "FORM100"
        if form in tokens:
            return form, tokens[form]
        if "FORM170" in tokens:
            return "FORM170", tokens["FORM170"]
        return None
    if "adjudicado" in estado_l:
        form = "FORM220" if es_cm else "FORM200"
        return (form, tokens[form]) if form in tokens else None
    return None

def procesar_e_insertar(items_raw: list) -> int:
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
    result = supabase_insert("items", items_limpios)
    if "error" in result:
        print(f"        ✗ insert error: {result['error'][:120]}")
        return 0
    count = result.get("count", 0)
    if count > 0 and items_limpios:
        supabase_marcar_procesado(items_limpios[0]["cuce"])
    return count

# ─── NAVEGACIÓN ───────────────────────────────────────────────────────────────

async def ir_a_buscador(page):
    """Navega al buscador avanzado de SICOES."""
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
                print(f"      {cuce}: sin tokens (estado={estado})")
                continue
            print(f"      {cuce}: {list(tokens.keys())} [{estado}]")
            filas_data.append({"cuce": cuce, "modalidad": modalidad, "estado": estado, "tokens": tokens})
    except Exception as e:
        print(f"    Error extrayendo filas: {e}")
    return filas_data

# ─── ABRIR FORMULARIO Y EXTRAER ───────────────────────────────────────────────

async def abrir_formulario(page, token: str, form_name: str, cuce: str) -> list[dict]:
    print(f"        {form_name}...", end=" ", flush=True)

    # Llamar verFormulario — Turnstile invisible se resuelve solo en Chrome real
    await page.evaluate(f"verFormulario('{token}')")

    # Esperar que el modal cargue contenido real (tabla dentro del div)
    try:
        await page.wait_for_selector("#visualizarformulario0 table", timeout=15000)
        await page.wait_for_timeout(300)
    except:
        print("sin contenido")
        # Cerrar modal si quedó abierto
        await page.evaluate("""
            () => {
                document.querySelectorAll('.modal').forEach(m => {
                    m.style.display='none'; m.classList.remove('show','in');
                });
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
            }
        """)
        return []

    html = await page.evaluate("""
        () => { var el = document.getElementById('visualizarformulario0'); return el ? el.innerHTML : ''; }
    """)

    if not html or len(html) < 100:
        print("HTML vacío")
        return []

    items = []
    if form_name in ("FORM200", "FORM100"):
        items = parsear_form200_100(html, cuce, form_name)
    elif form_name in ("FORM220", "FORM110"):
        items = parsear_form220_110(html, cuce, form_name)
    elif form_name == "FORM170":
        items = parsear_form170(html, cuce)

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
    await page.wait_for_timeout(800)

    print(f"{len(items)} ítems")
    return items

# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def scraping(entidades: list, anio: int, max_paginas: int):
    total_items = 0
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
            print('    --user-data-dir="/tmp/chrome-sicoes"')
            return

        print("✓ Conectado")

        # Usar el contexto existente del Chrome real (tiene las cookies/sesión)
        contexts = browser.contexts
        if not contexts:
            print("❌ Chrome no tiene contexto activo. Abrí una pestaña en SICOES.")
            return

        context = contexts[0]

        # Buscar pestaña de SICOES o abrir una nueva
        page = None
        for p_tab in context.pages:
            if "sicoes" in p_tab.url:
                page = p_tab
                print(f"✓ Usando pestaña existente: {p_tab.url[:60]}")
                break

        if not page:
            page = await context.new_page()
            print("✓ Abriendo nueva pestaña en SICOES...")
            await page.goto("https://www.sicoes.gob.bo/portal/index.php",
                           wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

        print("Navegando al buscador...")
        await ir_a_buscador(page)
        print("✓ Buscador listo")
        print(f"Entidades: {len(entidades)} | Año: {anio} | Max págs: {max_paginas}")
        print("=" * 60)

        for ent in entidades:
            cuce2, cuce3 = ent["codigo"].split("-")
            print(f"\n[{ent['codigo']}] {ent['nombre']}")

            for estado_label, estado_val in [("Contratados", "2C"), ("Desiertos", "2D")]:
                print(f"  → {estado_label}")
                await buscar(page, cuce2, cuce3, anio, estado_val)
                await page.evaluate("busquedadraw('1')")
                await page.wait_for_timeout(1000)
                try:
                    await page.wait_for_selector("table tbody tr td", timeout=10000)
                    await page.wait_for_timeout(600)
                except:
                    await page.wait_for_timeout(3000)

                paginas_vacias = 0
                pag = 1

                while pag <= max_paginas:
                    print(f"    Página {pag}...", end=" ", flush=True)
                    filas = await extraer_filas(page, ent["codigo"])
                    print(f"{len(filas)} procesos con tokens")

                    if not filas:
                        paginas_vacias += 1
                        if paginas_vacias >= 3:
                            print("    → 3 vacías consecutivas, pasando al siguiente estado")
                            break
                    else:
                        paginas_vacias = 0

                    items_pagina = 0
                    vacios_consecutivos = 0
                    for fila in filas:
                        if supabase_ya_procesado(fila["cuce"]):
                            print(f"        ↩ {fila['cuce']}: ya procesado, saltando")
                            continue
                        form_info = formulario_a_procesar(fila["modalidad"], fila["estado"], fila["tokens"])
                        if not form_info:
                            continue
                        form_name, token = form_info
                        items = await abrir_formulario(page, token, form_name, fila["cuce"])
                        if items:
                            vacios_consecutivos = 0
                            insertados = procesar_e_insertar(items)
                            items_pagina += insertados
                            total_items += insertados
                            total_procesos += 1
                        else:
                            vacios_consecutivos += 1
                            if vacios_consecutivos >= 3:
                                print(f"        ⏸ 3 vacíos seguidos — pausa {DELAY_RETRY:.0f}s para reset de rate limit...")
                                await asyncio.sleep(DELAY_RETRY)
                                vacios_consecutivos = 0
                        await asyncio.sleep(DELAY_FORM)

                    print(f"    → {items_pagina} ítems insertados en pág {pag}")
                    pag += 1
                    if pag <= max_paginas:
                        await ir_pagina(page, pag)
                        await asyncio.sleep(DELAY)

        # NO cerrar el browser — es el Chrome del usuario
        print(f"\n{'='*60}")
        print(f"COMPLETADO — Procesos: {total_procesos} | Ítems: {total_items}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SICOES Items Scraper (CDP)")
    parser.add_argument("--max-paginas", type=int, default=2, help="Páginas por estado/entidad (default: 2)")
    parser.add_argument("--anio", type=int, default=2026, help="Año CUCE (default: 2026)")
    args = parser.parse_args()

    print(f"SICOES Items Scraper CDP — año {args.anio} | max {args.max_paginas} págs/estado")
    asyncio.run(scraping(ENTIDADES_PRUEBA, args.anio, args.max_paginas))
