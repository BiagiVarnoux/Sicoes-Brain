import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import uuid
import sys
import importlib.metadata

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=Path(__file__).resolve().parent


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dumps(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True)
def ident(*parts):return hashlib.sha256(dumps(parts).encode()).hexdigest()


def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temp.open('xb') as fh:fh.write(data);fh.flush();os.fsync(fh.fileno())
    os.replace(temp,path)


def safe_root(path):
    p=Path(path).expanduser().resolve()
    if not p.is_relative_to(ROOT):raise ValueError('La salida debe estar dentro del repositorio')
    if not p.is_relative_to(PACKAGE/'data'):raise ValueError('La salida debe estar dentro de scraper/historico_local/data (ignorado por Git)')
    p.mkdir(parents=True,exist_ok=True);return p


def code_version():
    files={str(p.relative_to(ROOT)):p.read_bytes() for p in sorted(PACKAGE.glob('*.py'))}
    files['scraper/historico_local/schema.sql']=(PACKAGE/'schema.sql').read_bytes()
    files['Correr Sicoes Local.command']=(ROOT/'Correr Sicoes Local.command').read_bytes()
    files['scraper/probe_historico.py']=(ROOT/'scraper/probe_historico.py').read_bytes()
    try:head=subprocess.check_output(['git','--no-optional-locks','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except subprocess.SubprocessError:head='unknown'
    hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    dependencies={}
    for name in ('beautifulsoup4','lxml','playwright','pypdf'):
        try:dependencies[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:dependencies[name]=None
    return {'git_head':head,'python':sys.version,'dependencies':dependencies,'source_hashes':hashes,'code_sha256':ident(hashes,dependencies,sys.version)},files


class Store:
    def __init__(self,root):
        self.root=safe_root(root)
        self.db=sqlite3.connect(self.root/'prueba2.sqlite',timeout=30)
        self.db.row_factory=sqlite3.Row
        self.db.executescript((PACKAGE/'schema.sql').read_text())
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')

    def close(self):self.db.close()

    def artifact(self,data,suffix):
        digest=hashlib.sha256(data).hexdigest();relative=f'objects/{digest[:2]}/{digest}{suffix}'
        old=self.db.execute('SELECT path FROM artifacts WHERE sha256=?',(digest,)).fetchone()
        if old:
            actual=self.root/old['path']
            if not actual.is_file() or hashlib.sha256(actual.read_bytes()).hexdigest()!=digest:raise ValueError('Artefacto previo ausente/corrupto: '+digest)
            return digest,old['path']
        path=self.root/relative
        if not path.exists():atomic(path,data)
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Conflicto de contenido')
        self.db.execute('INSERT OR IGNORE INTO artifacts VALUES(?,?,?)',(digest,relative,len(data)))
        return digest,relative

    def start(self,mode,parameters):
        run=uuid.uuid4().hex;code,files=code_version();self.code=code;self.run=run
        with self.db:
            self.db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)',(run,mode,now(),None,dumps(parameters),dumps(code),'running','not_started',None))
            for name,data in files.items():atomic(self.root/'runs'/run/'code'/name,data)
        self.run_manifest();return run

    def run_manifest(self):
        row=dict(self.db.execute('SELECT * FROM runs WHERE run_id=?',(self.run,)).fetchone())
        row['cuces']=[r[0] for r in self.db.execute('SELECT cuce FROM discoveries WHERE run_id=? ORDER BY cuce',(self.run,))]
        for name in ('parameters_json','code_json','error_json'):
            if row[name]:row[name[:-5]]=json.loads(row[name])
            del row[name]
        atomic(self.root/'runs'/self.run/'manifest.json',(dumps(row)+'\n').encode())

    def finish(self,status,error=None):
        with self.db:self.db.execute('UPDATE runs SET finished_at=?,status=?,error_json=? WHERE run_id=?',(now(),status,dumps(error) if error else None,self.run))
        self.run_manifest()

    def discover(self,meta):
        cuce=meta['cuce'];parts=cuce.split('-')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO processes VALUES(?,?,?)',(cuce,f'{parts[1]}-{parts[2]}',2000+int(parts[0])))
            self.db.execute('INSERT OR REPLACE INTO discoveries VALUES(?,?,?)',(self.run,cuce,dumps(meta)))
        self.process_manifest(cuce)

    def inventory(self,cuce,kind,label,occurrence,availability,metadata):
        did=ident(cuce,kind,label,occurrence)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO documents VALUES(?,?,?,?,?)',(did,cuce,kind,label,occurrence))
            self.db.execute('INSERT OR REPLACE INTO document_inventory VALUES(?,?,?,?)',(self.run,did,availability,dumps(metadata)))
        self.process_manifest(cuce);return did

    def begin_attempt(self,did,metadata):
        aid=uuid.uuid4().hex
        with self.db:self.db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (aid,self.run,did,now(),None,'interrupted_or_running',None,'pending','not_attempted','not_attempted','[]',dumps(metadata)))
        return aid

    def end_attempt(self,aid,*,outcome,version_id=None,capture='not_captured',conversion='not_attempted',parse='not_attempted',errors=None,metadata=None):
        with self.db:
            old=self.db.execute('SELECT metadata_json,document_id FROM attempts WHERE attempt_id=?',(aid,)).fetchone()
            merged=json.loads(old['metadata_json']);merged.update(metadata or {})
            self.db.execute('UPDATE attempts SET finished_at=?,outcome=?,version_id=?,capture_status=?,conversion_status=?,parse_status=?,errors_json=?,metadata_json=? WHERE attempt_id=?',
                (now(),outcome,version_id,capture,conversion,parse,dumps(errors or []),dumps(merged),aid))
        cuce=self.db.execute('SELECT cuce FROM documents WHERE document_id=?',(old['document_id'],)).fetchone()[0]
        self.process_manifest(cuce)

    def process_manifest(self,cuce):
        docs=[]
        for d in self.db.execute('SELECT * FROM documents WHERE cuce=? ORDER BY kind,label,occurrence',(cuce,)):
            item=dict(d)
            item['inventory']=[dict(x) for x in self.db.execute('SELECT run_id,availability,metadata_json FROM document_inventory WHERE document_id=?',(d['document_id'],))]
            item['versions']=[dict(x) for x in self.db.execute('SELECT v.*,a.path FROM document_versions v JOIN artifacts a ON a.sha256=v.raw_sha256 WHERE document_id=?',(d['document_id'],))]
            item['attempts']=[dict(x) for x in self.db.execute('SELECT * FROM attempts WHERE document_id=? ORDER BY started_at',(d['document_id'],))]
            item['parses']=[dict(x) for x in self.db.execute('SELECT p.* FROM parses p JOIN document_versions v USING(version_id) WHERE v.document_id=?',(d['document_id'],))]
            for parsed in item['parses']:
                for key in ('structured','markdown'):
                    value=parsed[key+'_sha256']
                    parsed[key+'_path']=self.db.execute('SELECT path FROM artifacts WHERE sha256=?',(value,)).fetchone()[0] if value else None
            item['has_preserved_success']=any(x['status'] in ('PARSED','CAPTURED_NO_RECORDS','CONVERTED') for x in item['parses'])
            docs.append(item)
        atomic(self.root/'processes'/cuce/'manifest.json',(dumps({'cuce':cuce,'documents':docs})+'\n').encode())

    def reusable(self,did):
        row=self.db.execute("SELECT p.*,v.raw_sha256 FROM parses p JOIN document_versions v USING(version_id) WHERE v.document_id=? AND v.validation_status='valid' AND p.parser_version=? AND p.status IN ('PARSED','CONVERTED','CAPTURED_NO_RECORDS') ORDER BY p.rowid DESC LIMIT 1",(did,self.code['code_sha256'])).fetchone()
        if not row:return None
        for key in ('raw_sha256','structured_sha256','markdown_sha256'):
            if row[key]:
                artifact=self.db.execute('SELECT path FROM artifacts WHERE sha256=?',(row[key],)).fetchone()
                if not artifact or hashlib.sha256((self.root/artifact['path']).read_bytes()).hexdigest()!=row[key]:
                    raise ValueError('Evidencia previa corrupta; no declarar reanudación exitosa')
        return dict(row)

    def summary(self):
        counts={r[0]:r[1] for r in self.db.execute('SELECT outcome,count(*) FROM attempts WHERE run_id=? GROUP BY outcome',(self.run,))}
        eligible=sum(json.loads(r[0]).get('eligible',True) for r in self.db.execute('SELECT metadata_json FROM discoveries WHERE run_id=?',(self.run,)))
        published=self.db.execute("SELECT count(*) FROM document_inventory WHERE run_id=? AND availability='published'",(self.run,)).fetchone()[0]
        valid_captured=self.db.execute("SELECT count(DISTINCT a.document_id) FROM attempts a JOIN document_versions v USING(version_id) WHERE a.run_id=? AND v.validation_status='valid' AND a.outcome NOT LIKE 'FAILED%' AND a.outcome!='interrupted_or_running'",(self.run,)).fetchone()[0]
        return {'run_id':self.run,'outcomes':counts,'eligible_discovered':eligible,'published_documents_this_run':published,'validated_documents_this_run':valid_captured,'discovered':self.db.execute('SELECT count(*) FROM discoveries WHERE run_id=?',(self.run,)).fetchone()[0],
            'document_versions_total':self.db.execute('SELECT count(*) FROM document_versions').fetchone()[0],
            'original_rows_total':self.db.execute('SELECT count(*) FROM observations').fetchone()[0],
            'current_code_item_rows':self.db.execute('SELECT sum(item_rows) FROM parses WHERE parser_version=?',(self.code['code_sha256'],)).fetchone()[0] or 0,
            'parsed_item_rows_total':self.db.execute('SELECT sum(item_rows) FROM parses').fetchone()[0] or 0,
            'note':'Totales preservados de todas las versiones; no son productos únicos ni demanda fusionada.'}
