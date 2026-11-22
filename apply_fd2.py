"""Section FD2: the made-up 'Focus pair now' line is gone (static/index.html, Session limits card).
Run from the project folder: python apply_fd2.py  (safe to run twice). Needs apply_fd1.py first."""
def edit(path, pairs):
    s = open(path, encoding='utf-8').read(); o = s
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, path + ': need exactly one: ' + old[:60]
        s = s.replace(old, new, 1)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)

OLD = ('var f=focus();$("#uFocus").textContent=X.auto?(f?"Focus pair now: "+f.p[0]+" ("+f.a.s+" setup, score "+f.a.sc+").":'
       '"No clean setup right now, so the bot stays put."):"Auto-switch is off. The bot stays on the pair you chose.";')
NEW = ('$("#uFocus").textContent=X.auto?"Auto-switch is on. The bot moves to a pair when a live setup appears.":'
       '"Auto-switch is off. The bot stays on the pair you chose.";')
edit('static/index.html', [(OLD, NEW)])

NOTE = """
## Section FD2 (fake data fix b: Focus pair) DONE (Nov 22)
- static/index.html only. The Session limits note under the switches no longer prints 'Focus pair now: XAUUSD (Buy setup, score 72)' (it came from the made-up price table P, not live data). It now says only 'Auto-switch is on. The bot moves to a pair when a live setup appears.' or the old 'Auto-switch is off...' sentence. The unused focus() function was left in place. tests/test_fd2.py. apply_fd2.py.
- Fake data scan items 3-5 are still open (c News list, d Weekly brief / Home chart labels). Owner picks which next.
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Section FD2' not in h:
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h.rstrip('\n') + '\n' + NOTE)
print('ok docs/HANDOFF.md')
