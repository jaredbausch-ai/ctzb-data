import re
import chk

def cmp_lines(st, loc, shown_txt, exp_lines, cause):
    sh = [x for x in shown_txt.split('\n') if x.strip() != '']
    ex = [x for x in exp_lines if x is not None]
    n = max(len(sh), len(ex))
    lab = ''
    for i in range(n):
        s = sh[i] if i < len(sh) else '<missing>'
        e = ex[i] if i < len(ex) else '<missing>'
        if not re.search(r'\d', e) and not re.search(r'\d', s) and s == e:
            lab = e; chk.add(st, loc, f'text line {i}', s, e, cause); continue
        chk.add(st, loc, f'line {i}' + (f' (after "{lab}")' if lab else ''), s, e, cause)
        lab = e if not re.search(r'^[\d+−$-]', e) else lab


