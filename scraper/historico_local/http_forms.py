"""Variante de observación HTTP; no importa ni modifica historico_local.
Por defecto solo analiza un HAR local. No inicia navegador ni peticiones.
"""
import argparse
import asyncio
import base64
from collections import Counter
import json
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from .parsing import validate


def endpoint(url):
    u=urlsplit(url)
    return u.hostname=='www.sicoes.gob.bo' and u.path.endswith('/verFormulario.php')


def extract_html(body):
    obj=json.loads(body)
    # En el HAR observado, data.data JS significa respuesta['data'].
    if not isinstance(obj,dict) or not isinstance(obj.get('data'),str):
        raise ValueError('Contrato JSON distinto del observado: data debe ser texto')
    return obj['data']


def signature(html):
    soup=BeautifulSoup(html,'lxml')
    for node in soup(['script','style']):node.decompose()
    # Se conserva orden, duplicados, tablas y todas sus celdas.
    tables=[[[" ".join(c.stripped_strings) for c in tr.find_all(['td','th'],recursive=False)]
             for tr in t.find_all('tr') if tr.find_parent('table') is t] for t in soup.find_all('table')]
    return {'text':' '.join(soup.stripped_strings),'tables':tables}


def compare(http_html,dom_html):
    a,b=signature(http_html),signature(dom_html)
    return {'same_visible_text':a['text']==b['text'],'same_tables':a['tables']==b['tables'],
            'http_tables':len(a['tables']),'dom_tables':len(b['tables'])}


async def capture_once(page,open_modal,close_modal,cuce,kind,timeout_ms=30000):
    """Observación de UNA apertura normal. Sin reintentos ni KEEPALIVE preventivo.
    El llamador conserva versiones y decide recuperación reactiva; esta función
    nunca genera tokens ni peticiones independientes.
    """
    opening=None;result=None
    try:
        async with page.expect_response(lambda r:endpoint(r.url),timeout=timeout_ms) as event:
            opening=asyncio.create_task(open_modal())
            await asyncio.sleep(0)
        response=await event.value
        body=await asyncio.wait_for(response.body(),timeout_ms/1000)
        result={'status':response.status,'raw_body':body,'dom_html':''}
        if response.status>=400:
            result.update(valid=False,recovery_reason='http_server_error' if response.status>=500 else 'http_client_error')
            return result
        try:dom_html=await asyncio.wait_for(opening,timeout_ms/1000)
        except Exception as exc:
            result.update(valid=False,error=type(exc).__name__,recovery_reason='dom_timeout' if type(exc).__name__=='TimeoutError' else None)
            return result
        result['dom_html']=dom_html
        try:html=extract_html(body)
        except (ValueError,TypeError,UnicodeDecodeError):
            result.update(valid=False,recovery_reason=None,error='unexpected_json_contract');return result
        checked=validate(html.encode(),kind,cuce)
        result.update(http_html=html,valid=checked['valid'],validation=checked,comparison=compare(html,dom_html),recovery_reason=None)
        return result
    finally:
        if opening is not None:
            if not opening.done():opening.cancel()
            await asyncio.gather(opening,return_exceptions=True)
        try:await close_modal()
        except Exception as exc:
            if result is None:raise
            result['close_error']=type(exc).__name__


def analyze_har(path,originals=None):
    counts=Counter();comparisons=Counter()
    local=[]
    if originals:
        for p in Path(originals).glob('*/crudos/*.html'):
            local.append(signature(p.read_bytes()))
    entries=json.loads(Path(path).read_text())['log']['entries']
    for entry in entries:
        if not endpoint(entry['request']['url']):continue
        response=entry['response'];counts['requests']+=1;counts['http_'+str(response['status'])]+=1
        content=response.get('content',{});body=content.get('text')
        if body is None:counts['body_unavailable']+=1;continue
        counts['body_available']+=1
        try:
            if content.get('encoding')=='base64':body=base64.b64decode(body)
            html=extract_html(body)
        except (ValueError,TypeError,UnicodeDecodeError):counts['unexpected_contract']+=1;continue
        counts['json_data_html']+=1
        sig=signature(html)
        counts['html_with_tables']+=bool(sig['tables'])
        if originals:
            comparisons['same_text_and_tables_as_local']+=any(sig==s for s in local)
            comparisons['no_exact_local_match']+=not any(sig==s for s in local)
    # Salida agregada: no encabezados, cuerpos, argumentos ni tokens.
    return {'counts':dict(counts),'comparison':dict(comparisons),'local_originals_compared':len(local),
            'limitations':['Solo se comparan respuestas cuyo cuerpo está presente en el HAR.',
                            'Coincidencia textual no demuestra que se puedan repetir peticiones sin abrir el modal.',
                            'No hay ejecución de navegador ni política de recuperación integrada en este analizador.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--har',required=True,type=Path)
    parser.add_argument('--originals',type=Path)
    args=parser.parse_args()
    print(json.dumps(analyze_har(args.har,args.originals),ensure_ascii=False,indent=2))


if __name__=='__main__':main()


async def capture_primary(page,trigger,close_modal,cuce,kind,timeout_ms=30000,before_close=None):
    """Fuente HTTP primaria: flujo normal del portal, sin leer ni esperar el DOM."""
    import time
    started=time.monotonic();result=None;timings={}
    try:
        async with page.expect_response(lambda r:endpoint(r.url),timeout=timeout_ms) as event:
            await trigger()
        response=await event.value
        timings['response_headers_seconds']=round(time.monotonic()-started,6)
        mark=time.monotonic()
        body=await asyncio.wait_for(response.body(),timeout_ms/1000)
        timings['body_seconds']=round(time.monotonic()-mark,6)
        result={'status':response.status,'raw_body':body,'mode':'http_primary','comparison_performed':False}
        if response.status>=400:
            result.update(valid=False,recovery_reason='http_server_error' if response.status>=500 else 'http_client_error')
            return result
        mark=time.monotonic()
        try:html=extract_html(body)
        except (ValueError,TypeError,UnicodeDecodeError):
            result.update(valid=False,recovery_reason=None,error='unexpected_json_contract');return result
        checked=validate(html.encode(),kind,cuce)
        result.update(http_html=html,valid=checked['valid'],validation=checked,recovery_reason=None)
        timings['validation_seconds']=round(time.monotonic()-mark,6)
        return result
    finally:
        if before_close is not None and result is not None and result.get('valid'):
            mark=time.monotonic()
            try:await before_close()
            except Exception as exc:result['close_error']=type(exc).__name__
            timings['modal_ready_seconds']=round(time.monotonic()-mark,6)
        mark=time.monotonic()
        try:await close_modal()
        except Exception as exc:
            if result is None:raise
            result['close_error']=type(exc).__name__
        finally:
            timings['close_seconds']=round(time.monotonic()-mark,6)
            timings['total_seconds']=round(time.monotonic()-started,6)
            if result is not None:result['timings']=timings
