"""V48 external model zoo / challenger lab.
External models are metadata-only candidates until they pass reproducibility,
causality, robustness, execution, licensing and prospective-forward gates.
No external model can place live orders or silently replace the champion.
"""
from __future__ import annotations
import time

CATALOG=[
 {'id':'qlib_gbdt','name':'Qlib GBDT family','source':'Qlib','source_url':'https://github.com/microsoft/qlib','license':'MIT',
  'adapter':'TABULAR_SUPERVISED','data_requirements':['OHLCV','point-in-time features'],'status':'RESEARCH_CANDIDATE'},
 {'id':'qlib_lstm','name':'Qlib LSTM/GRU family','source':'Qlib','source_url':'https://github.com/microsoft/qlib','license':'MIT',
  'adapter':'SEQUENCE_SUPERVISED','data_requirements':['OHLCV sequence','point-in-time features'],'status':'RESEARCH_CANDIDATE'},
 {'id':'qlib_transformer','name':'Qlib Transformer/TFT family','source':'Qlib','source_url':'https://github.com/microsoft/qlib','license':'MIT',
  'adapter':'SEQUENCE_SUPERVISED','data_requirements':['OHLCV sequence','point-in-time features'],'status':'RESEARCH_CANDIDATE'},
 {'id':'finrl_policy','name':'FinRL-style RL policy family','source':'FinRL','source_url':'https://github.com/AI4Finance-Foundation/FinRL','license':'VERIFY_BEFORE_USE',
  'adapter':'RL_POLICY','data_requirements':['state vector','action space','cost-aware simulator'],'status':'RESEARCH_CANDIDATE'},
 {'id':'hf_finance_model','name':'Hugging Face finance model adapter','source':'Hugging Face','source_url':'https://huggingface.co/models?pipeline_tag=time-series-forecasting',
  'license':'MODEL_CARD_REQUIRED','adapter':'REMOTE_ARTIFACT','data_requirements':['model card','training data provenance','feature schema'],'status':'RESEARCH_CANDIDATE'}
]

REQUIRED_GATES=['LICENSE_OK','MODEL_CARD_COMPLETE','POINT_IN_TIME_OK','CAUSALITY_PASS','COST_STRESS_PASS','ROBUSTNESS_PASS','EXECUTION_COMPATIBLE','FORWARD_PAPER_PASS']

def catalog():
    return {'version':'48.0','models':CATALOG,'required_gates':REQUIRED_GATES,
            'policy':'External models remain challengers. Passing research gates only enables locked prospective paper testing.'}

def validate_candidate(card:dict):
    """Validate an external candidate card; unknown/uncertain evidence never passes."""
    c=card or {};reasons=[];checks={}
    lic=str(c.get('license') or '').strip()
    checks['LICENSE_OK']=bool(lic and lic not in {'UNKNOWN','VERIFY_BEFORE_USE','MODEL_CARD_REQUIRED'})
    checks['MODEL_CARD_COMPLETE']=all(c.get(k) not in (None,'',[]) for k in ['name','source','version','input_schema','output_schema'])
    checks['POINT_IN_TIME_OK']=c.get('point_in_time') is True
    checks['CAUSALITY_PASS']=c.get('causality_status')=='PASS'
    checks['COST_STRESS_PASS']=c.get('cost_stress_status')=='PASS'
    checks['ROBUSTNESS_PASS']=c.get('robustness_status')=='PASS'
    checks['EXECUTION_COMPATIBLE']=c.get('execution_compatible') is True
    fwd=c.get('forward_paper') or {}
    checks['FORWARD_PAPER_PASS']=bool((fwd.get('days') or 0)>=90 and (fwd.get('trades') or 0)>=30 and (fwd.get('profit_factor') or 0)>=1.2 and (fwd.get('max_drawdown_pct') or 999)<=8)
    for k in REQUIRED_GATES:
        if not checks.get(k):reasons.append(k)
    return {'status':'ELIGIBLE_FOR_CHALLENGER' if not reasons else 'RESEARCH_ONLY',
            'checks':checks,'veto_reasons':reasons,
            'note':'Eligibility never authorizes live trading or automatic champion replacement.'}

def score_candidate(card:dict):
    """Conservative ordering score for candidates that already passed validation."""
    v=validate_candidate(card)
    if v['status']!='ELIGIBLE_FOR_CHALLENGER':
        return {'status':v['status'],'score':None,'veto_reasons':v['veto_reasons']}
    f=card.get('forward_paper') or {}
    ret=float(f.get('return_pct') or 0);dd=max(0,float(f.get('max_drawdown_pct') or 0));pf=float(f.get('profit_factor') or 1)
    days=max(1,int(f.get('days') or 0));trades=max(1,int(f.get('trades') or 0))
    sample=min(1,days/180)*min(1,trades/60)
    score=(ret-1.5*dd+4*(pf-1))*sample
    return {'status':'ELIGIBLE_FOR_CHALLENGER','score':round(score,4),'sample_factor':round(sample,3)}

def lab_summary(cards=None):
    rows=[]
    for c in cards or []:
        rows.append({'id':c.get('id'),'name':c.get('name'),**validate_candidate(c),**score_candidate(c)})
    rows.sort(key=lambda x:(x.get('status')!='ELIGIBLE_FOR_CHALLENGER',-(x.get('score') or -999)))
    return {'status':'OK','generated_at':time.time(),'rows':rows,
            'policy':'Research candidates must pass all gates and then compete prospectively as challengers; production champion stays unchanged.'}
