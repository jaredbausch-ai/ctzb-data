"""CTZB engine - mirrors ct_zone_bounce_v8.pine exactly.
Rebuilt from Pine source, not from memory."""
import csv, math, os, datetime as dt

UP = "/mnt/user-data/uploads"

# user's bull windows (from v8 inputs)
BULL = [("2014-12-04","2017-12-17"),("2018-12-17","2021-11-10"),
        ("2022-11-10","2025-10-06"),("2026-06-24","2029-12-31")]
CYCLE_LOWS = ["2015-01-14","2018-12-15","2022-11-21","2026-06-24"]

def _d(s): return dt.datetime.strptime(s,"%Y-%m-%d").date()
BULLD = [(_d(a),_d(b)) for a,b in BULL]
CLD = [_d(x) for x in CYCLE_LOWS]

def rsi(src, n=14):
    out=[None]*len(src)
    if len(src)<n+1: return out
    g=l=0.0
    for i in range(1,n+1):
        ch=src[i]-src[i-1]
        g+=max(ch,0.0); l+=max(-ch,0.0)
    ag=g/n; al=l/n
    out[n]=100.0 if al==0 else 100-100/(1+ag/al)
    for i in range(n+1,len(src)):
        ch=src[i]-src[i-1]
        ag=(ag*(n-1)+max(ch,0.0))/n
        al=(al*(n-1)+max(-ch,0.0))/n
        out[i]=100.0 if al==0 else 100-100/(1+ag/al)
    return out

def sma(src,n):
    out=[None]*len(src); s=0.0; q=[]
    for i,v in enumerate(src):
        if v is None:
            q=[]; s=0.0; continue
        q.append(v); s+=v
        if len(q)>n: s-=q.pop(0)
        if len(q)==n: out[i]=s/n
    return out

def stoch_of(src,n=14):
    """ta.stoch(src,src,src,n)"""
    out=[None]*len(src)
    for i in range(len(src)):
        w=src[max(0,i-n+1):i+1]
        if len(w)<n or any(x is None for x in w): continue
        hi=max(w); lo=min(w)
        out[i]=0.0 if hi==lo else 100*(src[i]-lo)/(hi-lo)
    return out

def ema(src,n):
    out=[None]*len(src); a=2.0/(n+1); prev=None
    # pine ta.ema seeds with sma
    first=None
    for i,v in enumerate(src):
        if v is None: continue
        if first is None: first=i; break
    if first is None: return out
    vals=[v for v in src[first:] if v is not None]
    if len(vals)<n: return out
    seed=sum(src[first:first+n])/n
    out[first+n-1]=seed; prev=seed
    for i in range(first+n,len(src)):
        prev=(src[i]-prev)*a+prev
        out[i]=prev
    return out

def load(path):
    """Read a TradingView export. Returns dict of lists."""
    with open(path, newline='', encoding='utf-8-sig') as f:
        rd=csv.reader(f); hdr=next(rd); rows=list(rd)
    idx={}
    for j,h in enumerate(hdr):
        h=h.strip()
        idx.setdefault(h,[]).append(j)
    def col(name):
        if name not in idx: return None
        for j in idx[name]:
            vals=[]
            ok=False
            for r in rows:
                try: v=float(r[j]); ok=True
                except: v=None
                vals.append(v)
            if ok and any(v is not None for v in vals): return vals
        return None
    def req(name):
        v=col(name)
        if v is None: raise KeyError(name)
        return v
    times=[]
    for r in rows:
        t=r[idx['time'][0]]
        try: times.append(dt.datetime.utcfromtimestamp(int(t)).date())
        except: times.append(dt.datetime.fromisoformat(t.replace('Z','')).date())
    return dict(date=times, open=req('open'), high=req('high'),
                low=req('low'), close=req('close'))

def bull(d):
    return any(a<=d<=b for a,b in BULLD)

def cycday(d):
    last=CLD[0]
    for c in CLD:
        if d>=c: last=c
    return (d-last).days

def signals(path, rsiLen=14, stLen=14, smK=3, smD=3, pvL=3, pvR=3,
            rxLen=10, zBear=40, bSpl=55, dSpl=65, zMid=50, regime=None, ungated=True):
    """Return confirmed signals, mirroring v8.
    regime: callable(date)->bool. Defaults to the user's hindsight bull windows."""
    inreg = regime if regime is not None else bull
    b=load(path)
    c=b['close']; hi=b['high']; lo=b['low']; dates=b['date']
    n=len(c)
    ct=rsi(c,rsiLen)
    st=stoch_of(ct,stLen)
    kL=sma(st,smK)
    rng=[(hi[i]-lo[i]) for i in range(n)]
    arng=sma(rng,rxLen)

    out=[]
    pCt=pK=None; pB=None
    for conf in range(n):
        ti=conf-pvR
        if ti-pvL<0: continue
        v=ct[ti]
        if v is None: continue
        w=[ct[j] for j in range(ti-pvL,ti+pvR+1)]
        if any(x is None for x in w): continue
        # pivotlow: strictly lower than all neighbours
        if any(ct[j]<=v for j in range(ti-pvL,ti)): continue
        if any(ct[j]<=v for j in range(ti+1,ti+pvR+1)): continue
        tk=kL[ti]
        if tk is None: continue
        d=dates[ti]
        inb=inreg(d)
        bk = "A" if v<zBear else "B" if v<bSpl else "C" if v<dSpl else "D"
        hasPrev = (pCt is not None) if ungated else (inb and pCt is not None)
        dCt = v-pCt if hasPrev else None
        dK  = tk-pK  if hasPrev else None
        ap = arng[ti-1] if ti-1>=0 else None
        rx = (hi[ti]-lo[ti])/ap if (ap and ap>0) else None
        dis = bool(hasPrev and ((dCt>0 and dK<0) or (dCt<0 and dK>0)))
        strong = dis and v<zMid
        prime = 20<=tk<50
        if inb:
            out.append(dict(ti=ti, ei=conf, date=d, edate=dates[conf],
                            ct=v, k=tk, bk=bk, dis=dis, strong=strong,
                            prime=prime, rx=rx, entry=c[conf],
                            cyc=cycday(d), prev=pCt))
            pCt=v; pK=tk; pB=ti
        if ungated:
            pCt=v; pK=tk; pB=ti
    return out, b

def fwd(b, ei, days, tfdays):
    """Forward measurement from entry bar ei over `days` calendar days."""
    c=b['close']; hi=b['high']; dates=b['date']
    end=dates[ei]+dt.timedelta(days=days)
    j=ei+1; best=-1e9; worst=1e9; last=None
    peak_j=ei
    while j<len(dates) and dates[j]<=end:
        if hi[j]>best:
            best=hi[j]; peak_j=j
        last=c[j]
        j+=1
    if last is None: return None
    up=(best/c[ei]-1)*100
    ret=(last/c[ei]-1)*100
    # RISK = worst CLOSE between entry and the eventual peak
    wc=min([c[k] for k in range(ei, peak_j+1)])
    risk=(wc/c[ei]-1)*100
    return dict(up=up, ret=ret, risk=risk, bars=j-ei-1)

def med(xs):
    xs=sorted(xs)
    if not xs: return None
    m=len(xs)//2
    return xs[m] if len(xs)%2 else (xs[m-1]+xs[m])/2
