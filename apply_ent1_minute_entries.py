import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if old not in s:
        if new in s: print('already done:', path); return
        sys.exit('NOT FOUND in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
B = 'backend/burst.py'
sub(B, "'minute_n': _clamp(j.get('minute_n'), 2, 3, DEF['minute_n'])}", "'minute_n': _clamp(j.get('minute_n'), 2, c, DEF['minute_n'])}")
sub(B, "new['minute_n'] = _whole(d['minute_n'], 2, 3, 'Entries each minute')", "new['minute_n'] = _whole(d['minute_n'], 2, c, 'Entries each minute')")
H = 'static/index.html'
sub(H, 'the bot opens 2 or 3 entries every minute', 'the bot opens this many entries every minute')
sub(H, 'Entries each minute (2 or 3)', 'Entries each minute (2 or more)')
sub(H, 'id="bswMinN" type="number" min="2" max="3"', 'id="bswMinN" type="number" min="2" max="15"')
sub('tests/test_bt7.py', "{'minute_n': 1}, {'minute_n': 4}, {'minute_n': 2.5}", "{'minute_n': 1}, {'minute_n': 16}, {'minute_n': 2.5}")
print('ENT1 done')
