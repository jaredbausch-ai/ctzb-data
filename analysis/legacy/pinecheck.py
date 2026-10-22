"""Static checker for Pine v5/v6. Rebuilt. Rules earned the hard way."""
import re, sys

# A line that ENDS mid-expression, so the next line continues it.
# NOTE: "=>" is deliberately excluded - it OPENS a function body, so a
# 4-space indent after it is correct, not a continuation.
OPEN_END = re.compile(r'(?:(?<![=<>!])[,+\-*/?(\[]|(?<!:):(?!:)|\b(?:and|or|not)\b|:=|==)\s*$')
# A line that legitimately opens an indented block.
OPENS_BLOCK = re.compile(r'(?:=>|^\s*(?:if|else|else\s+if|for|while|switch)\b.*)\s*$')

def strip_strings(s):
    out=[];i=0;n=len(s)
    while i<n:
        c=s[i]
        if c=='"':
            j=i+1
            while j<n and s[j]!='"': j+=2 if s[j]=='\\' else 1
            out.append('""'); i=j+1
        else:
            out.append(c); i+=1
    return ''.join(out)

def code_of(line):
    s=strip_strings(line)
    p=s.find('//')
    return s[:p] if p>=0 else s

def check(path):
    L=open(path,encoding='utf-8').read().split('\n')
    errs=[]
    # --- declared functions and their line numbers ---
    decl={}
    for i,l in enumerate(L):
        m=re.match(r'^(\w+)\s*\(([^)]*)\)\s*=>', l)
        if m: decl[m.group(1)]=i+1
    builtin=set('''if for while and or not na nz int float bool string color label line table
        plot plotshape hline fill bgcolor indicator input request str math ta array
        barstate timeframe alertcondition max min abs floor round timestamp var varip
        close open high low volume time switch method type matrix map log'''.split())

    depth_prev=0
    for i,raw in enumerate(L):
        ln=i+1
        code=code_of(raw)
        if not code.strip():
            continue
        ind=len(raw)-len(raw.lstrip(' '))

        # RULE 1: continuation line indented by a multiple of 4  -> parsed as a new block
        if i>0:
            prev=code_of(L[i-1])
            if prev.strip() and OPEN_END.search(prev.rstrip()) and not OPENS_BLOCK.search(prev.rstrip()):
                if ind>0 and ind%4==0:
                    errs.append((ln,'CONTINUATION indented %d (multiple of 4) -> parsed as a new block'%ind))

        # RULE 2: non-ASCII outside comments and strings
        for ch in code:
            if ord(ch)>127:
                errs.append((ln,'non-ASCII %r in code (allowed only in comments/strings)'%ch)); break

        # RULE 3: indent rises but the previous line opens no block
        if i>0:
            pj=i-1
            while pj>=0 and not code_of(L[pj]).strip(): pj-=1
            if pj>=0:
                pcode=code_of(L[pj]); pind=len(L[pj])-len(L[pj].lstrip(' '))
                cont=bool(OPEN_END.search(pcode.rstrip()))
                opens=bool(OPENS_BLOCK.search(pcode.rstrip()))
                if ind>pind and not opens and not cont:
                    errs.append((ln,'indent rises from %d to %d but line %d opens no block'%(pind,ind,pj+1)))

        # RULE 4: function called before it is declared
        for m in re.finditer(r'\b(\w+)\s*\(', code):
            nm=m.group(1)
            if nm in decl and decl[nm]>ln and nm not in builtin:
                errs.append((ln,'calls %s() declared later at line %d'%(nm,decl[nm])))

    # RULE 6: a "? x : na" ternary as the FIRST argument of plotshape and
    # friends. Those take a series bool straight; the na branch is typed
    # "simple na" and the compiler rejects it (CE10123). Cost one round trip.
    for i,raw in enumerate(L):
        c=code_of(raw)
        m=re.search(r'\b(plotshape|plotchar|plotarrow)\s*\(', c)
        if m:
            j=m.end(); depth=1; arg=''
            while j<len(c) and depth>0:
                ch=c[j]
                if ch=='(': depth+=1
                elif ch==')': depth-=1
                if depth==0: break
                if ch==',' and depth==1: break
                arg+=ch; j+=1
            if re.search(r':\s*na\s*$', arg.strip()):
                errs.append((i+1,'%s() first arg uses "? ... : na" - pass the bool series directly (CE10123)'%m.group(1)))

    # RULE 5: unbalanced brackets
    bal=0
    for i,raw in enumerate(L):
        c=code_of(raw)
        bal+=c.count('(')+c.count('[')-c.count(')')-c.count(']')
    if bal!=0: errs.append((0,'bracket imbalance %+d over the file'%bal))
    return errs

if __name__=='__main__':
    bad=0
    for p in sys.argv[1:]:
        e=check(p)
        print('=== %s : %d issue(s)'%(p.split('/')[-1],len(e)))
        seen=set()
        for ln,m in e:
            if (ln,m) in seen: continue
            seen.add((ln,m)); bad+=1
            print('   line %-4s %s'%(ln,m))
    sys.exit(1 if bad else 0)
