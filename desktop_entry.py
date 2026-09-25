from __future__ import annotations
import os
import traceback

# Explicit imports make PyInstaller analyze every local application module.
import app.advanced_indicators
import app.analyst_engine
import app.opportunity_engine
import app.backtest
import app.catalysts
import app.data_provider
import app.fundamentals
import app.kap_engine
import app.market_data
import app.market_internals
import app.model_governance
import app.news_engine
import app.portfolio_analytics
import app.providers
import app.research_engine
import app.scoring
import app.universe

def main():
    try:
        import uvicorn
        from app.main import app
        port=int(os.getenv("BIST_AI_PORT","18765"))
        uvicorn.run(app,host="127.0.0.1",port=port,log_level="warning",access_log=False)
    except Exception:
        traceback.print_exc()
        raise

if __name__=="__main__":
    main()
