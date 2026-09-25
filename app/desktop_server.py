from __future__ import annotations
import os
import uvicorn
from app.main import app

def main():
    port=int(os.getenv("BIST_AI_PORT","18765"))
    uvicorn.run(app,host="127.0.0.1",port=port,log_level="warning",access_log=False)

if __name__=="__main__":
    main()
