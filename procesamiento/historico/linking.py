"""Asociaciones documentales dentro de CUCE; no equivalencia entre productos."""
from collections import Counter
import re
from decimal import Decimal
from .parser import norm,unique_field
from .technical import codes

STOP=set('de del la las el los para por y o en a al un una bien bienes servicio servicios toner tonner impresora impresoras fax marca modelo tipo equipo equipos'.split())
def tokens(text):return set(re.findall(r'[a-z0-9]+',norm(text)))-STOP

def subtype(text):
    n=norm(text)
    if 'escaner' in n:return 'escaner'
    if 'toner' in n or 'tonner' in n:return 'toner'
    if 'matricial' in n:return 'matricial'
    if 'termica' in n:return 'termica'
    if 'computacion' in n or 'computador' in n:return 'computador'
    if 'impresora' in n:return 'impresora'
    return None


def unit_key(value):
    n=norm(value or '')
    groups={'pieza':{'pieza','piezas','pza','pzas','unidad','unidades'},'caja':{'caja','cajas','cajita','cajitas'},
            'paquete':{'paquete','paquetes'},'rollo':{'rollo','rollos'},'tubo':{'tubo','tubos'}}
    return next((key for key,aliases in groups.items() if n in aliases),None)


def candidate(spec,observation):
    if spec['cuce']!=observation['cuce']:return None
    a=tokens(spec['title']);b=tokens(observation['description_visible']);common=a&b
    containment=len(common)/max(1,min(len(a),len(b)))
    ca={c['value'] for c in codes(spec['title'])};cb={c['value'] for c in codes(observation['description_visible'])}
    field=unique_field(observation['fields'],'cantidad');n=unique_field(observation['fields'],'nro_item_documento')
    quantity_match=field is not None and field['normalized'].get('value') is not None and spec['quantity'] is not None and Decimal(field['normalized']['value'])==Decimal(spec['quantity'])
    quantity_conflict=field is not None and field['normalized'].get('value') is not None and spec['quantity'] is not None and not quantity_match
    unit_field=unique_field(observation['fields'],'unidad_medida')
    unit_form=unit_field['visible'] if unit_field else None;unit_dbc=spec.get('unit')
    unit_conflict=bool(unit_key(unit_form) and unit_key(unit_dbc) and unit_key(unit_form)!=unit_key(unit_dbc))
    lot=unique_field(observation['fields'],'lote_documentado')
    lot_form=lot['visible'] if lot else None;lot_dbc=spec.get('lot')
    lot_conflict=bool(lot_form and lot_dbc and lot_form!=lot_dbc)
    number_match=n is not None and n['visible']==spec['number']
    ta,tb=subtype(spec['title']),subtype(observation['description_visible']);type_match=ta is not None and ta==tb
    type_conflict=ta is not None and tb is not None and ta!=tb and 'impresora' not in (ta,tb)
    code_conflict=bool(ca and cb and not ca&cb)
    shared_codes=sorted(ca&cb)
    score=round(.5*containment+.25*bool(shared_codes)+.15*quantity_match+.10*number_match+.1*type_match,6)
    anchor=bool(shared_codes) or len(common)>=2 and containment>=.75 or type_match and ta in ('escaner','matricial','termica')
    eligible=anchor and not (code_conflict or type_conflict or quantity_conflict or unit_conflict or lot_conflict or len(ca)>1 or len(cb)>1) and (quantity_match or number_match)
    return {'observation_id':observation['observation_id'],'score':score,'confirmation_supported':eligible,
            'evidence':{'cuce_equal':True,'description_tokens_shared':sorted(common),'description_containment':round(containment,4),
                        'unit_form':unit_form,'unit_dbc':unit_dbc,'unit_conflict':unit_conflict,'quantity_dbc':spec['quantity'],'quantity_form':field['normalized'].get('value') if field else None,'lote_dbc':lot_dbc,'lote_form':lot_form,'lot_conflict':lot_conflict,'catalog_code_form':(unique_field(observation['fields'],'codigo_catalogo') or {}).get('visible'),'section_form':observation['section'],'section_dbc':spec.get('source_section'),'codes_shared':shared_codes,'codes_dbc':sorted(ca),'codes_form':sorted(cb),'quantity_equal':quantity_match,
                        'number_equal':number_match,'type_dbc':ta,'type_form':tb,'code_conflict':code_conflict,'type_conflict':type_conflict,'quantity_conflict':quantity_conflict},
            'form_reference':{'document_id':observation['document_id'],'path':observation['source_path'],'sha256':observation['source_sha256'],
                              'table':observation['table_position'],'row':observation['row_position']}}


def link(specs,observations):
    req=[o for o in observations if o['stage']=='requerimiento'];relations=[]
    for spec in specs:
        candidates=sorted([c for o in req if (c:=candidate(spec,o)) is not None and c['score']>=.25],key=lambda c:(-c['score'],c['observation_id']))
        top=candidates[0] if candidates else None
        margin=round(top['score']-candidates[1]['score'],6) if len(candidates)>1 else 1
        confirmed=top is not None and top['confirmation_supported'] and margin>=.12
        relations.append({'spec_id':spec['spec_id'],'cuce':spec['cuce'],'status':'CONFIRMADA' if confirmed else 'AMBIGUA' if candidates else 'SIN_CORRESPONDENCIA',
                          'observation_id':top['observation_id'] if confirmed else None,'best_candidate_id':top['observation_id'] if top else None,
                          'margin':margin,'candidates':candidates,'spec_reference':{'original_path':spec['original_path'],'sha256':spec['original_sha256'],'table':spec['table'],'row':spec['row'],'number':spec['number']},
                          'reason':'Evidencia documental conjunta y candidato único; no confirma identidad comercial' if confirmed else 'Evidencia insuficiente, contradictoria o sin margen; no se aplica enriquecimiento' if candidates else 'Sin candidato con evidencia suficiente'})
    assigned=Counter(r['observation_id'] for r in relations if r['status']=='CONFIRMADA')
    for r in relations:
        if r['status']=='CONFIRMADA' and assigned[r['observation_id']]>1:
            r.update(status='AMBIGUA',observation_id=None,reason='Varios conjuntos DBC reclaman la misma observación; no se resuelve automáticamente')
    return relations
