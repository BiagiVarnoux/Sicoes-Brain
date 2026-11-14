"""HTTP primario por página: no altera los ejecutores anteriores."""
import argparse
import asyncio
import hashlib
import json
import math
from pathlib import Path
import re
import time
from . import historico_http_directo as base
from .storage import PACKAGE,atomic,dumps,now,safe_root
from playwright.async_api import Error as PlaywrightError,TimeoutError as PlaywrightTimeoutError


SNAPSHOT_JS="""() => {
 const table=document.querySelector('#tablaAvanzada');
 const pager=document.querySelector('#tablaAvanzada_paginate');
 return {
   table_present:!!table,
   info:pager?.querySelector('.dataTables_info')?.textContent||'',
   raw_cuces:[...(table?.querySelectorAll(':scope > tbody > tr')||[])].map(r=>r.cells[0]?.textContent.trim()||'').filter(x=>/^\\d{2}-\\d{4}-\\d{2}-\\d+-[0-9A-Za-z]+-[0-9A-Za-z]+$/.test(x)),
   table_text:table?.querySelector('tbody')?.textContent||'',
   active_page:Number(pager?.querySelector('li.active a')?.textContent)||null,
   pager_last:(()=>{let m=0;(pager?pager.querySelectorAll('a'):[]).forEach(a=>{const t=(a.textContent||'').trim();if(/^\\d+$/.test(t)){const n=parseInt(t,10);if(n>m)m=n;}});return m;})()
 };
}"""


def pagination(snapshot,page_number=1):
    """Total del buscador avanzado + nº de páginas. El nº de páginas se toma del
    PAGINADOR del portal cuando está visible (autoritativo), no del cálculo
    total/tamaño: ese se desfasa —e inventa una página de más— si una página
    llega con una fila de menos por un render a medio pintar."""
    match=re.search(r'Se han encontrado\s+([\d.,\s]+)\s+registros',snapshot.get('info',''),re.I)
    total=int(re.sub(r'\D','',match[1])) if match else None
    count=len(snapshot.get('raw_cuces',[]))
    size=count if page_number==1 and count else None
    computed=math.ceil(total/size) if total is not None and size else (0 if total==0 else None)
    pager_last=snapshot.get('pager_last') or 0
    if total==0:pages=0
    elif pager_last>1:pages=pager_last
    else:pages=computed
    return {'registered_total':total,'page_size':size,'expected_pages':pages,
            'total_source':'advanced_search_info' if total is not None else 'unavailable',
            'page_size_source':'observed_first_page' if size else 'unavailable',
            'pages_source':'pager' if pager_last>1 else 'computed'}


async def snapshot(page):
    data=await page.evaluate(SNAPSHOT_JS)
    if not data.get('table_present'):raise base.RecoveryRequired('Tabla avanzada ausente: no es fin de resultados')
    return data


async def stable_snapshot(page):
    """Evita la carrera de render del portal: la tabla puede reportar una fila de
    menos si se la fotografía antes de que termine de pintar el draw de DataTables.
    Espera a que el nº de filas se repita en dos lecturas seguidas (para páginas con
    filas basta una repetición; para una tabla vacía se exige confirmarla varias
    veces por si aún está cargando) antes de confiar en la foto."""
    data=await snapshot(page);prev=len(data['raw_cuces']);stable=0
    for _ in range(10):
        await page.wait_for_timeout(350)
        data=await snapshot(page);count=len(data['raw_cuces'])
        if count==prev:
            stable+=1
            if count>0 or stable>=3:return data
        else:
            stable=0;prev=count
    return data


async def fresh_current(page,cuce,entity,number,nav):
    rows=await nav['extraer_filas'](page,entity)
    matches=[r for r in rows if r['cuce']==cuce]
    if len(matches)!=1:raise base.RecoveryRequired('CUCE ya no está en la página actual; no usar enlaces antiguos')
    row=matches[0];row['_result_page']=number
    nav['_active_cuce']=cuce
    return row


async def recover_current(page,entity,year,number,cuce,nav,root):
    """Una recuperación por proceso, sin recolectar todas las páginas otra vez."""
    event={'at':now(),'cuce':cuce,'page':number,'keepalive':'STARTED'}
    try:
        with base.timed(nav,'keepalive',cuce):await nav['keepalive'](page)
        event['keepalive']='VALIDATED'
        await page.wait_for_timeout(2500)
    except base.BrowserUnavailable:raise
    except Exception as exc:event.update(keepalive='FAILED',error_type=type(exc).__name__)
    finally:
        p=root/'recuperaciones.json';events=json.loads(p.read_text()) if p.exists() else []
        events.append(event);atomic(p,(dumps(events)+'\n').encode())
    with base.timed(nav,'search_recovery',cuce):
        await nav['ir_a_buscador'](page)
        a,b=entity.split('-');await nav['buscar'](page,a,b,year,'2C')
        await nav['ir_pagina'](page,number)
        await page.wait_for_function("cuce=>[...document.querySelectorAll('#tablaAvanzada > tbody > tr')].some(r=>r.cells[0]?.innerText.trim()===cuce)",arg=cuce,timeout=30000)
    return await fresh_current(page,cuce,entity,number,nav)


def quiet_exclusion_logging(nav):
    """Silenciar solo el aviso heredado repetido, en el namespace de esta corrida."""
    import types
    func=nav.get('extraer_filas')
    if not isinstance(func,types.FunctionType):return
    def historical_print(*args,**kwargs):
        if len(args)==1 and isinstance(args[0],str) and re.fullmatch(r"\s*\(saltando .* — modalidad .* fuera de alcance\)",args[0]):return
        print(*args,**kwargs)
    func.__globals__['print']=historical_print


def prior_eligible(path,entity,year,selected):
    if selected or not path.exists():return None,None
    try:
        previous=json.loads(path.read_text())
        if previous.get('entity')!=entity or previous.get('year')!=year or previous.get('termination')!='registered_total_verified' or previous.get('selected_cuces'):return None,None
        if previous.get('filters')!={'type':'Bienes','state':'2C','modalities':['CM','ANPE','ANPP','LP']}:return None,None
        ids={c for page in previous['pages'] for c in page['eligible_cuces']}
        if len(ids)!=previous.get('eligible_discovered'):return None,None
        return ids,previous.get('registered_total')
    except (ValueError,KeyError,TypeError):return None,None


def progress(index,discovered,selected,previous,last_page):
    if selected:return f'[{index}/{len(selected)} seleccionados]'
    if last_page:return f'[{index}/{len(discovered)} elegibles]'
    if previous is not None:return f'[{index}/{len(previous)} elegibles; referencia del inventario anterior]'
    return f'[{index}/? elegibles; {len(discovered)} descubiertos]'


async def walk(page,entity,year,converter,nav,root,selected=None):
    selected=set(selected or []);processed=set();seen_raw=set();discovered=set()
    results=json.loads((root/'REPORTE.json').read_text()) if (root/'REPORTE.json').exists() else {}
    previous,previous_registered=prior_eligible(root/'inventario_paginas.json',entity,year,selected)
    quiet_exclusion_logging(nav)
    current={};inventory={'entity':entity,'year':year,'filters':{'type':'Bienes','state':'2C','modalities':['CM','ANPE','ANPP','LP']},'at':now(),'selected_cuces':sorted(selected),'pages':[],'termination':None}
    number=1;empty=0;stale=0;meta=None
    def save():
        inventory['eligible_discovered']=len(discovered);inventory['registered_seen']=len(seen_raw)
        inventory['processed_this_run']=len(processed)
        atomic(root/'inventario_paginas.json',(dumps(inventory)+'\n').encode())
        atomic(root/'cuces_descubiertos.json',(dumps(sorted(discovered))+'\n').encode())
    while True:
        with base.timed(nav,'page_discovery',str(number)):
            if number>1:await nav['ir_pagina'](page,number)
            state=await stable_snapshot(page)
            if state.get('active_page') is not None and state['active_page']!=number:
                await page.wait_for_function("n=>Number(document.querySelector('#tablaAvanzada_paginate li.active a')?.textContent)===n",arg=number,timeout=30000)
                state=await stable_snapshot(page)
                if state.get('active_page')!=number:raise base.RecoveryRequired('El portal no confirmó la página solicitada')
            if meta is None:
                meta=pagination(state);inventory.update(meta)
                if previous_registered!=meta['registered_total']:previous=None
                if meta['registered_total'] is not None and bool(meta['registered_total'])!=bool(state['raw_cuces']):
                    raise base.RecoveryRequired('Total registrado y primera página incoherentes')
                print(f"Buscador avanzado: {meta['registered_total']} registrados; tamaño observado {meta['page_size']}; páginas calculadas {meta['expected_pages']}",flush=True)
            elif pagination(state,number)['registered_total']!=meta['registered_total']:
                raise base.RecoveryRequired('Cambió el total del buscador; revisar cobertura antes de continuar')
            raw=set(state['raw_cuces']);new=raw-seen_raw
            stale=stale+1 if raw and not new else 0
            if stale>=2:raise base.RecoveryRequired('Páginas repetidas sin avance; cobertura no confirmada')
            if not raw and not re.search(r'no hay datos|no se encontr|sin registros',state.get('table_text',''),re.I):
                raise base.RecoveryRequired('Tabla vacía sin mensaje de fin: posible fallo de sesión')
            seen_raw.update(raw)
            rows=await nav['extraer_filas'](page,entity)
            rows=[r for r in rows if re.fullmatch(re.escape(str(year)[2:]+'-'+entity)+r'-\d+-[0-9A-Za-z]+-[0-9A-Za-z]+',r['cuce'])]
            discovered.update(r['cuce'] for r in rows)
            if previous is not None and not discovered<=previous:previous=None
            excluded=sorted(raw-{r['cuce'] for r in rows})
            inventory['pages'].append({'page':number,'registered_rows':len(raw),'eligible_cuces':[r['cuce'] for r in rows],'excluded_cuces':excluded})
            print(f"Página {number}/{meta['expected_pages'] or '?'}: {len(raw)} registrados; {len(rows)} elegibles; {len(discovered)} elegibles descubiertos",flush=True)
            if excluded:print(f'    Fuera de filtros en esta página: {len(excluded)} CUCE (detalle en inventario_paginas.json)',flush=True)
            save()
        # Los candidatos de esta página se procesan ANTES de avanzar.
        for initial in rows:
            cuce=initial['cuce']
            if cuce in processed or selected and cuce not in selected:continue
            try:
                row=await fresh_current(page,cuce,entity,number,nav)
                last_page=meta['expected_pages'] is not None and number==meta['expected_pages']
                indicator=progress(len(processed)+1,discovered,selected,previous,last_page)
                print(f"{indicator} Página {number} — {cuce}",flush=True)
                ok=await base.process(page,row,root,nav,converter)
                if not ok and base.needs_recovery(root,cuce):
                    row=await recover_current(page,entity,year,number,cuce,nav,root)
                    ok=await base.process(page,row,root,nav,converter)
                manifest=json.loads((root/cuce/'manifest.json').read_text())
                current[cuce]=manifest['status'] if ok else 'PARCIAL';results[cuce]=current[cuce]
            except base.BrowserUnavailable:
                raise  # el navegador se cayó: no se puede continuar la gestión
            except (base.RecoveryRequired,PlaywrightTimeoutError,PlaywrightError) as exc:
                # Falla operativa de ESTE proceso (sesión/página/timeout). Lo dejo
                # PARCIAL y SIGO con el resto del año: un proceso trabado nunca más
                # aborta la gestión entera. Queda registrado para reconciliar.
                current[cuce]='PARCIAL';results[cuce]='PARCIAL'
                print(f"    {cuce}: no se pudo capturar ({type(exc).__name__}); queda PARCIAL, sigo con el resto",flush=True)
            processed.add(cuce);atomic(root/'REPORTE.json',(dumps(results)+'\n').encode());save()
            print(f"    Resultado: {current[cuce].replace('_',' ')}",flush=True)
            await page.wait_for_timeout(1500)
        if selected and selected<=processed:
            inventory['termination']='selected_scope_completed';save();break
        # Cobertura completa: ya se vieron todos los registrados → listo. Esto corta
        # ANTES de visitar una página de más, así un tamaño de página mal medido ya
        # no provoca una página fantasma ni un falso mismatch.
        if not selected and meta['registered_total'] is not None and len(seen_raw)>=meta['registered_total']:
            inventory['termination']='registered_total_verified';save();break
        if meta['expected_pages'] is not None and number>=max(1,meta['expected_pages']):
            if len(seen_raw)!=meta['registered_total']:
                inventory['termination']='total_mismatch'
                inventory['missing_count']=meta['registered_total']-len(seen_raw) if meta['registered_total'] is not None else None
                save()
                raise base.RecoveryRequired(f"CUCE observados ({len(seen_raw)}) no coinciden con total registrado ({meta['registered_total']})")
            inventory['termination']='registered_total_verified';save();break
        empty=empty+1 if not raw else 0
        if empty>=2:
            inventory['termination']='two_explicit_empty_pages_total_unavailable';save();break
        number+=1
    if selected-processed:
        inventory['missing_selected']=sorted(selected-processed);save()
        raise base.RecoveryRequired('No se encontraron todos los CUCE seleccionados')
    return current


async def run(entity,year,converter,selected=None,startup_seconds=0):
    from playwright.async_api import async_playwright
    root=safe_root(PACKAGE/'data'/f'historico_http_paginas_{entity}_{year}')
    started=time.monotonic();nav=base.original_functions('primary')
    nav['source_hashes']['historico_http_paginas.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    nav.update(_timing_root=root,_timing_mode='page_primary',_timing_started=started-startup_seconds,_selected_cuces=selected)
    nav['_timings'].append({'phase':'brave_startup','seconds':startup_seconds,'status':'OK'})
    atomic(root/'fuentes.json',(dumps(nav['source_hashes'])+'\n').encode())
    async with async_playwright() as pw:
        with base.timed(nav,'connect_and_search'):
            _,_,page=await base.connect_ready(pw,nav,root,entity,year)
        results=await walk(page,entity,year,converter,nav,root,selected)
    summary=base.summarize(root,list(results));atomic(root/'RESUMEN_HTTP.json',(dumps(summary)+'\n').encode())
    base.write_timings(root,nav,'page_primary',time.monotonic()-started+startup_seconds)
    print(f"Procesos finalizados: {len(results)}/{len(results)}",flush=True)
    print('Resumen HTTP: '+dumps(summary),flush=True);print(f'Resultados: {root}',flush=True)
    return base.exit_status(results)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entidad',default='0660-10');p.add_argument('--anio',type=int,default=2024)
    p.add_argument('--cuce',action='append');p.add_argument('--check',action='store_true')
    args=p.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}',args.entidad) or not 2000<=args.anio<=2100:p.error('Entidad o gestión inválida')
    if args.cuce and any(not re.fullmatch(re.escape(str(args.anio)[2:]+'-'+args.entidad)+r'-\d+-[0-9A-Za-z]+-[0-9A-Za-z]+',c) for c in args.cuce):p.error('CUCE fuera de alcance')
    converter=base.dependencies()
    if args.check:print('Dependencias disponibles. Sin conexiones.');return
    started=time.monotonic();base.prepare_brave();elapsed=time.monotonic()-started
    try:
        code=asyncio.run(run(args.entidad,args.anio,converter,args.cuce,elapsed))
    except (base.RecoveryRequired,base.BrowserUnavailable,PlaywrightTimeoutError,PlaywrightError) as exc:
        # Cierre limpio y legible (sin traceback de Python): lo descargado se
        # conserva y la gestión queda marcada para reconciliar/reintentar por CUCE.
        print(f'Gestión {args.anio}: {type(exc).__name__}: {exc}. Lo descargado se conserva; queda registrado como pendiente de reconciliación.',flush=True)
        raise SystemExit(1)
    raise SystemExit(code)


if __name__=='__main__':main()
