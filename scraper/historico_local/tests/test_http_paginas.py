import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock,Mock,patch
from scraper.historico_local import historico_http_paginas as h
from scraper.historico_local.storage import PACKAGE


def cuce(n):return f'24-0660-10-{1400000+n}-1-1'
def row(n):return {'cuce':cuce(n),'modalidad':'CM','forms':[],'archivos':[]}
def state(ids,total=3,number=1):
    return {'table_present':True,'raw_cuces':[cuce(n) for n in ids],
            'info':f'Se han encontrado {total} registros' if total is not None else '',
            'table_text':'contenido' if ids else 'No hay datos registrados','active_page':number}

class PageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        (PACKAGE/'data/tests').mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=PACKAGE/'data/tests');self.root=Path(self.tmp.name)
        self.net=patch('socket.socket.connect',side_effect=AssertionError('Sin conexiones'));self.net.start()
        self.page=Mock();self.page.current=1;self.page.wait_for_timeout=AsyncMock();self.page.wait_for_function=AsyncMock()
        self.events=[]
    async def asyncTearDown(self):self.net.stop();self.tmp.cleanup()
    def nav(self,rows):
        async def change(page,number):page.current=number;self.events.append(('page',number))
        async def extract(page,entity):return rows.get(page.current,[])
        return {'ir_pagina':AsyncMock(side_effect=change),'extraer_filas':AsyncMock(side_effect=extract),
                'keepalive':AsyncMock(return_value=True),'ir_a_buscador':AsyncMock(),'buscar':AsyncMock()}
    async def process(self,page,r,root,nav,conv):
        self.events.append(('process',r['cuce'],page.current))
        p=root/r['cuce']/'manifest.json';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({'status':'FALTA_OCR','documents':{},'needs_navigation_recovery':False}))
        return True
    def test_calculates_pages_from_observed_size(self):
        meta=h.pagination(state(range(10),1692));self.assertEqual(meta['page_size'],10);self.assertEqual(meta['expected_pages'],170)
        self.assertIsNone(h.pagination(state(range(10),None))['expected_pages'])
    def test_real_sanitized_dom_has_distinct_totals(self):
        from bs4 import BeautifulSoup
        p=Path('/Users/fabriziocuellar/Downloads/SICOES_Buscador_Avanzado_Sanitizado.html')
        if not p.exists():self.skipTest('DOM local no disponible')
        soup=BeautifulSoup(p.read_bytes(),'lxml')
        info=soup.select_one('#tablaAvanzada_paginate .dataTables_info').get_text()
        raw=soup.select('#tablaAvanzada > tbody > tr')
        data={'info':info,'raw_cuces':[str(n) for n in range(len(raw))]}
        self.assertEqual(h.pagination(data)['registered_total'],1692)
        self.assertEqual(h.pagination(data)['expected_pages'],170)
    async def test_processes_page_before_advancing_without_return_trip(self):
        nav=self.nav({1:[row(1),row(2)],2:[row(3)]})
        async def snap(page):return state([1,2] if page.current==1 else [3],3,page.current)
        with patch.object(h,'snapshot',side_effect=snap),patch.object(h.base,'process',side_effect=self.process):
            results=await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root)
        self.assertEqual(len(results),3)
        self.assertEqual(self.events,[('process',cuce(1),1),('process',cuce(2),1),('page',2),('process',cuce(3),2)])
        nav['keepalive'].assert_not_awaited()
        inventory=json.loads((self.root/'inventario_paginas.json').read_text())
        self.assertEqual(inventory['termination'],'registered_total_verified');self.assertEqual(inventory['registered_seen'],3)
    async def test_no_eligible_rows_on_first_page_does_not_end_search(self):
        nav=self.nav({1:[],2:[row(20)]})
        async def snap(page):return state(range(1,11) if page.current==1 else range(11,21),20,page.current)
        with patch.object(h,'snapshot',side_effect=snap),patch.object(h.base,'process',side_effect=self.process):
            results=await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root,[cuce(20)])
        self.assertEqual(list(results),[cuce(20)]);nav['ir_pagina'].assert_awaited_once_with(self.page,2)
    async def test_selected_scope_stops_without_scanning_rest(self):
        nav=self.nav({1:[row(1),row(2),row(3)]})
        with patch.object(h,'snapshot',new=AsyncMock(return_value=state(range(1,11),100))),patch.object(h.base,'process',side_effect=self.process):
            results=await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root,[cuce(2)])
        self.assertEqual(list(results),[cuce(2)]);nav['ir_pagina'].assert_not_awaited()
        self.assertEqual(json.loads((self.root/'inventario_paginas.json').read_text())['termination'],'selected_scope_completed')
    async def test_duplicate_pages_fail_instead_of_looping(self):
        nav=self.nav({1:[row(1)],2:[row(1)],3:[row(1)]})
        async def snap(page):return state([1,2],6,page.current)
        with patch.object(h,'snapshot',side_effect=snap),patch.object(h.base,'process',side_effect=self.process):
            with self.assertRaisesRegex(h.base.RecoveryRequired,'sin avance'):await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root)
        self.assertEqual(sum(e[0]=='process' for e in self.events),1)
    async def test_recovery_reopens_only_current_page_once(self):
        nav=self.nav({1:[row(1)]});calls=[]
        async def process(*args):
            calls.append(True);await self.process(*args)
            p=self.root/cuce(1)/'manifest.json';m=json.loads(p.read_text());m['needs_navigation_recovery']=True;p.write_text(json.dumps(m))
            return len(calls)>1
        with patch.object(h,'snapshot',new=AsyncMock(return_value=state([1],1))),patch.object(h.base,'process',side_effect=process):
            results=await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root,[cuce(1)])
        self.assertEqual(len(calls),2);nav['keepalive'].assert_awaited_once();nav['buscar'].assert_awaited_once()
        nav['ir_pagina'].assert_awaited_once_with(self.page,1)
        self.assertEqual(results[cuce(1)],'FALTA_OCR')
    async def test_missing_table_is_not_end_of_results(self):
        self.page.evaluate=AsyncMock(return_value={'table_present':False})
        with self.assertRaises(h.base.RecoveryRequired):await h.snapshot(self.page)
    async def test_changed_total_stops_without_claiming_complete(self):
        nav=self.nav({1:[row(1),row(2)]})
        async def snap(page):return state([1,2] if page.current==1 else [3],3 if page.current==1 else 4,page.current)
        with patch.object(h,'snapshot',side_effect=snap),patch.object(h.base,'process',side_effect=self.process):
            with self.assertRaisesRegex(h.base.RecoveryRequired,'Cambió el total'):await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root)

    def test_progress_does_not_invent_unseen_eligible_total(self):
        self.assertIn('1/?',h.progress(1,{'a','b'},set(),None,False))
        self.assertIn('1/19',h.progress(1,{'a'},set(),set(map(str,range(19))),False))
        self.assertIn('referencia',h.progress(1,{'a'},set(),{'a','b'},False))
        self.assertEqual(h.progress(3,{'a','b','c'},set(),None,True),'[3/3 elegibles]')
    async def test_prior_inventory_progress_and_exclusions_once_per_page(self):
        import io
        from contextlib import redirect_stdout
        prior={'entity':'0660-10','year':2024,'termination':'registered_total_verified','registered_total':3,'eligible_discovered':3,'filters':{'type':'Bienes','state':'2C','modalities':['CM','ANPE','ANPP','LP']},'pages':[{'eligible_cuces':[cuce(1),cuce(2),cuce(3)]}]}
        (self.root/'inventario_paginas.json').write_text(json.dumps(prior))
        nav=self.nav({1:[row(1),row(2)],2:[row(3)]})
        async def snap(page):return state([1,2] if page.current==1 else [3],3,page.current)
        output=io.StringIO()
        with redirect_stdout(output),patch.object(h,'snapshot',side_effect=snap),patch.object(h.base,'process',side_effect=self.process):
            await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root)
        self.assertIn('[1/3 elegibles; referencia',output.getvalue());self.assertIn('[3/3 elegibles]',output.getvalue())
    async def test_repeated_legacy_skip_message_is_quiet_without_filter_change(self):
        import io
        from contextlib import redirect_stdout
        nav=h.base.original_functions();h.quiet_exclusion_logging(nav)
        page=Mock();page.evaluate=AsyncMock(return_value=[{'cuce':cuce(1),'estado':'Contratado','modalidad':'CND1'},{'cuce':cuce(2),'estado':'Contratado','modalidad':'CM'}])
        output=io.StringIO()
        with redirect_stdout(output):
            a=await nav['extraer_filas'](page,'0660-10');b=await nav['extraer_filas'](page,'0660-10')
        self.assertEqual([r['cuce'] for r in a],[cuce(2)]);self.assertEqual(a,b)
        self.assertNotIn('saltando',output.getvalue())
    async def test_excluded_cuce_inventory_and_single_page_notice(self):
        import io
        from contextlib import redirect_stdout
        nav=self.nav({1:[row(1)]});output=io.StringIO()
        with redirect_stdout(output),patch.object(h,'snapshot',new=AsyncMock(return_value=state([1,2],2))),patch.object(h.base,'process',side_effect=self.process):
            await h.walk(self.page,'0660-10',2024,Mock(),nav,self.root)
        self.assertEqual(output.getvalue().count('Fuera de filtros'),1)
        inventory=json.loads((self.root/'inventario_paginas.json').read_text())
        self.assertEqual(inventory['pages'][0]['excluded_cuces'],[cuce(2)])


class PageLauncherTests(unittest.TestCase):
    def test_check_and_full_year_scope(self):
        import os,subprocess
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);fake=root/'python';trace=root/'calls'
            fake.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$PAGE_TEST_TRACE"\n');fake.chmod(0o700)
            env=dict(os.environ,SICOES_LOCAL_PYTHON=str(fake),PAGE_TEST_TRACE=str(trace))
            launcher=h.base.ROOT/'Correr Sicoes Local.command'
            result=subprocess.run([str(launcher),'--check'],env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0);self.assertIn('scraper.historico_local --check',trace.read_text())
            trace.write_text('');result=subprocess.run([str(launcher)],input='0660-10\n2024\n',env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0);self.assertNotIn('--cuce',trace.read_text());self.assertIn('--anio 2024',trace.read_text())
    def test_launcher_keeps_multiple_years_and_ranges(self):
        import os,subprocess
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);fake=root/'python';trace=root/'calls'
            fake.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$PAGE_TEST_TRACE"\n');fake.chmod(0o700)
            env=dict(os.environ,SICOES_LOCAL_PYTHON=str(fake),PAGE_TEST_TRACE=str(trace))
            launcher=h.base.ROOT/'Correr Sicoes Local.command'
            result=subprocess.run([str(launcher)],input='0660-10\n2022-2024 2023\n',env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0)
            commands=trace.read_text().splitlines();self.assertEqual(len(commands),3)
            self.assertEqual([c.split('--anio ')[1] for c in commands],['2022','2023','2024'])
            self.assertNotIn('--cuce',trace.read_text())

