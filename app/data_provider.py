from __future__ import annotations
import random
from datetime import datetime

def _series(seed:int, base:float, n=72):
    rnd=random.Random(seed); arr=[]; p=base
    for _ in range(n):
        p=max(1,p*(1+rnd.gauss(0,0.006))); arr.append(round(p,2))
    return arr

UNIVERSE=[
('ASELS','Aselsan','Savunma',232.40,92),('THYAO','Türk Hava Yolları','Ulaştırma',314.75,88),
('TUPRS','Tüpraş','Enerji',201.20,86),('KCHOL','Koç Holding','Holding',181.50,84),
('ASTOR','Astor Enerji','Enerji',111.80,83),('PGSUS','Pegasus','Ulaştırma',224.2,82),
('BIMAS','BİM','Perakende',563.00,81),('FROTO','Ford Otosan','Otomotiv',1068.00,80),
('GARAN','Garanti BBVA','Banka',145.10,79),('MGROS','Migros','Perakende',587.00,78),
('AKBNK','Akbank','Banka',69.25,77),('TOASO','Tofaş','Otomotiv',276.75,76),
('ISCTR','İş Bankası C','Banka',14.94,75),('ALARK','Alarko Holding','Holding',96.2,75),
('YKBNK','Yapı Kredi','Banka',35.74,74),('TCELL','Turkcell','İletişim',101.4,74),
('SISE','Şişecam','Sanayi',47.82,73),('TTKOM','Türk Telekom','İletişim',55.3,73),
('SAHOL','Sabancı Holding','Holding',93.20,72),('EREGL','Ereğli Demir Çelik','Demir Çelik',31.42,71),
('ENJSA','Enerjisa','Enerji',83.25,70),('ULKER','Ülker','Gıda',118.4,70),
('KONTR','Kontrolmatik','Teknoloji',58.15,69),('AEFES','Anadolu Efes','Gıda',18.6,68),
('EKGYO','Emlak Konut','GYO',21.1,66),('KOZAL','Koza Altın','Madencilik',28.8,64),
('PETKM','Petkim','Petrokimya',16.74,61),('SASA','Sasa Polyester','Kimya',4.43,55)]

def snapshot():
    rows=[]
    for i,(ticker,name,sector,base,score) in enumerate(UNIVERSE):
        s=_series(100+i,base); last=s[-1]; prev=s[-2]; change=(last/prev-1)*100
        target=last*(1+(score-50)/250); stop=last*(1-max(.035,(100-score)/700))
        sig='GÜÇLÜ AL' if score>=86 else 'AL' if score>=76 else 'İZLE' if score>=65 else 'UZAK DUR'
        rows.append({'ticker':ticker,'name':name,'sector':sector,'price':last,'change':round(change,2),
        'score':score,'signal':sig,'target':round(target,2),'stop':round(stop,2),
        'upside':round((target/last-1)*100,1),'risk':max(8,min(78,92-score+(i%5)*3)),
        'chart':s,'rsi':round(42+(score%34),1),'volume_ratio':round(.9+(score%13)/10,2),
        'kap_impact':round((score-70)*1.7,1),'smart_money':max(15,min(95,score+(i%4)*2-3)),
        'trend':'YUKARI' if score>=72 else 'YATAY' if score>=62 else 'AŞAĞI'})
    return sorted(rows,key=lambda x:x['score'],reverse=True)

def market_overview():
    return {'mode':'DEMO/CACHE','updated':datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
    'xu100':11284.6,'xu100_change':.84,'usdtry':41.33,'usdtry_change':.12,'sp500':6461.2,
    'sp500_change':.31,'global_score':63,'regime':'RISK-ON / BULL','fear':34,'breadth':68,
    'advancers':331,'decliners':176,'unchanged':29}

def kap_feed():
    return [{'time':'17:38','ticker':'ASELS','title':'Yeni iş ilişkisi / sözleşme bildirimi','impact':82,'sentiment':'Pozitif'},
    {'time':'17:21','ticker':'THYAO','title':'Operasyonel trafik sonuçları','impact':61,'sentiment':'Pozitif'},
    {'time':'16:54','ticker':'TUPRS','title':'Yatırım ve kapasite güncellemesi','impact':74,'sentiment':'Pozitif'},
    {'time':'16:28','ticker':'SASA','title':'Finansman / borçlanma işlemi','impact':-38,'sentiment':'Negatif'}]

def portfolio():
    top=snapshot()[:5]
    return {'equity':125430.0,'day_pnl':1420.0,'day_pnl_pct':1.15,'drawdown':-2.8,'cash':18400.0,
    'positions':[{'ticker':r['ticker'],'weight':w,'pnl':p} for r,w,p in zip(top,[24,22,19,18,17],[4.8,3.1,2.4,1.7,-.4])]}

def backtest():
    return {'return_pct':28.4,'xu100_pct':17.9,'alpha_pct':10.5,'sharpe':1.62,'max_drawdown':-8.7,
    'win_rate':58.4,'profit_factor':1.71,'trades':146,'equity':[100,101,99,103,105,108,106,112,115,113,119,123,121,128.4]}
