from __future__ import annotations
import os
def institutional_provider_status():
    return {
      'takas':{'configured':bool(os.getenv('TAKAS_API_URL')),'mode':'OFFICIAL_CONNECTOR_REQUIRED','env':'TAKAS_API_URL'},
      'level2':{'configured':bool(os.getenv('LEVEL2_API_URL')),'mode':'LICENSED_CONNECTOR_REQUIRED','env':'LEVEL2_API_URL'},
      'tick':{'configured':bool(os.getenv('TICK_API_URL')),'mode':'LICENSED_CONNECTOR_REQUIRED','env':'TICK_API_URL'},
      'fund_flow':{'configured':bool(os.getenv('FUND_FLOW_API_URL')),'mode':'OFFICIAL_CONNECTOR_REQUIRED','env':'FUND_FLOW_API_URL'},
      'note':'No synthetic custody/order-book/tick data is generated. Official licensed endpoints can be connected through environment-configured providers.'
    }
