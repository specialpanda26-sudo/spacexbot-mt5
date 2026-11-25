# NC1: the owner's "No limit on open trades" is ON by default (no maximum open trades)
def sub(p, old, new):
    s = open(p, encoding='utf-8').read()
    if old not in s: print('MISS', p, old[:50]); return
    open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('ok', p)
sub('backend/store.py', "'no_open_cap': os.getenv('NO_OPEN_CAP', '0')", "'no_open_cap': os.getenv('NO_OPEN_CAP', '1')")
sub('tests/test_oc1.py', "T('default: switch off, the owner limit is the old number', limits.no_cap('') is False and limits.max_open('') == 3)",
    "T('default: switch ON (NC1), the owner has no open limit', limits.no_cap('') is True and limits.max_open('') == limits.UNLIMITED)\nst.put('no_open_cap', '0'); T('switched off: back to the old number', limits.no_cap('') is False and limits.max_open('') == 3); st.put('no_open_cap', '0')")
