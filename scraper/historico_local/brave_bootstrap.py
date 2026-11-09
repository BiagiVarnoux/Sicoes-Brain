"""Preparación opt-in de Brave exclusivo. El modo local jamás llama este módulo.
Se verifica propietario del puerto ANTES de consultar /json/version.
"""
import argparse
import errno
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import uuid

from .storage import PACKAGE,safe_root,atomic,dumps,now

PORT=9226
ENDPOINT='http://127.0.0.1:9226'
BRAVE=Path('/Applications/Brave Browser.app/Contents/MacOS/Brave Browser')
PORTAL='https://www.sicoes.gob.bo/portal/index.php'


class PreparationError(RuntimeError):pass


def profile_path():
    data=safe_root(PACKAGE/'data');profile=data/'brave-historico-http'
    if profile.is_symlink() or (profile.exists() and not profile.is_dir()):
        raise PreparationError('El perfil exclusivo no puede ser un enlace ni un archivo.')
    return profile.resolve()


def require_endpoint(endpoint):
    p=urlsplit(endpoint)
    if p.scheme!='http' or p.hostname not in ('127.0.0.1','localhost') or p.port!=PORT or p.username or p.password or p.query or p.fragment or p.path not in ('','/'):
        raise PreparationError('Esta captura histórica utiliza exclusivamente HTTP local, puerto 9226.')


def listeners():
    binary=shutil.which('lsof')
    if not binary:raise PreparationError('No se encontró lsof: no es posible verificar el propietario de 9226.')
    r=subprocess.run([binary,'-nP',f'-iTCP:{PORT}','-sTCP:LISTEN','-t'],capture_output=True,text=True,timeout=5)
    if r.returncode not in (0,1):raise PreparationError('No se pudo inspeccionar el puerto 9226; no se conectará.')
    return sorted({int(line) for line in r.stdout.splitlines() if line.strip().isdigit()})


def port_is_occupied():
    # Bind de diagnóstico local; no conecta a ningún servicio.
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        try:s.bind(('127.0.0.1',PORT));return False
        except OSError as exc:
            if exc.errno==errno.EADDRINUSE:return True
            raise PreparationError('No se pudo comprobar si 9226 está libre.') from None


def process_identity(pid):
    lsof=shutil.which('lsof')
    if not lsof:raise PreparationError('Falta lsof para verificar el ejecutable.')
    executable=subprocess.run([lsof,'-a','-p',str(pid),'-d','txt','-Fn'],capture_output=True,text=True,timeout=5)
    args=subprocess.run(['/bin/ps','-ww','-p',str(pid),'-o','args='],capture_output=True,text=True,timeout=5)
    if executable.returncode or args.returncode:raise PreparationError('No se pudo identificar el proceso que escucha en 9226.')
    paths=[line[1:] for line in executable.stdout.splitlines() if line.startswith('n')]
    return paths,args.stdout.strip()


def command_matches(command,profile):
    # ps devuelve argv unido: se compara el valor completo conocido, con límites.
    if command.count('--user-data-dir')!=1 or command.count('--remote-debugging-port')!=1:return False
    port=re.search(r'(?:^|\s)--remote-debugging-port(?:=|\s+)9226(?=\s|$)',command)
    path=re.escape(str(profile))
    userdir=re.search(r'(?:^|\s)--user-data-dir(?:=|\s+)(?:'+path+r'|"'+path+r'"|\x27'+path+r'\x27)(?=\s|$)',command)
    return bool(port and userdir)


def authorize_listener(pids,profile):
    if not pids:raise PreparationError('No se identificó un navegador autorizado en 9226.')
    for pid in pids:
        paths,args=process_identity(pid)
        if not any(Path(p).resolve()==BRAVE.resolve() for p in paths) or not command_matches(args,profile):
            raise PreparationError('9226 está ocupado por otro navegador, perfil o servicio. No se reutilizó ni se cerró ese proceso.')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def fetch_version():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(ENDPOINT+'/json/version',timeout=2) as response:
        if response.status!=200:raise PreparationError('/json/version no devolvió HTTP 200.')
        data=response.read(65537)
    if len(data)>65536:raise PreparationError('Respuesta CDP demasiado grande.')
    obj=json.loads(data)
    if not isinstance(obj,dict):raise PreparationError('/json/version no devolvió un objeto JSON válido.')
    ws=urlsplit(obj.get('webSocketDebuggerUrl',''))
    if not isinstance(obj.get('Browser'),str) or not obj['Browser'].startswith(('Chrome/','Chromium/','HeadlessChrome/')) or ws.scheme!='ws' or ws.hostname not in ('127.0.0.1','localhost') or ws.port!=PORT or not ws.path.startswith('/devtools/browser/') or ws.username or ws.password or ws.query or ws.fragment:
        raise PreparationError('El servicio en 9226 no devuelve un endpoint CDP Chromium válido.')
    return {'browser':obj['Browser'],'protocol_version':obj.get('Protocol-Version')}


def verify_ready(endpoint=ENDPOINT):
    require_endpoint(endpoint);profile=profile_path();pids=listeners()
    authorize_listener(pids,profile)
    result=fetch_version()
    return dict(result,endpoint=ENDPOINT,profile=str(profile),listener_pids=pids)


def spawn(profile,logpath,open_portal):
    if not BRAVE.is_file():raise PreparationError('Brave no está instalado en /Applications/Brave Browser.app.')
    profile.mkdir(parents=True,exist_ok=True)
    with Path(logpath).open('ab') as log:
        return subprocess.Popen([str(BRAVE),f'--remote-debugging-port={PORT}',f'--user-data-dir={profile}',
             PORTAL if open_portal else 'about:blank'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)


def prepare(timeout=120):
    folder=safe_root(PACKAGE/'data/browser_bootstrap');record_path=folder/(uuid.uuid4().hex+'.json')
    record={'started_at':now(),'endpoint':ENDPOINT,'status':'preparing','capture_started':False}
    atomic(record_path,(dumps(record)+'\n').encode())
    try:
        profile=profile_path();record['profile']=str(profile)
        pids=listeners()
        if pids:
            # Puerto ajeno: fallar ANTES de hacer GET o abrir el portal.
            authorize_listener(pids,profile)
        elif port_is_occupied():
            raise PreparationError('9226 está ocupado y no se pudo verificar su propietario; no se conectará.')
        else:
            print('Abriendo Brave exclusivo en 9226; esperando disponibilidad (hasta 120 s)...',flush=True)
            log=folder/(record_path.stem+'_brave.log')
            child=spawn(profile,log,True);record.update(launched_pid=child.pid,browser_log=str(log))
        deadline=time.monotonic()+timeout
        while True:
            current=listeners()
            if current:
                authorize_listener(current,profile)
                try:
                    ready=fetch_version();break
                except (OSError,ValueError,PreparationError):pass
            if time.monotonic()>=deadline:
                raise PreparationError('Brave no quedó listo en 9226. Revisá el log y si el perfil exclusivo ya está abierto en otro puerto. No se ejecutó el scraper.')
            print('Esperando Brave y /json/version...',flush=True);time.sleep(1)
        # El endpoint se verifica antes de dirigir el portal a una instancia reutilizada.
        if pids:
            spawn(profile,folder/(record_path.stem+'_portal.log'),True)
        record.update(status='ready',finished_at=now(),listener_pids=current,**ready)
        atomic(record_path,(dumps(record)+'\n').encode())
        print('Brave verificado: puerto 9226 y perfil exclusivo correctos.',flush=True)
        print('Se solicitó abrir el portal SICOES en ese perfil. Si no aparece, abrilo allí manualmente: '+PORTAL,flush=True)
        return record
    except BaseException as exc:
        record.update(status='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',finished_at=now(),error_type=type(exc).__name__,error=str(exc) if isinstance(exc,PreparationError) else 'Falló la preparación; revisar el log local.')
        atomic(record_path,(dumps(record)+'\n').encode())
        raise


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare'])
    p.parse_args()
    try:prepare()
    except (PreparationError,OSError,ValueError,subprocess.SubprocessError) as exc:
        if isinstance(exc,PreparationError):print('ERROR: '+str(exc),flush=True)
        print('ERROR: no se pudo preparar Brave autorizado. Revisá scraper/historico_local/data/browser_bootstrap/ y el log del lanzador; no se iniciará la captura.',flush=True)
        raise SystemExit(2)

if __name__=='__main__':main()
