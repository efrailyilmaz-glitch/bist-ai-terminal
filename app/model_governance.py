from __future__ import annotations

def model_card():
    return {
      'version':'5.0',
      'purpose':'BIST quantitative + fundamental research terminal',
      'horizons':{
        'short':'days to weeks; technical/momentum/event weighted',
        'long':'months; trend/fundamental/quality/risk weighted'
      },
      'components':['technical','fundamental','KAP public events','headline sentiment','macro regime','portfolio risk'],
      'validation':{
        'transaction_costs':True,'slippage':True,'walk_forward':True,'monte_carlo_block_bootstrap':True,
        'strategy_comparison':True,'out_of_sample_metrics':True
      },
      'known_limitations':[
        'Current BIST universe can introduce survivorship bias in historical universe-level studies.',
        'Yahoo data is delayed/third-party and may have missing or revised fields.',
        'Fundamental fields are not guaranteed to be comparable across all sectors or reporting regimes.',
        'Turkish inflation accounting (TAS 29/TMS 29) can reduce comparability of historical accounting ratios.',
        'Headline sentiment scores titles only; article bodies are not semantically analyzed.',
        'KAP public-page parsing is not a substitute for licensed real-time KAP REST distribution.',
        'Smart-money and anomaly scores are price/volume proxies, not custody, takas, order-book or manipulation proof.',
        'Monte Carlo uses historical block-bootstrap distributions and is not an election-style probability forecast or price forecast.'
      ],
      'data_policy':{
        'missing':'N/A or reduced confidence','level2':'not fabricated','takas':'not fabricated',
        'live_broker':'disabled until official documented provider is configured'
      }
    }
