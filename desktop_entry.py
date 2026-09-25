from __future__ import annotations
import os
import traceback

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
