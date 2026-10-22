import json, html, subprocess
S=json.load(open('solo.json')); C=json.load(open('conf.json'))
rows=S['rows']; bases=S['bases']
rows.sort(key=lambda r:(-r['edge'],-r['n']))

COL={'all':'#334155','A':'#0D9488','B':'#2563A8','C':'#7C3AED','D':'#C2410C',
     'dia':'#64748B','gold':'#D97706','holl':'#94A3B8','Adia':'#0F766E',
     'Bdia':'#1E40AF','prime':'#1E293B'}

def pc(v,dec=1,sign=True):
    f='%+.'+str(dec)+'f' if sign else '%.'+str(dec)+'f'
    return (f%v)+'%'

def edge_cell(e):
    if e>=10:  return '<td class="e pos">+%d</td>'%e
    if e<=-5:  return '<td class="e neg">%d</td>'%e
    return '<td class="e">%s%d</td>'%('+' if e>=0 else '',e)

def risk_cell(v):
    cls='g' if v>-1.0 else ''
    return '<td class="%s">%s</td>'%(cls,pc(v))

def solo_rows(sub,start):
    out=[]
    for i,r in enumerate(sub,start):
        nc=' class="low"' if r['n']<10 else ''
        out.append('<tr><td class="idx">%d</td><td class="ch">%s</td>'
          '<td><span class="chip" style="background:%s">%s</span></td>'
          '<td%s>%d</td><td class="dim">%.1f</td><td class="w">%.0f%%</td>%s'
          '<td class="dim">%s</td><td class="dim">%s</td><td class="dim">%s</td>'
          '<td class="big">%s</td>%s<td class="worst">%s</td></tr>'%(
          i,r['chart'],COL[r['key']],html.escape(r['tag']),nc,r['n'],r['per_yr'],
          r['win'],edge_cell(r['edge']),pc(r['u10']),pc(r['u20']),pc(r['u30']),
          pc(r['u60']),risk_cell(r['risk']),pc(r['worst'])))
    return '\n'.join(out)

SOLO_HEAD=('<tr><th>#</th><th>CHART</th><th>TAG</th><th>n</th><th>/YR</th><th>WIN</th>'
 '<th>EDGE</th><th>UP 10d</th><th>UP 20d</th><th>UP 30d</th><th>UP 60d</th>'
 '<th>RISK</th><th>WORST</th></tr>')

CONF_HEAD=('<tr><th>#</th><th>TRADE</th><th>TAG</th><th>CONFIRM</th><th>CONFIRM TAG</th>'
 '<th>n</th><th>WIN</th><th>ALONE</th><th>GAIN</th><th>UP 30d</th><th>UP 60d</th><th>RISK</th></tr>')

def conf_rows(sub,start):
    out=[]
    for i,r in enumerate(sub,start):
        nc=' class="low"' if r['n']<12 else ''
        g=r['gain']
        gc='pos' if g>=25 else ''
        out.append('<tr><td class="idx">%d</td><td class="ch">%s</td>'
          '<td><span class="chip sm" style="background:%s">%s</span></td>'
          '<td class="ch">%s</td><td class="dim">%s</td><td%s>%d</td>'
          '<td class="w">%.0f%%</td><td class="alone">%.0f%%</td>'
          '<td class="e %s">+%d</td><td class="dim">%s</td><td class="big">%s</td>%s</tr>'%(
          i,r['trade'],COL.get(KEY.get(r['tag'],'all'),'#334155'),html.escape(r['tag']),
          r['conf'],html.escape(r['ctag']),nc,r['n'],r['win'],r['alone'],gc,g,
          pc(r['u30']),pc(r['u60']),risk_cell(r['risk'])))
    return '\n'.join(out)

KEY={'ALL troughs':'all','A  trough <40':'A','B  trough 40-55':'B','C  trough 55-65':'C',
     'D  trough >65':'D','Any diamond':'dia','GOLD diamond <50':'gold',
     'HOLLOW diamond >=50':'holl','A + diamond':'Adia','B + diamond':'Bdia',
     'Prime K 20-50':'prime'}

CSS='''
@page { size: 11in 8.5in; margin: 0.4in; }
body{font-family:Helvetica,Arial,sans-serif;color:#0F172A;margin:0;}
.hdr{background:#0F172A;color:#fff;padding:16px 20px;border-radius:3px;margin-bottom:12px;}
.hdr h1{margin:0;font-size:26px;letter-spacing:.5px;}
.hdr p{margin:7px 0 0;font-size:11.5px;color:#CBD5E1;line-height:1.5;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th{background:#1E293B;color:#fff;padding:7px 7px;text-align:right;font-size:10.5px;
   font-weight:600;letter-spacing:.4px;}
th:nth-child(1),th:nth-child(2),th:nth-child(3){text-align:left;}
td{padding:5.5px 7px;text-align:right;border-bottom:1px solid #E2E8F0;}
td.idx{color:#94A3B8;text-align:left;width:26px;font-size:11px;}
td:nth-child(3){text-align:left;}
td.ch{text-align:left;font-weight:700;font-size:12px;}
td.dim{color:#64748B;}
td.w{font-weight:700;}
td.big{font-weight:700;font-size:13px;}
td.e{font-weight:700;font-size:13px;}
td.e.pos{background:#DCFCE7;color:#166534;}
td.e.neg{background:#FEE2E2;color:#991B1B;}
td.g{color:#0D9488;}
td.worst{color:#DC2626;}
td.alone{color:#CBD5E1;}
td.low{color:#DC2626;font-weight:700;}
.chip{display:inline-block;padding:3px 8px;border-radius:2px;color:#fff;
      font-size:11px;font-weight:600;white-space:nowrap;}
.chip.sm{font-size:10px;padding:2px 6px;}
.foot{margin-top:11px;font-size:11px;color:#64748B;line-height:1.6;}
.page{page-break-after:always;}
.page:last-child{page-break-after:auto;}
h2.sec{background:#0F172A;color:#fff;margin:0 0 11px;padding:12px 17px;font-size:19px;border-radius:3px;}
.kv{width:100%;border-collapse:collapse;font-size:12.5px;}
.kv th{background:#1E293B;color:#fff;text-align:left;padding:8px 12px;font-size:13px;}
.kv td{text-align:left;vertical-align:top;padding:8px 12px;border-bottom:1px solid #E2E8F0;line-height:1.55;}
.kv td.k{font-weight:700;width:215px;}
.warn{background:#FEF2F2;border-left:4px solid #DC2626;padding:12px 15px;margin:0 0 13px;
      font-size:12.5px;line-height:1.6;}
.warn b{color:#991B1B;}
'''

def page(inner): return '<div class="page">%s</div>'%inner

H1=('<div class="hdr"><h1>CTZB ODDS v3 &mdash; SOLO TAGS</h1>'
 '<p><b>Ranked by EDGE, highest first</b> &mdash; ties broken by sample size. UPSIDE = median '
 'best price reached. RISK = worst CLOSE between entry and the eventual peak.<br>'
 '<b style="color:#FCA5A5">v3 corrects the EDGE column.</b> Every edge is now measured against '
 'that chart&rsquo;s OWN all-troughs rate. v2 used baselines set below the true rate &mdash; '
 'harmless on most charts, but the ETH 5D was listed at 70% when its real baseline is 84%, '
 'so every ETH 5D edge in v2 was overstated by 14 points.</p></div>')
P1=page(H1+'<table>'+SOLO_HEAD+solo_rows(rows[:22],1)+'</table>')

P2=page('<table>'+SOLO_HEAD+solo_rows(rows[22:44],23)+'</table>')
BASESTR=' &middot; '.join('<b>%s %d%%</b>'%(k,v) for k,v in bases.items())
P3=page('<table>'+SOLO_HEAD+solo_rows(rows[44:],45)+'</table>'
 +'<p class="foot">Baselines (each chart&rsquo;s own all-troughs rate at 60 days, inside '
 +'bull windows): '+BASESTR+'. Signal counts under 10 in red.</p>')

CH1=('<div class="hdr"><h1>CONFLUENCE</h1><p>One chart&rsquo;s tag confirmed by another '
 'chart within 10 days. GAIN is the lift over the SAME tag on the SAME chart without the '
 'confirmer &mdash; that is the only honest comparison, and because both arms are measured '
 'the same way, GAIN never depended on the baseline that v3 corrects. These figures are '
 'unchanged in substance from v2.</p></div>')
C1=page(CH1+'<table>'+CONF_HEAD+conf_rows(C[:22],1)+'</table>')

C2=page('<div class="hdr"><h1>CONFLUENCE (continued)</h1></div>'
 +'<table>'+CONF_HEAD+conf_rows(C[22:44],23)+'</table>'
 +'<p class="foot">ALONE = the same tag on the same chart <b>without</b> the confirmer nearby. '
 +'A high WIN with a low GAIN means the tag was already good. Counts under 12 in red. '
 +str(len(C))+' combinations were computed; these are the best by GAIN, which is exactly the '
 +'selection that produces false positives &mdash; read the last page.</p>')

READ=page('<h2 class="sec">HOW TO READ THIS</h2>'
 '<div class="warn"><b>What changed in v3.</b> The EDGE column was recomputed. '
 'A chart&rsquo;s baseline IS its all-troughs win rate, so an ALL TROUGHS row must show an edge '
 'of zero by definition. In v2 the ETH 5D ALL TROUGHS row showed 84% win and +14 edge, which '
 'was the tell: the 84% was the baseline. Inside a bull window <b>every</b> trough on the ETH 5D '
 'went 84% at 60 days, so no tag on that chart beats simply taking them all. '
 'ETH 5D &ldquo;Any diamond&rdquo; went from +14 to &minus;1. '
 'ETH 3D, BTC 1D and BTC 2D shifted by 2 to 3 points. ETH 1D and ETH 2D are unchanged.</div>'
 '<table class="kv"><tr><th colspan="2">THE COLUMNS</th></tr>'
 '<tr><td class="k">UPSIDE</td><td>Median best price reached by that horizon. We take profit, '
 'so this is what was available &mdash; not the close at day 60.</td></tr>'
 '<tr><td class="k">RISK</td><td>The worst <b>close</b> between entry and the eventual peak. '
 'The most you were ever underwater before the trade worked. Measured on closes, so exchange '
 'wicks are excluded.</td></tr>'
 '<tr><td class="k">WORST</td><td>The single worst instance of RISK in that cell. One trade, '
 'not a median.</td></tr>'
 '<tr><td class="k">EDGE</td><td>Percentage points of win rate over that chart&rsquo;s own '
 'bull-window all-troughs rate. Zero means the tag told you nothing the chart did not.</td></tr>'
 '<tr><td class="k">GAIN</td><td>Confluence only. The lift over the SAME tag on the SAME chart '
 'without the confirmer.</td></tr></table>'
 '<table class="kv" style="margin-top:12px"><tr><th colspan="2">WHAT TO TRUST</th></tr>'
 '<tr><td class="k">The cycle filter</td><td>The primary edge. Everything here is measured inside '
 'bull windows anchored to Bitcoin all-time highs, Window 4 from 2026-06-24. Outside those '
 'windows the tags are close to worthless.</td></tr>'
 '<tr><td class="k">Diamonds on the ETH 2D</td><td>89% at 60 days against a 69% baseline on 35 '
 'signals, 4.6 a year, risk &minus;2.0%. Validated across RSI lengths 8 to 28 and pivot widths '
 '2 to 5, so it is not fitted to the defaults. The single best cell in the study.</td></tr>'
 '<tr><td class="k">The ETH 5D as a CONFIRMER</td><td>Not as a chart to trade. A signal on one of '
 'the other five charts within 10 days of an ETH 5D trough went <b>82% with +41.3% upside</b>, '
 'against 63% and +23.6% outside that window &mdash; +18pp on n=1064. The strongest single effect '
 'in the stack, and it survived re-measurement. The 5D&rsquo;s own tags add nothing; its value is '
 'entirely as a clock for the other charts.</td></tr>'
 '<tr><td class="k">The prime dot</td><td>Stoch K between 20 and 50 at the trough. Pooled over '
 'nine charts, diamonds with the dot went 79% and +39.6% upside against 71% and +29.1% without. '
 'Positive at 10, 20, 30, 60 and 90 days and on 8 of 9 charts. XRP is the exception.</td></tr>'
 '<tr><td class="k">Bucket A</td><td>Strongest bucket on BTC and on the ETH 5D.</td></tr></table>')

WARN=page('<h2 class="sec">WHAT NOT TO TRUST</h2>'
 '<table class="kv">'
 '<tr><td class="k">The top of the confluence table</td><td>'+str(len(C))+' combinations were computed and the '
 'page is sorted by the best of them. That is precisely how a false positive is manufactured. '
 'An earlier confluence finding on this data looked significant at p=0.003 and dissolved to '
 'p=0.42 when a longer file was supplied.</td></tr>'
 '<tr><td class="k">Anything under about 15 signals</td><td>Directional at best. Counts under 10 '
 '(solo) and 12 (confluence) are printed in red. Several cells rest on 3 to 8 trades.</td></tr>'
 '<tr><td class="k">Overlapping measurement</td><td>Signals on the 1D and 2D of one asset often '
 'describe the same market move, and the 60-day windows of consecutive signals overlap heavily. '
 'The effective sample is far smaller than the counts suggest.</td></tr>'
 '<tr><td class="k">GOLD over HOLLOW</td><td>The filled gold diamond is not the stronger glyph. '
 'Pooled over eight charts, excluding XRP, the HOLLOW diamond went 81% with +42.5% upside against '
 'the filled diamond&rsquo;s 72% and +31.4%. Hollow beat filled on 7 of 9 charts. XRP is the sole '
 'reversal. The colouring on the chart implies a ranking the data does not support.</td></tr>'
 '<tr><td class="k">The bucket boundaries</td><td>Move 40/55/65 by five points and which letter '
 'looks worst changes. A/B/C/D is vocabulary, not measurement. Bucket C is weakest at the current '
 'boundaries on most charts, but that is a property of where the lines sit.</td></tr>'
 '<tr><td class="k">Filters that were tested and dropped</td><td>Range expansion, volume, money '
 'flow, stochastic slope, stochastic level and the WGMI liquidity star all came back null or '
 'worse. The range expansion filter discarded a fifth of all diamonds and the discarded group had '
 'HIGHER upside (+38.5% vs +31.9%) and LOWER risk than the group it kept. It was removed from the '
 'indicator and the scanner in v9 / v6.</td></tr>'
 '<tr><td class="k">Intraday</td><td>The diamond carries no information below the daily. On ETH 4H '
 'and 12H it scores &minus;3 to +2pp at every horizon.</td></tr></table>'
 '<p class="foot">Entry is the close of the confirmation bar, three pivot bars after the RSI low '
 '&mdash; six days on a 2D chart. The label sits on the trough; the bottom-row diamond marks the '
 'entry bar, and every figure here is priced from the entry bar. Data 2016&ndash;2026 for ETH, '
 '2014&ndash;2026 for BTC, bull windows only. Past behaviour on historical data &mdash; not a '
 'forecast, not financial advice.</p>')

doc='<html><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>'%(
    CSS,P1+P2+P3+C1+C2+READ+WARN)
open('odds_v3.html','w').write(doc)
subprocess.run(['wkhtmltopdf','--enable-local-file-access','-q','--page-size','Letter',
                '--orientation','Landscape','--margin-top','10mm','--margin-bottom','10mm',
                '--margin-left','10mm','--margin-right','10mm',
                'odds_v3.html','CTZB_odds_v3.pdf'],check=True)
print('CTZB_odds_v3.pdf written')
