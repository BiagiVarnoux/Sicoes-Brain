"""Variante HTTP primaria: sin extracción DOM; diagnóstico comparativo opcional.
Reutiliza funciones del histórico mediante AST, sin importar sus clientes Supabase.
"""
import argparse
import ast
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import urllib.request
from .storage import ROOT,PACKAGE,atomic,dumps,now,safe_root
from .parsing import validate
from .http_forms import capture_once,capture_primary
from contextlib import contextmanager

def _cdp_port():
    """Puerto CDP de esta corrida. Default 9226; configurable para correr DOS
    corridas en paralelo (cada una su puerto y su perfil). Valor inválido → 9226."""
    raw=os.environ.get('SICOES_LOCAL_CDP_PORT')
    if not raw:return 9226
    try:value=int(raw)
    except ValueError:return 9226
    return value if 1024<=value<=65535 else 9226
PORT=_cdp_port()
# El perfil default se conserva idéntico en 9226 (compatibilidad); otros puertos
# usan un perfil propio para no compartir sesión entre corridas paralelas.
PROFILE=PACKAGE/'data'/('brave-historico-http' if PORT==9226 else f'brave-historico-http-{PORT}')
ENDPOINT=f'http://127.0.0.1:{PORT}'
PORTAL='https://www.sicoes.gob.bo/portal/index.php'
BRAVE=Path('/Applications/Brave Browser.app/Contents/MacOS/Brave Browser')


def dependencies():
    missing=[n for n in ('playwright','markitdown','pdfminer','mammoth','bs4','lxml') if importlib.util.find_spec(n) is None]
    if missing:raise RuntimeError('Faltan dependencias locales: '+', '.join(missing))
    # No clientes IA: MarkItDown sin llm_client ni plugins externos.
    from markitdown import MarkItDown
    import inspect
    kwargs={'enable_plugins':False} if 'enable_plugins' in inspect.signature(MarkItDown).parameters else {}
    return MarkItDown(**kwargs)


@contextmanager
def timed(nav,phase,label=None):
    started=time.monotonic();status='OK'
    try:yield
    except BaseException:
        status='FAILED';raise
    finally:
        event={'phase':phase,'seconds':round(time.monotonic()-started,6),'status':status,'at':now()}
        if label:event['label']=label
        nav.setdefault('_timings',[]).append(event)
        if '_timing_root' in nav:
            write_timings(nav['_timing_root'],nav,nav['_timing_mode'],time.monotonic()-nav['_timing_started'],announce=False)


def write_timings(root,nav,mode,total,announce=True):
    import uuid
    totals={}
    for event in nav.get('_timings',[]):totals[event['phase']]=round(totals.get(event['phase'],0)+event['seconds'],6)
    report={'mode':mode,'at':now(),'wall_seconds':round(total,6),'phase_seconds':totals,'events':nav.get('_timings',[]),'source_hashes':nav.get('source_hashes',{}),'selected_cuces':nav.get('_selected_cuces'),
            'note':'Las fases pueden estar anidadas; no sumar fases como tiempo total.'}
    run_id=nav.setdefault('_timing_run_id',uuid.uuid4().hex)
    atomic(root/'tiempos'/(run_id+'.json'),(dumps(report)+'\n').encode())
    if announce:print('Tiempos por fase: '+dumps(totals),flush=True)


class BrowserUnavailable(RuntimeError):pass
class RecoveryRequired(RuntimeError):pass


def collapse_forms(forms):
    """Si un mismo formulario aparece varias veces, conservar SOLO el último.

    El portal lista los formularios de arriba a abajo; cuando un formulario se
    repite (p.ej. varios FORM 170 por re-adjudicación) las apariciones previas
    quedaron anuladas/descalificadas y solo la última es la versión vigente. Se
    identifican por su número (``\\d{3}``) y se conserva la última de cada
    número, preservando el orden de aparición. Los enlaces sin número
    reconocible no se agrupan y se dejan intactos."""
    def num(f):
        m=re.search(r'\d{3}',f.get('label',''))
        return m[0] if m else None
    last={}
    for i,f in enumerate(forms):
        n=num(f)
        if n is not None:last[n]=i
    return [f for i,f in enumerate(forms) if num(f) is None or last[num(f)]==i]


async def refresh_row(page,row,nav):
    """Leer argumentos actuales; nunca persistirlos en manifiestos."""
    entity='-'.join(row['cuce'].split('-')[1:3])
    matches=[r for r in await nav['extraer_filas'](page,entity) if r['cuce']==row['cuce']]
    if len(matches)!=1:raise RecoveryRequired('Fila avanzada ausente o no unívoca')
    row.update(matches[0])
    row['forms']=collapse_forms(row.get('forms',[]))


async def form_http_guard(page,operation):
    """Interrumpir la espera del DOM si el servidor ya respondió con error."""
    failed=asyncio.get_running_loop().create_future()
    def response_received(response):
        from urllib.parse import urlsplit
        url=urlsplit(response.url)
        if url.hostname=='www.sicoes.gob.bo' and url.path.endswith('/verFormulario.php') and response.status>=400:
            if not failed.done():failed.set_result(response.status)
    page.on('response',response_received)
    task=asyncio.create_task(operation())
    try:
        done,_=await asyncio.wait((task,failed),return_when=asyncio.FIRST_COMPLETED)
        if failed in done:
            raise RecoveryRequired(f'Formulario respondió HTTP {failed.result()}')
        return await task
    finally:
        page.remove_listener('response',response_received)
        if not task.done():task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        failed.cancel()

def ensure_browser(page):
    if page.is_closed() is True or (page.context.browser is not None and page.context.browser.is_connected() is False):
        raise BrowserUnavailable('Navegador/contexto cerrado; detener y reanudar con el lanzador')


def original_functions(mode="primary"):
    if mode not in ("primary","compare"):raise ValueError("Modo inválido")
    ns={'os':os,'re':re,'json':json,'PORTAL':PORTAL,
        'BUSCADOR':'/portal/contrataciones/busqueda/convocatorias.php?tipo=convNacional',
        'MODALIDADES':{'CM','ANPE','ANPP','LP'}}
    sources={
      'probe_historico.py':{'_sanitizar_fs','_ext_desde_headers','_nombre_desde_cd','_asegurar_portal','ir_a_buscador','buscar','extraer_filas','descargar_token','_cerrar_modales','_cerrar_modal_real','keepalive','_abrir_form_intento','abrir_formulario_html'},
      'sicoes_items_cdp.py':{'ir_pagina'},
      'historico.py':{'_detectar_paginas','_recolectar_filas','_revivir_sesion'}}
    hashes={}
    for filename,names in sources.items():
        src=(ROOT/'scraper'/filename).read_text();hashes[filename]=hashlib.sha256(src.encode()).hexdigest()
        nodes=[n for n in ast.parse(src).body if isinstance(n,ast.AsyncFunctionDef) and n.name in names or isinstance(n,ast.FunctionDef) and n.name in names]
        if {n.name for n in nodes}!=names:raise RuntimeError('Cambió la interfaz del histórico: '+filename)
        for node in nodes:
            if node.name=='_recolectar_filas':
                for child in ast.walk(node):
                    if isinstance(child,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='de_pag' for t in child.targets):
                        child.value=ast.Call(func=ast.Name(id='_tag_page',ctx=ast.Load()),args=[child.value,ast.Name(id='pag',ctx=ast.Load())],keywords=[])
            for child in ast.walk(node):
                if not isinstance(child,ast.Constant) or not isinstance(child.value,str):continue
                # Dos tablas simultáneas e ID de contenido repetido en el DOM real.
                child.value=child.value.replace("document.querySelectorAll('table tbody tr')","document.querySelectorAll('#tablaAvanzada > tbody > tr')")
                child.value=child.value.replace("document.querySelector('ul.pagination')","document.querySelector('#f-avanzada ul.pagination')")
                child.value=child.value.replace('#visualizarformulario0 table','#modalVerFormulario [id=visualizarformulario0] table, #modalFormulario [id=visualizarformulario0] table')
                child.value=child.value.replace("document.getElementById('visualizarformulario0')","document.querySelector('#modalVerFormulario [id=visualizarformulario0], #modalFormulario [id=visualizarformulario0]')")
                child.value=child.value.replace('#modalFormulario .close,','#modalVerFormulario .close, #modalFormulario .close,')
                child.value=child.value.replace('.btn-primary, button[type="submit"]','#formAvanzada input[type="submit"], #formAvanzada button[type="submit"]')
                child.value=child.value.replace("b.textContent.includes('Buscar')","(b.textContent || b.value || '').includes('Buscar')")
                child.value=child.value.replace('/tmp/sicoes_keepalive',str(PACKAGE/'data/historico_http_auxiliares'))
                child.value=child.value.replace('if (window.$) window.$.fn.modal = function() { return this; };','')
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),filename,'exec'),ns)
    def tag_page(rows,page):
        for row in rows:row['_result_page']=page
        return rows
    ns['_tag_page']=tag_page
    ns['_timings']=[]
    ns['_capture_owns_close']=True
    async def keepalive(page):
        ensure_browser(page)
        token=await page.evaluate(r'''cuce=>[...document.querySelectorAll('#tablaAvanzada > tbody > tr')]
          .find(tr=>tr.cells[0]?.innerText.trim()===cuce)?.querySelector('a[onclick*="descargarArchivo"]')
          ?.getAttribute('onclick')?.match(/descargarArchivo\('([^']+)'\)/)?.[1]||null''',ns.get('_active_cuce'))
        if not token:
            raise RecoveryRequired('KEEPALIVE: sin documento auxiliar elegible en la fila actual')
        print('    KEEPALIVE: archivo auxiliar del CUCE actual',flush=True)
        path=await ns['descargar_token'](page,token,str(PACKAGE/'data/historico_http_auxiliares'),'keepalive')
        ensure_browser(page)
        if not path:raise RecoveryRequired('KEEPALIVE: petición auxiliar sin archivo recibido')
        checked=validate(Path(path).read_bytes(),'ANNEX',ns['_active_cuce'])
        if not checked['valid']:raise RecoveryRequired('KEEPALIVE: respuesta auxiliar inválida; original conservado')
        print('    KEEPALIVE: archivo auxiliar recibido y validado',flush=True)
        return True
    original_download=ns['descargar_token'];download_lock=asyncio.Lock()
    async def download(page,token,folder,label):
        async with download_lock:
            ensure_browser(page)
            print(f'    Descarga {label}: esperando disponibilidad del portal',flush=True)
            with timed(ns,'download_guard',label):
                await page.wait_for_function("()=>typeof esperandoTokenDescargaArchivo==='undefined'||esperandoTokenDescargaArchivo===false",timeout=20000)
            with timed(ns,'download',label):
                result=await original_download(page,token,folder,label)
            ensure_browser(page)
            print(f"    Descarga {label}: {'archivo recibido' if result else 'sin archivo recibido'}",flush=True)
            return result
    original_close=ns['_cerrar_modal_real']
    async def checked_close(page):
        await original_close(page)
        try:
            await page.wait_for_function("()=>![...document.querySelectorAll('#modalVerFormulario, #modalFormulario')].some(m=>m.getClientRects().length && getComputedStyle(m).visibility!=='hidden')",timeout=5000)
        except Exception:raise RecoveryRequired('Modal no cerrado: recuperar antes de continuar') from None
    ns['_cerrar_modal_real']=checked_close
    ns['descargar_token']=download
    ns['keepalive']=keepalive
    async def open_form(page,token):
        row=ns['_active_row'];label=ns['_active_label'];occurrence=ns.get('_active_occurrence',0)
        await refresh_row(page,row,ns)
        group=[f for f in row.get('forms',[]) if f['label']==label]
        if len(group)<=occurrence:raise RuntimeError('FORM no anunciado o incompleto; no activar KEEPALIVE')
        token=group[occurrence]['token']
        form=re.search(r'\d{3}',label);kind='FORM'+form[0] if form else 'FORM'
        async def opening():
            return await ns['_abrir_form_intento'](page,token,25000)
        started=time.monotonic()
        if mode=='compare':
            result=await capture_once(page,opening,lambda:ns['_cerrar_modal_real'](page),row['cuce'],kind)
            result['mode']='compare';result['comparison_performed']=True
        else:
            async def trigger():
                await ns['_cerrar_modales'](page)
                await page.wait_for_timeout(500)  # pausa previa original; no espera de renderizado
                await page.evaluate('token=>{verFormulario(token);}',token)
            async def modal_ready():
                # Esperar solo el modal y su botón real evita cerrar antes de que
                # el callback AJAX lo muestre. No espera ni extrae sus tablas.
                await page.wait_for_function("()=>[...document.querySelectorAll('#modalVerFormulario, #modalFormulario')].some(m=>m.getClientRects().length && getComputedStyle(m).visibility!=='hidden' && m.querySelector('.close'))",timeout=5000)
            result=await capture_primary(page,trigger,lambda:ns['_cerrar_modal_real'](page),row['cuce'],kind,before_close=modal_ready)
        folder=ns['_http_folder'];digest=hashlib.sha256(result['raw_body']).hexdigest()
        import uuid
        prefix=re.sub(r'[^A-Za-z0-9_-]','_',label)+'__'+digest+'__'+uuid.uuid4().hex
        atomic(folder/(prefix+'.response'),result['raw_body'])
        if result.get('http_html') is not None:atomic(folder/(prefix+'.http.html'),result['http_html'].encode())
        if result.get('dom_html') is not None:atomic(folder/(prefix+'.dom.html'),result['dom_html'].encode())
        record={k:result[k] for k in ('status','valid','validation','comparison','recovery_reason','error','close_error','mode','comparison_performed','timings') if k in result}
        record.update(sha256=digest,bytes=len(result['raw_body']),at=now(),elapsed_seconds=round(time.monotonic()-started,3))
        atomic(folder/(prefix+'.json'),(dumps(record)+'\n').encode())
        print(f"    HTTP {label}: estado {result['status']}; válido={result['valid']}; comparación={result.get('comparison')}",flush=True)
        if result.get('close_error'):raise RecoveryRequired('No se pudo verificar el cierre del modal; evidencia HTTP conservada')
        if not result['valid']:
            if result['status'] in (401,403) or 'captcha' in result.get('validation',{}).get('errors',[]):
                raise BrowserUnavailable('Control de acceso/captcha: resolver manualmente en Brave y reanudar')
            if result.get('recovery_reason') in ('http_server_error','dom_timeout'):raise RecoveryRequired('Fallo HTTP/timeout: evaluar recuperación reactiva')
            raise RuntimeError('Respuesta inválida o documento ausente; no activar KEEPALIVE automáticamente')
        if mode=='compare' and not result.get('dom_html','').strip():raise RecoveryRequired('Modal vacío: recuperación reactiva')
        if mode=='compare' and not all(result.get('comparison',{}).get(k,False) for k in ('same_visible_text','same_tables')):
            raise RuntimeError('Respuesta HTTP y DOM difieren: conservar evidencia y revisar')
        return result['http_html']
    ns['abrir_formulario_html']=open_form
    hashes['historico_http_directo.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    hashes['http_forms.py']=hashlib.sha256((PACKAGE/'http_forms.py').read_bytes()).hexdigest()
    ns['source_hashes']=hashes
    return ns


def prepare_brave(timeout=300):
    """Mismo arranque automático del .command histórico; perfil aislado del original."""
    profile=safe_root(PROFILE)
    lsof=shutil.which('lsof')
    if not lsof:raise RuntimeError('Falta lsof para identificar el navegador experimental')
    def pids():
        r=subprocess.run([lsof,'-nP',f'-iTCP:{PORT}','-sTCP:LISTEN','-t'],capture_output=True,text=True,check=False)
        if r.returncode not in (0,1):raise RuntimeError('No se pudo verificar el puerto experimental')
        return sorted({int(x) for x in r.stdout.split() if x.isdigit()})
    def authorized(ids):
        for pid in ids:
            args=subprocess.check_output(['/bin/ps','-ww','-p',str(pid),'-o','args='],text=True)
            from .brave_bootstrap import command_matches
            # La comprobación de perfil se aplica sobre el argumento del puerto propio.
            check=args
            if str(BRAVE) not in args or not command_matches(check,profile,PORT):
                raise RuntimeError(f'{PORT} pertenece a otro navegador/perfil; no se reutilizará')
    ids=pids()
    if ids:authorized(ids)
    else:
        with socket.socket() as sock:
            try:sock.bind(('127.0.0.1',PORT))
            except OSError:raise RuntimeError(f'{PORT} ocupado sin propietario verificable') from None
        if not BRAVE.is_file():raise RuntimeError('Brave no está instalado en /Applications')
        with (profile.parent/'brave-historico-http.log').open('ab') as log:
            subprocess.Popen([str(BRAVE),f'--remote-debugging-port={PORT}',f'--user-data-dir={profile}',PORTAL],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline=time.monotonic()+timeout;next_notice=0
    print(f'Esperando Brave en {PORT} (hasta {timeout} segundos)...',flush=True)
    while time.monotonic()<deadline:
        if time.monotonic()>=next_notice:
            print('    Brave todavía se está preparando; no cierres su ventana.',flush=True)
            next_notice=time.monotonic()+15
        ids=pids()
        if ids:
            authorized(ids)
            try:
                with opener.open(ENDPOINT+'/json/version',timeout=5) as r:version=json.loads(r.read(65536))
                if not version.get('webSocketDebuggerUrl','').startswith(f'ws://127.0.0.1:{PORT}/devtools/browser/'):
                    raise RuntimeError('Respuesta CDP no reconocida')
                return
            except (OSError,ValueError):pass
        time.sleep(1)
    raise RuntimeError(f'Brave no respondió en {PORT} tras {timeout} segundos; se conserva todo lo descargado')


def save_original(folder,label,data,kind,cuce):
    digest=hashlib.sha256(data).hexdigest();check=validate(data,kind,cuce)
    suffix={'html':'.html','pdf':'.pdf','docx':'.docx','ole':'.doc','json':'.json'}.get(check['detected_type'],'.bin')
    name=re.sub(r'[^A-Za-z0-9_-]','_',label)[:60] or 'documento'
    target=folder/'crudos'/(name+'__'+digest+suffix)
    if not target.exists():atomic(target,data)
    elif hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Original previo con hash incorrecto')
    return {'path':str(target.relative_to(folder)),'sha256':digest,'bytes':len(data),'format':check['detected_type'],'valid':check['valid'],'errors':check['errors']}


def convert(folder,entry,converter):
    source=folder/entry['path'];target=folder/'md'/(source.stem+'.md')
    try:
        if entry['format']=='ole':
            if not shutil.which('textutil'):raise RuntimeError('DOC antiguo requiere textutil de macOS')
            text=subprocess.check_output(['textutil','-convert','txt','-stdout',str(source)],timeout=120).decode('utf-8')
        else:
            result=converter.convert(str(source));text=getattr(result,'text_content','') or getattr(result,'markdown','')
        if not text.strip():
            if entry.get('valid') and entry['format']=='pdf':
                entry.update(conversion='FALTA_OCR',ocr_reason='PDF válido sin texto extraíble')
                for key in ('error','error_type'):entry.pop(key,None)
                return entry
            raise RuntimeError('Sin texto extraíble')
        atomic(target,text.encode());entry.update(markdown=str(target.relative_to(folder)),conversion='CONVERTED')
    except (KeyboardInterrupt,SystemExit):raise
    except BaseException as exc:
        entry.update(conversion='FAILED_CONVERSION',error_type=type(exc).__name__,error=str(exc)[:500])
    return entry


def nth_link(links,label,occurrence=0):
    """Token de la ``occurrence``-ésima aparición de ``label`` en la fila refrescada.

    Desambigua formas repetidas (p.ej. dos FORM 170: pre-adjudicación anulada y
    re-adjudicación) por ORDEN, no por token (el portal regenera tokens al
    refrescar). Con etiqueta única equivale al comportamiento previo."""
    group=[d for d in links if d.get('label')==label]
    if len(group)<=occurrence:
        raise RecoveryRequired('Documento ya no disponible o incompleto en la fila actual')
    return group[occurrence]['token']


def targets(row):
    docs=[('FORM',f['label'],f['token']) for f in collapse_forms(row.get('forms',[]))]
    wanted='oferta' if row['modalidad']=='CM' else 'documento base'
    selected=[a for a in row.get('archivos',[]) if wanted in a.get('label','').lower()]
    docs.extend(('OFFER' if row['modalidad']=='CM' else 'DBC',a['label'],a['token']) for a in selected)
    if not selected:docs.append(('OFFER' if row['modalidad']=='CM' else 'DBC',wanted,None))
    return docs


async def process(page,row,root,nav,converter,missing_only=False):
    folder=root/row['cuce'];folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/'manifest.json'
    report=json.loads(manifest.read_text()) if manifest.exists() else {'cuce':row['cuce'],'documents':{}}
    # Metadata pública: nunca guardar argumentos operativos como credenciales.
    report['metadata']={k:v for k,v in row.items() if k not in ('forms','archivos')}
    report['announced']={k:[{'label':x['label']} for x in row.get(k,[])] for k in ('forms','archivos')}
    complete=True;report['needs_navigation_recovery']=False
    nav['_active_row']=row
    nav['_http_folder']=folder/'http';nav['_http_folder'].mkdir(exist_ok=True)
    seen_labels={}
    for position,(kind,label,token) in enumerate(targets(row)):
        occurrence=seen_labels.get((kind,label),0);seen_labels[(kind,label)]=occurrence+1
        print(f'    {label}: preparando',flush=True)
        key=f'{kind}:{label}:{position}';doc=report['documents'].setdefault(key,{'label':label,'kind':kind,'versions':[],'attempts':[]})
        good=next((v for v in reversed(doc['versions']) if v['valid'] and (folder/v['path']).exists() and hashlib.sha256((folder/v['path']).read_bytes()).hexdigest()==v['sha256']),None)
        if good:
            if missing_only:
                print(f'    {label}: original válido conservado; sin reprocesar',flush=True)
                complete=complete and good.get('conversion') in ('CONVERTED','FALTA_OCR')
                continue
            if good.get('conversion')!='FALTA_OCR' and (good.get('conversion')!='CONVERTED' or not (folder/good.get('markdown','missing')).is_file()):
                with timed(nav,'conversion_reused',label):convert(folder,good,converter)
            print(f"    {label}: original conservado; {good.get('conversion')}",flush=True)
            complete=complete and good.get('conversion') in ('CONVERTED','FALTA_OCR')
            atomic(manifest,(dumps(report)+'\n').encode());continue
        # Hasta REINTENTOS intentos por documento ante fallos NO de sesión (p. ej.
        # conversión, original inválido, timeouts sueltos). Un fallo de captura/sesión
        # no se martilla acá: corta para que la recuperación de sesión reviva y reprocese.
        REINTENTOS=3;doc_complete=False;need_session_recovery=False
        for retry in range(REINTENTOS):
            attempt={'at':now()}
            if retry:attempt['retry']=retry
            doc['attempts'].append(attempt)
            stage='inventory'
            try:
                ensure_browser(page)
                if not token:raise RuntimeError('Documento objetivo no anunciado')
                stage='capture'
                if 'extraer_filas' in nav:
                    await refresh_row(page,row,nav)
                    links=row.get('forms' if kind=='FORM' else 'archivos',[])
                    token=nth_link(links,label,occurrence)
                nav['_active_label']=label;nav['_active_occurrence']=occurrence
                if kind=='FORM':
                    try:
                        with timed(nav,'form_capture',label):
                            html=await nav['abrir_formulario_html'](page,token)
                    finally:
                        if not nav.get('_capture_owns_close',False):await nav['_cerrar_modal_real'](page)
                    data=("<html><meta charset='utf-8'><body>"+html+'</body></html>').encode()
                    form=re.search(r'\d{3}',label);validation_kind='FORM'+form[0] if form else 'FORM'
                else:
                    # El descargador histórico escribe en un directorio por intento: no pisa originales.
                    import uuid
                    incoming=folder/'descargas'/uuid.uuid4().hex
                    path=await nav['descargar_token'](page,token,str(incoming),kind)
                    ensure_browser(page)
                    if not path:raise RecoveryRequired('Descarga sin archivo: recuperación de navegación requerida')
                    data=Path(path).read_bytes();validation_kind='ANNEX'
                entry=save_original(folder,label,data,validation_kind,row['cuce'])
                if not any(v['sha256']==entry['sha256'] for v in doc['versions']):doc['versions'].append(entry)
                if not entry['valid']:raise RuntimeError('Original recibido no válido')
                stage='conversion'
                with timed(nav,'conversion',label):convert(folder,entry,converter)
                attempt['status']=entry['conversion']
                print(f"    {label}: original guardado ({entry['bytes']} bytes); {entry['conversion']}",flush=True)
                doc_complete=entry['conversion'] in ('CONVERTED','FALTA_OCR')
                atomic(manifest,(dumps(report)+'\n').encode());break  # documento logrado
            except Exception as exc:
                # No serializar excepciones de Playwright: pueden contener tokens/URLs.
                attempt.update(status='FAILED',error_type=type(exc).__name__,stage=stage,
                               reason=str(exc) if isinstance(exc,RecoveryRequired) else 'Fallo en '+stage)
                if isinstance(exc,BrowserUnavailable):
                    report['status']='INTERRUMPIDA';atomic(manifest,(dumps(report)+'\n').encode());raise
                recoverable=isinstance(exc,(RecoveryRequired,TimeoutError)) or type(exc).__name__=='TimeoutError'
                report['needs_navigation_recovery']|=recoverable
                report['reactive_recovery_reason']=type(exc).__name__ if recoverable else None
                if stage in ('capture','keepalive'):
                    print(f'    {label}: fallo en {stage} ({type(exc).__name__})',flush=True)
                    need_session_recovery=True;atomic(manifest,(dumps(report)+'\n').encode());break
                last=retry>=REINTENTOS-1
                print(f'    {label}: fallo en {stage} ({type(exc).__name__}) — intento {retry+1}/{REINTENTOS}'+(''if last else'; reintento'),flush=True)
                atomic(manifest,(dumps(report)+'\n').encode())
                if not last:await page.wait_for_timeout(1500)
        complete=complete and doc_complete
        if need_session_recovery:break  # recuperar antes de seguir sobre una sesión incierta
    report['pending_ocr']=[d['label'] for d in report['documents'].values()
                           if next((v for v in reversed(d['versions']) if v.get('valid')),{}).get('conversion')=='FALTA_OCR']
    status=('FALTA_OCR' if report['pending_ocr'] else 'COMPLETA') if complete else 'PARCIAL'
    report.update(status=status,updated_at=now())
    atomic(manifest,(dumps(report)+'\n').encode())
    return complete


async def position_process(page,row,nav):
    ensure_browser(page)
    number=row.get('_result_page',1)
    print(f"    Buscador avanzado: página {number} para {row['cuce']}",flush=True)
    await nav['ir_pagina'](page,number)
    await page.wait_for_function("cuce=>[...document.querySelectorAll('#tablaAvanzada > tbody > tr')].some(tr=>tr.cells[0]?.innerText.trim()===cuce)",arg=row['cuce'],timeout=30000)
    nav['_active_cuce']=row['cuce']
    if 'extraer_filas' in nav:await refresh_row(page,row,nav)


async def configure_downloads(context,page,root):
    path=root/'descargas_nativas';path.mkdir(parents=True,exist_ok=True)
    cdp=await context.new_cdp_session(page)
    try:await cdp.send('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(path.resolve()),'eventsEnabled':True})
    finally:await cdp.detach()


def needs_recovery(root,cuce):
    return json.loads((root/cuce/'manifest.json').read_text()).get('needs_navigation_recovery',False)


async def connect_ready(pw,nav,root,entity,year,timeout=600):
    """Arranque tolerante a CDP lento y pestañas cerradas/restauradas por Brave."""
    loop=asyncio.get_running_loop();deadline=loop.time()+timeout;attempt=0
    async def once():
        browser=await pw.chromium.connect_over_cdp(ENDPOINT,timeout=60000)
        if not browser.contexts:raise BrowserUnavailable('Brave todavía no tiene contexto')
        context=browser.contexts[0]
        page=next((p for p in context.pages if not p.is_closed() and p.url.startswith(PORTAL)),None)
        if page is None:page=await context.new_page()
        await configure_downloads(context,page,root)
        await nav['ir_a_buscador'](page)
        cuce2,cuce3=entity.split('-')
        await nav['buscar'](page,cuce2,cuce3,year,'2C')
        await page.evaluate("busquedadraw('1')");await page.wait_for_timeout(1200)
        ensure_browser(page)
        return browser,context,page
    while loop.time()<deadline:
        attempt+=1
        print(f'Preparando conexión y portal: intento {attempt}, quedan {max(1,int(deadline-loop.time()))} s...',flush=True)
        try:return await asyncio.wait_for(once(),timeout=max(.001,deadline-loop.time()))
        except Exception as exc:
            retryable=isinstance(exc,(OSError,RuntimeError,TimeoutError)) or type(exc).__module__.startswith('playwright.')
            if not retryable:raise
            print(f'    Arranque aún no listo ({type(exc).__name__}); reintento en 5 s. No cierres Brave.',flush=True)
            remaining=deadline-loop.time()
            if remaining<=0:break
            await asyncio.sleep(min(5,remaining))
    raise BrowserUnavailable(f'No se pudo estabilizar Brave/portal en {timeout} segundos. Datos conservados; reabrí el lanzador para reanudar.')


async def run(entity,year,converter,selected_cuces=None,missing_only=False,mode="primary",startup_seconds=0):
    from playwright.async_api import async_playwright
    started=time.monotonic()
    root=safe_root(PACKAGE/'data'/f'historico_http_directo_{mode}_{entity}_{year}')
    nav=original_functions(mode);nav.setdefault('_timings',[]).append({'phase':'brave_startup','seconds':startup_seconds,'status':'OK'});atomic(root/'fuentes.json',(dumps(nav['source_hashes'])+'\n').encode())
    nav.update(_timing_root=root,_timing_mode=mode,_timing_started=started-startup_seconds,_selected_cuces=selected_cuces)
    async with async_playwright() as pw:
        with timed(nav,'connect_and_search'):
            browser,context,page=await connect_ready(pw,nav,root,entity,year)
        cuce2,cuce3=entity.split('-')
        with timed(nav,'discovery'):
            hint=await nav['_detectar_paginas'](page)
            rows=await nav['_recolectar_filas'](page,entity,hint,0,0)
        rows={r['cuce']:r for r in rows if re.fullmatch(re.escape(str(year)[2:]+'-'+entity)+r'-\d+-\d+-\d+',r['cuce'])}
        if selected_cuces:
            if any(c not in rows for c in selected_cuces):raise RecoveryRequired('CUCE solicitado no encontrado en el alcance')
            rows={c:rows[c] for c in selected_cuces}
        else:atomic(root/'cuces.json',(dumps(sorted(rows))+'\n').encode())
        print(f'{len(rows)} procesos históricos encontrados; sin límite de cinco.',flush=True)
        results=json.loads((root/'REPORTE.json').read_text()) if (root/'REPORTE.json').exists() else {}
        current_results={}
        for i,cuce in enumerate(list(rows),1):
            print(f'[{i}/{len(rows)}] {cuce}',flush=True)
            with timed(nav,'position',cuce):
                await position_process(page,rows[cuce],nav)
            ok=await process(page,rows[cuce],root,nav,converter,missing_only)
            if not ok and needs_recovery(root,cuce):
                ensure_browser(page)
                print('    Recuperación por fallo de captura/navegación; no por conversión',flush=True)
                recovery={'at':now(),'cuce':cuce,'trigger':'recoverable_failure','keepalive':'STARTED'}
                try:
                    print('    KEEPALIVE reactivo: fallo recuperable; un solo intento',flush=True)
                    with timed(nav,'keepalive',cuce):
                        await nav['keepalive'](page)
                    recovery['keepalive']='VALIDATED'
                    with timed(nav,'recovery_pause',cuce):
                        await page.wait_for_timeout(2500)
                except Exception as exc:
                    recovery.update(keepalive='FAILED',error_type=type(exc).__name__)
                    print(f'    KEEPALIVE reactivo no completado ({type(exc).__name__}); recuperar buscador una vez',flush=True)
                history=root/'recuperaciones.json'
                events=json.loads(history.read_text()) if history.exists() else []
                events.append(recovery);atomic(history,(dumps(events)+'\n').encode())
                with timed(nav,'search_recovery',cuce):
                    rows.update(await nav['_revivir_sesion'](page,cuce2,cuce3,year,'2C',entity,hint,0,0))
                if cuce in rows:
                    with timed(nav,'position_recovered',cuce):
                        await position_process(page,rows[cuce],nav)
                    ok=await process(page,rows[cuce],root,nav,converter,missing_only)
            status=json.loads((root/cuce/'manifest.json').read_text()).get('status','COMPLETA') if ok else 'PARCIAL'
            results[cuce]=status
            print(f'    Resultado {cuce}: '+status.replace('_',' '),flush=True)
            current_results[cuce]=results[cuce]
            atomic(root/'REPORTE.json',(dumps(results)+'\n').encode())
            await page.wait_for_timeout(1500)
        summary=summarize(root,list(current_results))
        atomic(root/'RESUMEN_HTTP.json',(dumps(summary)+'\n').encode())
        write_timings(root,nav,mode,time.monotonic()-started+startup_seconds)
        print('Resumen HTTP: '+dumps(summary),flush=True)
        print(f'Resultados locales: {root}',flush=True)
        return exit_status(current_results)


def exit_status(results):
    return 0 if results and all(v in ('COMPLETA','FALTA_OCR') for v in results.values()) else 2


def summarize(root,cuces):
    counts={'processes':len(cuces),'valid_originals':0,'converted':0,'http_records':0,'matching_http_dom':0,'http_errors':0,'primary_http_records':0,'compared_records':0,'pending_ocr':0}
    for cuce in cuces:
        manifest=root/cuce/'manifest.json'
        if manifest.exists():
            for d in json.loads(manifest.read_text()).get('documents',{}).values():
                versions=[v for v in d['versions'] if v.get('valid')]
                counts['valid_originals']+=bool(versions)
                counts['converted']+=any(v.get('conversion')=='CONVERTED' for v in versions)
                counts['pending_ocr']+=bool(versions) and versions[-1].get('conversion')=='FALTA_OCR'
        for p in (root/cuce/'http').glob('*.json'):
            r=json.loads(p.read_text());counts['http_records']+=1
            counts['primary_http_records']+=r.get('mode')=='http_primary'
            counts['compared_records']+=bool(r.get('comparison_performed'))
            counts['matching_http_dom']+=all(r.get('comparison',{}).get(k,False) for k in ('same_visible_text','same_tables'))
            counts['http_errors']+=r['status']>=400
    return counts


def main():
    parser=argparse.ArgumentParser(description='Histórico documental local, basado en el original; sin Supabase')
    parser.add_argument('--entidad',default='0660-10');parser.add_argument('--anio',type=int,default=2024)
    parser.add_argument('--mode',choices=('primary','compare'),default='primary')
    parser.add_argument('--check',action='store_true',help='Solo dependencias; no navegador ni red')
    parser.add_argument('--cuce',action='append',help='Capturar únicamente este CUCE; no altera inventario anual')
    parser.add_argument('--solo-pendientes',action='store_true',help='Reutilizar originales válidos sin reconvertirlos')
    args=parser.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}',args.entidad) or not 2000<=args.anio<=2100:parser.error('Entidad AAAA-BB y gestión válida requeridas')
    if args.cuce and any(not re.fullmatch(re.escape(str(args.anio)[2:]+'-'+args.entidad)+r'-\d+-\d+-\d+',c) for c in args.cuce):parser.error('CUCE fuera de entidad/gestión solicitadas')
    converter=dependencies()
    if args.check:print('Dependencias HTML/DOCX/PDF disponibles. Sin conexiones.');return
    started=time.monotonic();prepare_brave();startup=time.monotonic()-started
    raise SystemExit(asyncio.run(run(args.entidad,args.anio,converter,args.cuce,args.solo_pendientes,args.mode,startup)))

if __name__=='__main__':main()
