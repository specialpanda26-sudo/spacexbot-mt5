import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s: print('already done:', path, old[:40]); return
    if old not in s: sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
sub('backend/risk.py', "    net = exposure(uid); cap = int(st.fget('max_ccy_exposure'))\n",
    "    net = exposure(uid); cap = int(st.fget('max_ccy_exposure'))\n    if cap <= 0: cap = 1000 if limits._owner(uid) else 2          # RS4: 0 = off for the owner; everyone else keeps 2\n")
sub('backend/app.py', "('max_ccy_exposure', 0, 10)".replace('0, 10', '1, 10'), "('max_ccy_exposure', 0, 10)")
sub('static/index.html', '["max_ccy_exposure","Most trades leaning the same way on one currency","n",1,10]', '["max_ccy_exposure","Most trades leaning the same way on one currency (0 = off, owner only)","n",0,10]')
print('RS4 done')
