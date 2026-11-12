import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
root, now = sys.argv[1], dt.datetime.fromisoformat(sys.argv[2].replace('Z','+00:00'))
M = L.Market(root, now)
for a in ('ETH','BTC'):
    for tf in (1,2,3,5,8):
        b = M.chart(a, tf); C=b['close']; n=len(C); ct=L.rsi(C)
        for back in (1,2,3):
            ti=n-1-back; v=ct[ti]
            if any(ct[j] <= v for j in range(ti-3,ti)): continue
            if any(ct[j] < v for j in range(ti+1,n)): continue
            print(a, tf, 'forming trough', b['date'][ti], 'need', 3-back, 'ct', round(v,2)); break
print('gate today', M.gate(M.today), M.today)
