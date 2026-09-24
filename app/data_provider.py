from __future__ import annotations
from datetime import datetime
import math
import pandas as pd
import yfinance as yf

TICKERS=["ASELS","THYAO","TUPRS","KCHOL","ASTOR","PGSUS","BIMAS","FROTO","GARAN","MGROS","AKBNK","TOASO","ISCTR","ALARK","YKBNK","TCELL","SISE","TTKOM","SAHOL","EREGL","ENJSA","ULKER","KONTR","AEFES","EKGYO","KOZAL","PETKM","SASA"]
NAMES={"ASELS":"Aselsan","THYAO":"Türk Hava Yolları","TUPRS":"Tüpraş","KCHOL":"Koç Holding","ASTOR":"Astor Enerji","PGSUS":"Pegasus","BIMAS":"BİM","FROTO":"Ford Otosan","GARAN":"Garanti BBVA","MGROS":"Migros","AKBNK":"Akbank","TOASO":"Tofaş","ISCTR":"İş Bankası C","ALARK":"Alarko Holding","YKBNK":"Yapı Kredi","TCELL":"Turkcell","SISE":"Şişecam","TTKOM":"Türk Telekom","SAHOL":"Sabancı Holding","EREGL":"Ereğli Demir Çelik","ENJSA":"Enerjisa","ULKER":"Ülker","KONTR":"Kontrolmatik","AEFES":"Anadolu Efes","EKGYO":"Emlak Konut","KOZAL":"Koza Altın","PETKM":"Petkim","SASA":"Sasa Polyester"}
SECTORS={"ASELS":"Savunma","THYAO":"Ulaştırma","TUPRS":"Enerji","KCHOL":"Holding","ASTOR":"Enerji","PGSUS":"Ulaştırma","BIMAS":"Perakende","FROTO":"Otomotiv","GARAN":"Banka","MGROS":"Perakende","AKBNK":"Banka","TOASO":"Otomotiv","ISCTR":"Banka","ALARK":"Holding","YKBNK":"Banka","TCELL":"İletişim","SISE":"Sanayi","TTKOM":"İletişim","SAHOL":"Holding","EREGL":"Demir Çelik","ENJSA":"Enerji","ULKER":"Gıda","KONTR":"Teknoloji","AEFES":"Gıda","EKGYO":"GYO","KOZAL":"Madencilik","PETKM":"Petrokimya","SASA":"Kimya"}
_cache={"stocks":[],"market":{},"at":None}

def _rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0).rolling(n).mean(); dn=(-d.clip(upper=0)).rolling(n).mean()
    rs=up/dn.replace(0,float("nan")); return 100-(100/(1+rs))

def _score(close,vol):
    ma20=close.rolling(20).mean().iloc[-1]; ma50=close.rolling(50).mean().iloc[-1]
    r=float(_rsi(close).iloc[-1]) if len(close)>=15 else 50
    vr=float(vol.iloc[-1]/vol.tail(20).mean()) if vol.tail(20).mean() else 1
    score=50+(10 if close.iloc[-1]>ma20 else -10)+(10 if ma20>ma50 else -10)
    score+=8 if 45<=r<=68 else (-6 if r>78 else 0); score+=min(10,max(-5,(vr-1)*10))
    return int(max(0,min(100,round(score)))),round(r,1),round(vr,2),ma20,ma50

def _live():
    symbols=[x+".IS" for x in TICKERS]
    raw=yf.download(symbols,period="6mo",interval="1d",group_by="ticker",auto_adjust=True,threads=True,progress=False)
    rows=[]
    for t in TICKERS:
        try:
            df=raw[t+".IS"].dropna()
            if len(df)<55: continue
            close=df["Close"]; vol=df["Volume"]; last=float(close.iloc[-1]); prev=float(close.iloc[-2])
            score,rsi,vr,ma20,ma50=_score(close,vol)
            atr=float((df["High"]-df["Low"]).tail(14).mean())
            signal="GÜÇLÜ AL" if score>=80 else "AL" if score>=68 else "İZLE" if score>=50 else "ZAYIF"
            rows.append({"ticker":t,"name":NAMES.get(t,t),"sector":SECTORS.get(t,""),"price":round(last,2),"change":round((last/prev-1)*100,2),"score":score,"signal":signal,"target":round(last+2*atr,2),"stop":round(max(0,last-1.5*atr),2),"upside":round(2*atr/last*100,1),"risk":max(5,100-score),"chart":[round(float(x),2) for x in close.tail(72)],"rsi":rsi,"volume_ratio":vr,"kap_impact":0,"smart_money":min(100,max(0,round(50+(vr-1)*20+(10 if last>ma20 else -10)))),"trend":"YUKARI" if last>ma20>ma50 else "AŞAĞI" if last<ma20<ma50 else "YATAY"})
        except Exception: pass
    return sorted(rows,key=lambda x:x["score"],reverse=True)

def snapshot():
    global _cache
    try:
        rows=_live()
        if rows: _cache["stocks"]=rows; _cache["at"]=datetime.now(); return rows
    except Exception: pass
    return _cache["stocks"]

def _one(symbol):
    d=yf.download(symbol,period="5d",interval="1d",auto_adjust=True,progress=False)
    if len(d)<2:return None
    c=d["Close"]; last=float(c.iloc[-1]); prev=float(c.iloc[-2])
    return last,round((last/prev-1)*100,2)

def market_overview():
    vals={}
    for key,sym in {"xu100":"XU100.IS","usdtry":"TRY=X","sp500":"^GSPC"}.items():
        try: vals[key]=_one(sym)
        except Exception: vals[key]=None
    return {"mode":"LIVE / YAHOO" if vals.get("xu100") else "CACHE","updated":datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    "xu100":round(vals["xu100"][0],2) if vals.get("xu100") else 0,"xu100_change":vals["xu100"][1] if vals.get("xu100") else 0,
    "usdtry":round(vals["usdtry"][0],4) if vals.get("usdtry") else 0,"usdtry_change":vals["usdtry"][1] if vals.get("usdtry") else 0,
    "sp500":round(vals["sp500"][0],2) if vals.get("sp500") else 0,"sp500_change":vals["sp500"][1] if vals.get("sp500") else 0,
    "global_score":50,"regime":"VERİ HESAPLANIYOR","fear":50,"breadth":50,"advancers":0,"decliners":0,"unchanged":0}

def kap_feed():
    return [{"time":"—","ticker":"KAP","title":"Canlı KAP entegrasyonu hazırlanıyor; resmi KAP veri yayın REST servisi abonelik tabanlıdır.","impact":0,"sentiment":"Bilgi"}]

def portfolio(): return {"equity":0,"day_pnl":0,"day_pnl_pct":0,"drawdown":0,"cash":0,"positions":[]}
def backtest(): return {"return_pct":0,"xu100_pct":0,"alpha_pct":0,"sharpe":0,"max_drawdown":0,"win_rate":0,"profit_factor":0,"trades":0,"equity":[100]}
