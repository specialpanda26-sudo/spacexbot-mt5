import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s: print('already done:', path, old[:40]); return
    if old not in s: sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
H = 'static/index.html'
sub(H, 'var n=parseFloat(this.value);if(n>0){S[imap[id]]=n;save();',
       'var n=parseFloat(this.value);if(n>0){var lo=parseFloat(this.min),hi=parseFloat(this.max);if(lo==lo&&n<lo)n=lo;if(hi==hi&&n>hi){n=hi;this.value=hi}S[imap[id]]=n;save();')
sub(H, 'id="riskPct" type="number" min="0.1" max="5"', 'id="riskPct" type="number" min="0.1" max="2"')
print('RS3 done')
