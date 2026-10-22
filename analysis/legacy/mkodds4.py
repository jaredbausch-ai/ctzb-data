import json, html, subprocess
D=json.load(open('odds4.json'))
rows=D['rows']; bases=D['bases']; hbases=D['hbases']; C=D['conf']

COL={'all':'#334155','A':'#0D9488','B':'#2563A8','C':'#7C3AED','D':'#C2410C',
     'dia':'#64748B','gold':'#D97706','holl':'#94A3B8','Adia':'#0F766E',
     'Bdia':'#1E40AF','prime':'#1E293B'}
KEY={'ALL troughs':'all','A  trough <40':'A','B  trough 40-55':'B','C  trough 55-65':'C',
     'D  trough >65':'D','Any diamond':'dia','GOLD diamond <50':'gold',
     'HOLLOW diamond >=50':'holl','A + diamond':'Adia','B + diamond':'Bdia',
     'Prime K 20-50':'prime'}

def pc(v,d=1): return ('%+.'+str(d)+'f')%v+'%'
def ec(e):
    if e>=10: return '<td class="e pos">+%d</td>'%e
    if e<=-5: return '<td class="e neg">%d</td>'%e
    return '<td class="e">%s%d</td>'%('+' if e>=0 else '',e)
def rk(v): return '<td class="%s">%s</td>'%('g' if v>-1.0 else '',pc(v))

SOLO_HEAD=('<tr><th>#</th><th>CHART</th><th>TAG</th><th>n</th><th>/YR</th><th>WIN</th>'
 '<th>EDGE</th><th>UP 10d</th><th>UP 30d</th><th>UP 60d</th><th>RISK</th>'
 '<th class="sep">old WIN</th><th>old EDGE</th></tr>')

def solo(sub,start):
    o=[]
    for i,r in enumerate(sub,start):
        nc=' class="low"' if r['n']<10 else ''
        hw='%.0f%%'%r['h_win'] if r['h_win'] is not None else '-'
        he=('%+d'%r['h_edge']) if r['h_edge'] is not None else '-'
        delta=''
        if r['h_win'] is not None:
            d=r['win']-r['h_win']
            delta=' hi' if d>0 else ''
        o.append('<tr><td class="idx">%d</td><td class="ch">%s</td>'
          '<td><span class="chip" style="background:%s">%s</span></td>'
          '<td%s>%d</td><td class="dim">%.1f</td><td class="w%s">%.0f%%</td>%s'
          '<td class="dim">%s</td><td class="dim">%s</td><td class="big">%s</td>%s'
          '<td class="sep old">%s</td><td class="old">%s</td></tr>'%(
          i,r['chart'],COL[r['key']],html.escape(r['tag']),nc,r['n'],r['per_yr'],
          delta,r['win'],ec(r['edge']),pc(r['u10']),pc(r['u30']),pc(r['u60']),
          rk(r['risk']),hw,he))
    return '\n'.join(o)

CONF_HEAD=('<tr><th>#</th><th>TRADE</th><th>TAG</th><th>CONFIRM</th><th>CONFIRM TAG</th>'
 '<th>n</th><th>WIN</th><th>ALONE</th><th>GAIN</th><th>UP 30d</th><th>UP 60d</th><th>RISK</th></tr>')
def conf(sub,start):
    o=[]
    for i,r in enumerate(sub,start):
        nc=' class="low"' if r['n']<12 else ''
        o.append('<tr><td class="idx">%d</td><td class="ch">%s</td>'
          '<td><span class="chip sm" style="background:%s">%s</span></td>'
          '<td class="ch">%s</td><td class="dim">%s</td><td%s>%d</td>'
          '<td class="w">%.0f%%</td><td class="alone">%.0f%%</td>'
          '<td class="e %s">+%d</td><td class="dim">%s</td><td class="big">%s</td>%s</tr>'%(
          i,r['trade'],COL.get(KEY.get(r['tag'],'all'),'#334155'),html.escape(r['tag']),
          r['conf'],html.escape(r['ctag']),nc,r['n'],r['win'],r['alone'],
          'pos' if r['gain']>=25 else '',r['gain'],pc(r['u30']),pc(r['u60']),rk(r['risk'])))
    return '\n'.join(o)

CSS='''
@page { size: 11in 8.5in; margin: 0.4in; }
body{font-family:Helvetica,Arial,sans-serif;color:#0F172A;margin:0;}
.hdr{background:#0F172A;color:#fff;padding:16px 20px;border-radius:3px;margin-bottom:12px;}
.hdr h1{margin:0;font-size:26px;letter-spacing:.5px;}
.hdr p{margin:7px 0 0;font-size:11.5px;color:#CBD5E1;line-height:1.5;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th{background:#1E293B;color:#fff;padding:7px;text-align:right;font-size:10.5px;font-weight:600;}
th:nth-child(1),th:nth-child(2),th:nth-child(3){text-align:left;}
th.sep{border-left:2px solid #64748B;}
td{padding:5.5px 7px;text-align:right;border-bottom:1px solid #E2E8F0;}
td.idx{color:#94A3B8;text-align:left;width:26px;font-size:11px;}
td:nth-child(3){text-align:left;}
td.ch{text-align:left;font-weight:700;}
td.dim{color:#64748B;}
td.w{font-weight:700;}
td.w.hi{color:#0D9488;}
td.big{font-weight:700;font-size:13px;}
td.e{font-weight:700;font-size:13px;}
td.e.pos{background:#DCFCE7;color:#166534;}
td.e.neg{background:#FEE2E2;color:#991B1B;}
td.g{color:#0D9488;}
td.old{color:#94A3B8;font-size:11px;}
td.sep{border-left:2px solid #CBD5E1;}
td.alone{color:#CBD5E1;}
td.low{color:#DC2626;font-weight:700;}
.chip{display:inline-block;padding:3px 8px;border-radius:2px;color:#fff;font-size:11px;font-weight:600;white-space:nowrap;}
.chip.sm{font-size:10px;padding:2px 6px;}
.foot{margin-top:11px;font-size:11px;color:#64748B;line-height:1.6;}
.page{page-break-after:always;}
.page:last-child{page-break-after:auto;}
h2.sec{background:#0F172A;color:#fff;margin:0 0 11px;padding:12px 17px;font-size:19px;border-radius:3px;}
.kv{width:100%;border-collapse:collapse;font-size:12.5px;}
.kv th{background:#1E293B;color:#fff;text-align:left;padding:8px 12px;font-size:13px;}
.kv td{text-align:left;vertical-align:top;padding:8px 12px;border-bottom:1px solid #E2E8F0;line-height:1.55;}
.kv td.k{font-weight:700;width:215px;}
.warn{background:#FEF2F2;border-left:4px solid #DC2626;padding:12px 15px;margin:0 0 13px;font-size:12.5px;line-height:1.6;}
.warn b{color:#991B1B;}
.ok{background:#F0FDF4;border-left:4px solid #16A34A;padding:12px 15px;margin:0 0 13px;font-size:12.5px;line-height:1.6;}
.ok b{color:#166534;}
'''
def page(x): return '<div class="page">%s</div>'%x

H=('<div class="hdr"><h1>CTZB ODDS v4 &mdash; SOLO TAGS</h1>'
 '<p><b>All figures are now measured under the LIVE regime</b> (BTC 2D CT RSI: bull after 8 bars '
 'at or above 60, bear after 12 bars at or below 40). Ranked by EDGE, ties broken by sample size.<br>'
 'The two grey columns on the right are the OLD hand-drawn-window figures, kept so you can see what '
 'changed. Those windows ended on known cycle tops, so they excluded the stretches that failed and '
 'every baseline sat about nine points too high. <b style="color:#FCA5A5">The old win rates were '
 'not achievable in real time.</b> Trade the white columns.</p></div>')

P1=page(H+'<table>'+SOLO_HEAD+solo(rows[:22],1)+'</table>')
P2=page('<table>'+SOLO_HEAD+solo(rows[22:44],23)+'</table>')
BS=' &middot; '.join('<b>%s %d%%</b> <span style="color:#94A3B8">(old %d%%)</span>'%(k,v,hbases.get(k,0)) for k,v in bases.items())
P3=page('<table>'+SOLO_HEAD+solo(rows[44:],45)+'</table>'
 +'<p class="foot">Baselines, each chart&rsquo;s own all-troughs rate at 60 days inside the live '
 +'regime: '+BS+'. Signal counts under 10 in red. A green win rate beat the old hand-drawn figure.</p>')

CH1=('<div class="hdr"><h1>CONFLUENCE</h1><p>One chart&rsquo;s tag confirmed by another chart within '
 '10 days, measured under the live regime. GAIN is the lift over the SAME tag on the SAME chart '
 'without the confirmer. Both arms are measured the same way, so GAIN never depended on the baseline.</p></div>')
C1=page(CH1+'<table>'+CONF_HEAD+conf(C[:22],1)+'</table>')
C2=page('<div class="hdr"><h1>CONFLUENCE (continued)</h1></div><table>'+CONF_HEAD+conf(C[22:44],23)+'</table>'
 +'<p class="foot">ALONE = the same tag on the same chart <b>without</b> the confirmer nearby. '
 +'Counts under 12 in red. '+str(len(C))+' combinations were computed; these are the best by GAIN, '
 +'which is exactly the selection that produces false positives &mdash; read the last page.</p>')

VAL=page('<h2 class="sec">WHAT THE VALIDATION FOUND</h2>'
 '<div class="ok"><b>The indicator passed both tests.</b> Every setting was frozen on data up to '
 '31 Dec 2021 and scored on 2022&ndash;2026 untouched. The diamond edge went from +1pp in-sample to '
 '<b>+11pp out</b>. The ETH 5D window went from +14pp to <b>+39pp out</b>. The ETH 2D diamond went '
 'from 71% to <b>80%</b>. Nothing was re-tuned. Separately, the hand-drawn bull windows were replaced '
 'with a rule that could have been followed live, and the edge survived &mdash; it did not depend on '
 'hindsight.</div>'
 '<div class="warn"><b>But the absolute win rates were inflated, and this sheet now says so.</b> '
 'The old windows ended on known cycle tops. They excluded exactly the stretches that failed, which '
 'lifted every baseline by roughly nine points. ETH 2D diamonds read 89% under those windows and '
 '<b>75% under a live rule</b> &mdash; same signals, honest measurement. Plan with the white columns.</div>'
 '<table class="kv"><tr><th colspan="2">THE REGIME RULE</th></tr>'
 '<tr><td class="k">How it works</td><td>Driven by BTC 2D CT RSI. <b>BULL</b> after 8 consecutive '
 'bars at or above 60. <b>BEAR</b> after 12 consecutive bars at or below 40. In between, the state '
 'holds &mdash; so an ordinary correction passes through the middle without flipping you.</td></tr>'
 '<tr><td class="k">Why 8 bars for bull</td><td>Every run of BTC 2D CT RSI at or above 60 was sorted '
 'by regime: runs of 8+ bars happened <b>27 times inside bull windows and zero times in a bear '
 'period</b>. The longest a bear ever held the zone was 7 bars. ETH 2D is the same. The test uses no '
 'return data, so the threshold is not fitted to P&amp;L.</td></tr>'
 '<tr><td class="k">Why the bear side is slower</td><td>The mirror test does not separate. Runs of '
 'CT RSI at or below 40: 3+ bars is 20 bull / 16 bear, 8+ bars is 4 / 8, 12+ bars is 2 / 6. Bull '
 'markets dip into the bear zone constantly, so a brief visit means nothing. 12 bars is the shortest '
 'length where bear periods clearly dominate.</td></tr>'
 '<tr><td class="k">Why not combine with the halving</td><td>Tested. Requiring both gave 89% win and '
 '+103.8% upside in-sample and <b>50% on 20 signals out of sample</b>. Textbook overfitting. One rule '
 'or the other, never both.</td></tr></table>')

READ=page('<h2 class="sec">HOW TO READ THIS</h2>'
 '<table class="kv"><tr><th colspan="2">THE COLUMNS</th></tr>'
 '<tr><td class="k">UPSIDE</td><td>Median best price reached by that horizon. We take profit, so this '
 'is what was available &mdash; not the close at day 60.</td></tr>'
 '<tr><td class="k">RISK</td><td>The worst <b>close</b> between entry and the eventual peak. Measured '
 'on closes, so exchange wicks are excluded.</td></tr>'
 '<tr><td class="k">EDGE</td><td>Percentage points of win rate over that chart&rsquo;s own all-troughs '
 'rate in the live regime. Zero means the tag told you nothing the chart did not.</td></tr>'
 '<tr><td class="k">old WIN / old EDGE</td><td>The same cell under the hand-drawn windows. Reference '
 'only. Do not plan with these.</td></tr>'
 '<tr><td class="k">GAIN</td><td>Confluence only. The lift over the SAME tag on the SAME chart without '
 'the confirmer.</td></tr></table>'
 '<table class="kv" style="margin-top:12px"><tr><th colspan="2">WHAT TO TRUST</th></tr>'
 '<tr><td class="k">The regime filter</td><td>The primary edge, and it is not hindsight. Pooled '
 'diamonds score +9 edge under a live rule and <b>+1 with no regime filter at all</b>. That last '
 'number is the most important in the study: strip the filter and the diamond is worth nothing.</td></tr>'
 '<tr><td class="k">Diamonds on the ETH 2D</td><td>75% live on 36 signals, +46.5% upside, risk '
 '&minus;2.3%. Validated across RSI lengths 8 to 28 and pivot widths 2 to 5, so not fitted to the '
 'defaults. Still the best cell in the study.</td></tr>'
 '<tr><td class="k">The ETH 5D as a CONFIRMER</td><td>Not as a chart to trade. A signal on another '
 'chart within 10 days of an ETH 5D trough lifted the win rate <b>+39pp out of sample</b>. It also '
 'holds with no regime filter at all, so it does not depend on the cycle call. The strongest and most '
 'robust effect in the stack.</td></tr>'
 '<tr><td class="k">The prime dot</td><td>Stoch K between 20 and 50 at the trough. Flat in-sample, '
 '<b>+16pp out of sample</b> on ETH and BTC diamonds with upside more than doubled. Promoted to its '
 'own glyph and alert in v11.</td></tr></table>')

WARN=page('<h2 class="sec">WHAT NOT TO TRUST</h2>'
 '<table class="kv">'
 '<tr><td class="k">The old win rates</td><td>Every figure in the grey columns assumed windows that '
 'ended on known cycle tops. Roughly nine points of that was hindsight.</td></tr>'
 '<tr><td class="k">The top of any sorted table</td><td>'+str(len(C))+' confluence combinations were '
 'computed and the page is sorted by the best. That is how a false positive is manufactured. Worse: '
 'the #1 and #2 tags on the 2021 leaderboard were the <b>worst</b> performers afterwards, while the '
 'ETH 2D diamond ranked only 4th. Trade the structural effects, not the top row.</td></tr>'
 '<tr><td class="k">Anything under about 15 signals</td><td>Directional at best. Counts under 10 '
 '(solo) and 12 (confluence) are in red. Several cells rest on 3 to 8 trades.</td></tr>'
 '<tr><td class="k">Overlapping measurement</td><td>Signals on the 1D and 2D of one asset often '
 'describe the same move, and consecutive 60-day windows overlap heavily. The effective sample is '
 'smaller than the counts suggest.</td></tr>'
 '<tr><td class="k">GOLD versus HOLLOW</td><td>Earlier versions of this sheet said the hollow diamond '
 'was the stronger glyph. <b>That failed out of sample</b> &mdash; hollow led by +10pp before 2022 and '
 'trailed by 1pp after. Neither glyph reliably leads. The claim has been removed.</td></tr>'
 '<tr><td class="k">The bucket boundaries</td><td>Move 40/55/65 by five points and which letter looks '
 'worst changes. A/B/C/D is vocabulary, not measurement. Bucket C is weakest at the current '
 'boundaries &mdash; 59% out of sample &mdash; but that is a property of where the lines sit.</td></tr>'
 '<tr><td class="k">Filters tested and dropped</td><td>Range expansion, volume, money flow, stochastic '
 'slope, stochastic level and the WGMI liquidity star all came back null or worse. The range expansion '
 'filter discarded a fifth of all diamonds and the discarded group had HIGHER upside.</td></tr>'
 '<tr><td class="k">Intraday</td><td>The diamond carries no information below the daily. On ETH 4H and '
 '12H it scores &minus;3 to +2pp at every horizon.</td></tr>'
 '<tr><td class="k">The 5D mechanism</td><td>Unexplained. The same test with a BTC 5D confirmer shows '
 'nothing (p=1.00). Promising, not proven.</td></tr></table>'
 '<p class="foot">Entry is the close of the confirmation bar, three pivot bars after the RSI low '
 '&mdash; six days on a 2D chart. The label sits on the trough; the bottom-row diamond marks the entry '
 'bar, and every figure here is priced from the entry bar. Data 2016&ndash;2026 for ETH, '
 '2014&ndash;2026 for BTC. Matches CT Zone Bounce v11 and CTZB Scanner v8. Past behaviour on '
 'historical data &mdash; not a forecast, not financial advice.</p>')

doc='<html><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>'%(
    CSS,P1+P2+P3+C1+C2+VAL+READ+WARN)
open('odds_v4.html','w').write(doc)
subprocess.run(['wkhtmltopdf','--enable-local-file-access','-q','--page-size','Letter',
 '--orientation','Landscape','--margin-top','10mm','--margin-bottom','10mm',
 '--margin-left','10mm','--margin-right','10mm','odds_v4.html','CTZB_odds_v4.pdf'],check=True)
print('CTZB_odds_v4.pdf written')
