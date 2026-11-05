"""V113 expanded external model zoo.
Current catalog metadata is explicit about license/use restrictions and adapter availability.
No external artifact is downloaded or trusted merely because it is popular.
"""
from __future__ import annotations
import importlib.util,time
from .model_zoo_lab import REQUIRED_GATES

CANDIDATES=[
 {'id':'qlib','name':'Microsoft Qlib','kind':'QUANT_FRAMEWORK','source':'GitHub','url':'https://github.com/microsoft/qlib','license':'MIT','commercial_policy':'REVIEW_ALLOWED','package':'qlib','adapter':'QLIB_BRIDGE'},
 {'id':'finrl_x','name':'FinRL-X / FinRL-Trading','kind':'RL_FRAMEWORK','source':'GitHub','url':'https://github.com/AI4Finance-Foundation/FinRL-Trading','license':'VERIFY_BEFORE_USE','commercial_policy':'RESEARCH_ONLY_UNTIL_LICENSE_VERIFIED','package':'finrl','adapter':'RL_SANDBOX'},
 {'id':'pybroker','name':'PyBroker','kind':'ML_BACKTEST_FRAMEWORK','source':'GitHub','url':'https://github.com/edtechre/pybroker','license':'VERIFY_BEFORE_USE','commercial_policy':'RESEARCH_ONLY_UNTIL_LICENSE_VERIFIED','package':'pybroker','adapter':'BACKTEST_ADAPTER'},
 {'id':'chronos2','name':'Amazon Chronos-2','kind':'TIME_SERIES_FOUNDATION','source':'Hugging Face','url':'https://huggingface.co/amazon/chronos-2','license':'Apache-2.0','commercial_policy':'REVIEW_ALLOWED','package':'chronos','adapter':'FORECAST_ADAPTER'},
 {'id':'timesfm3','name':'Google TimesFM 3.0','kind':'TIME_SERIES_FOUNDATION','source':'Hugging Face','url':'https://huggingface.co/google/timesfm-3.0-pytorch','license':'TimesFM Non-Commercial License v1.0','commercial_policy':'NON_COMMERCIAL_RESEARCH_ONLY','package':'timesfm','adapter':'FORECAST_ADAPTER'},
 {'id':'moirai2','name':'Salesforce Moirai 2.0','kind':'TIME_SERIES_FOUNDATION','source':'Hugging Face','url':'https://huggingface.co/Salesforce/moirai-2.0-R-small','license':'CC-BY-NC-4.0','commercial_policy':'NON_COMMERCIAL_RESEARCH_ONLY','package':'uni2ts','adapter':'FORECAST_ADAPTER'},
]

def catalog():
    rows=[]
    for c in CANDIDATES:
        installed=bool(importlib.util.find_spec(c['package']))
        lic_ok=c['license'] not in {'VERIFY_BEFORE_USE','UNKNOWN'} and 'Non-Commercial' not in c['license'] and 'NC' not in c['license']
        rows.append({**c,'installed':installed,'license_gate':'PASS' if lic_ok else 'RESEARCH_ONLY',
                     'integration_status':'ADAPTER_READY_TO_VALIDATE' if installed and lic_ok else 'PACKAGE_NOT_INSTALLED' if not installed else 'LICENSE_RESTRICTED'})
    return {'status':'OK','version':'113.0','as_of':'2026-11-05','rows':rows,'required_gates':REQUIRED_GATES,
            'policy':'External frameworks/models stay isolated challengers. Popularity is not evidence. License, model card, point-in-time, causality, cost, robustness, execution and prospective paper gates remain mandatory before any deeper integration.'}

def adapter_plan(candidate_id):
    c=next((x for x in CANDIDATES if x['id']==candidate_id),None)
    if not c:return {'status':'NOT_FOUND'}
    blocked=c['commercial_policy'] in {'NON_COMMERCIAL_RESEARCH_ONLY','RESEARCH_ONLY_UNTIL_LICENSE_VERIFIED'}
    return {'status':'RESEARCH_ONLY' if blocked else 'READY_FOR_SANDBOX_ADAPTER','candidate':c,
            'steps':['pin exact artifact/version','capture license + model card hash','map causal BIST input schema','run offline reproducibility test','run purged/embargoed OOS validation','run cost/capacity stress','lock prospective paper challenger'],
            'live_execution':False,'automatic_download':False,
            'policy':'No automatic package/model download. Exact artifact and legal/technical provenance must be reviewed before sandbox installation.'}
