"""Is the page harness sensitive? Tamper with the feed the page reads (not the data my values come from) and count what it catches."""
import copy, json, datetime as dt, sys
import run_page as RP, stage_data as SD
root='../a18/replay_0414'; today=dt.date(2026,11,12)
feed=json.load(open(root+'/feed/ctzb_feed.json'))
f=copy.deepcopy(feed)
muts=[]
o=next(x for x in f['open_signals'] if x['signal_id']=='BTC-2D-2026-09-21')
o['card']['typical_biggest_rise_exact_pct']+=0.06; muts.append('open card typical high +0.06')
o['card']['if_it_falls_first'][0]['still_rose10_exact_pct']=70.0; muts.append('open ladder exact share to 70')
o['days_elapsed']+=1; muts.append('days elapsed +1')
o['entry_close']+=0.01; muts.append('entry close +1c')
c=f['cards'][0]; c['must_close_above']+=0.01; c['typical_day_of_60d_high']+=1; c['confirms_on']='2026-11-14'; muts+=['kill +1c','high day +1','confirms +1 day']
f['example_card']['typical_deepest_dip_exact_pct']-=0.05; muts.append('example drop -0.05')
f['past_paths'][0]['days'][60]['median_pct']+=0.1; muts.append('path day60 median +0.1')
f['if_it_misses'][0]['median_peak_pct']+=0.1; muts.append('miss median +0.1')
f['grade_odds'][0]['rose10_within60d_pct']+=1; muts.append('grade odds +1')
C,ctx,_=RP.run('MUT',root,today,site_kw=dict(feed=f))
bad=[r for r in C.rows if r[5]!='ok']
print(len(muts),'mutations ->',len(bad),'page disagreements')
for r in bad[:60]: print('  ',r[1],'|',r[2],'|',str(r[3])[:70],'|',str(r[4])[:70])
