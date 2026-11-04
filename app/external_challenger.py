"""V73 external challenger execution layer.
Standardizes license-aware research execution for model-zoo candidates.
No adapter can place paper/live orders or auto-promote a champion.
"""
from __future__ import annotations
from .model_zoo_lab import CATALOG
from .qlib_bridge import FEATURES, adapter_status
from .cross_sectional_ml import current_ranking
from .model_registry import register as register_artifact

PERMISSIVE_LICENSES={'MIT','Apache-2.0','BSD-3-Clause','BSD-2-Clause'}

def _card(candidate_id):
    return next((x for x in CATALOG if x.get('id')==candidate_id),None)

def adapter_catalog():
    st=adapter_status();rows=[]
    for c in CATALOG:
        lic=str(c.get('license') or '')
        license_ok=lic in PERMISSIVE_LICENSES
        if c['id']=='qlib_gbdt':
            ready=license_ok and bool(st.get('lightgbm_installed'))
            reason=None if ready else ('LIGHTGBM_UNAVAILABLE' if license_ok else 'LICENSE_NOT_CLEARED')
            mode='INTERNAL_CONCEPT_REIMPLEMENTATION'
        elif c['id'] in {'qlib_lstm','qlib_transformer'}:
            ready=False;reason='SEQUENCE_ADAPTER_NOT_IMPLEMENTED';mode='MODEL_ARTIFACT_REQUIRED'
        elif lic=='MODEL_CARD_REQUIRED':
            ready=False;reason='MODEL_CARD_AND_LICENSE_REQUIRED';mode='REMOTE_ARTIFACT'
        else:
            ready=False;reason='LICENSE_NOT_CLEARED';mode=c.get('adapter')
        rows.append({'id':c['id'],'name':c['name'],'source':c['source'],'license':lic,
                     'license_ok':license_ok,'ready':ready,'reason':reason,'mode':mode})
    return {'status':'OK','rows':rows,
            'policy':'Only license-cleared adapters may execute in research mode. No external adapter has a broker or production path.'}

def run_candidate(candidate_id,tickers=None,period='5y',limit=120):
    card=_card(candidate_id)
    if not card:return {'status':'UNKNOWN_CANDIDATE','candidate_id':candidate_id}
    lic=str(card.get('license') or '')
    if lic not in PERMISSIVE_LICENSES:
        return {'status':'LICENSE_BLOCK','candidate_id':candidate_id,'license':lic,
                'promotion_status':'RESEARCH_ONLY','live_execution':False}
    if candidate_id!='qlib_gbdt':
        return {'status':'ADAPTER_NOT_READY','candidate_id':candidate_id,'license':lic,
                'reason':'Only qlib_gbdt has a V73 executable research adapter.',
                'promotion_status':'RESEARCH_ONLY','live_execution':False}
    st=adapter_status()
    if not st.get('lightgbm_installed'):
        return {'status':'ADAPTER_UNAVAILABLE','candidate_id':candidate_id,**st,
                'promotion_status':'RESEARCH_ONLY','live_execution':False}
    result=current_ranking(tickers,period,limit)
    if result.get('status')!='OK':
        return {'status':result.get('status'),'candidate_id':candidate_id,'detail':result,
                'promotion_status':'RESEARCH_ONLY','live_execution':False}
    upstream=result.get('model_artifact') or {}
    ext_artifact=register_artifact({
        'model_name':'Qlib GBDT family · BIST concept adapter',
        'model_version':'73.0',
        'seed':56,
        'features':['xs_'+x for x in FEATURES],
        'label':'label_excess_5d',
        'train_rows':result.get('train_rows'),
        'train_dates':None,
        'train_cutoff':None,
        'as_of':result.get('as_of'),
        'symbols':result.get('symbols'),
        'universe_integrity':result.get('universe_integrity'),
        'params':{
            'source':'Qlib','source_url':card.get('source_url'),'license':lic,
            'adapter_mode':'INTERNAL_CONCEPT_REIMPLEMENTATION',
            'upstream_model_fingerprint':upstream.get('model_fingerprint'),
            'neutralization':'V65_FACTORS_SECTOR_IF_AVAILABLE'
        }
    })
    return {'status':'OK','candidate_id':candidate_id,'name':card.get('name'),'source':card.get('source'),
            'license':lic,'adapter_mode':'INTERNAL_CONCEPT_REIMPLEMENTATION',
            'as_of':result.get('as_of'),'symbols':result.get('symbols'),'rows':result.get('rows') or [],
            'current_quality':result.get('current_quality'),'training_quality':result.get('training_quality'),
            'universe_integrity':result.get('universe_integrity'),'neutralization':result.get('neutralization'),
            'upstream_model_artifact':upstream,'external_model_artifact':ext_artifact,
            'promotion_status':'RESEARCH_ONLY','paper_execution_enabled':False,'live_execution':False,
            'policy':'Research output only. V48/V60+ gates and prospective paper evidence remain mandatory before any challenger review.'}
