"""Section FD4: the made-up Weekly market brief is labelled 'sample data' in its title and hidden once you are signed in and verified (static/index.html).
Run from the project folder: python apply_fd4.py  (safe to run twice). Needs apply_fd3.py first."""
def edit(path, pairs):
    s = open(path, encoding='utf-8').read(); o = s
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, path + ': need exactly one: ' + old[:60]
        s = s.replace(old, new, 1)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)

OLD1 = 'card(["Weekly market brief",""]'
NEW1 = 'card(["Weekly market brief (sample data)",""]'
OLD2 = 'function fake() { var a = document.getElementById("autobotc"); if (a) a.style.display = ready() ? "none" : ""; }'
NEW2 = ('function fake() { var a = document.getElementById("autobotc"); if (a) a.style.display = ready() ? "none" : "";\n'
        '    var w = document.getElementById("wbGo"), c = w && w.closest ? w.closest(".card") : null; if (c) c.style.display = ready() ? "none" : ""; }   /*FD4: the random-walk Weekly brief is hidden for a signed-in, verified person*/')
edit('static/index.html', [(OLD1, NEW1), (OLD2, NEW2)])

NOTE = """
## Section FD4 (fake data fix d: Weekly brief) DONE (Nov 22)
- static/index.html only. The Weekly market brief (a random-walk series of the 8 made-up pairs) now says 'sample data' in its card title, and the S4 fake() function that already hid the sample Autobot card for a signed-in, verified person hides it too. It still shows (labelled) to signed-out and unverified people. tests/test_fd4.py. apply_fd4.py.
- LEFT AS IT IS on purpose: the Home chart / chart tab already carries a 'Sample data' chip and a note (line ~1486-1488), the Backtest card is labelled 'sample data, not your bot' and no longer counts (FD1), the landing phone mock-up is decorative (aria-hidden). The Autobot scan log was already hidden for signed-in people.
- The fake-data scan is now fully handled: a (FD1), b (FD2), c (FD3), d (FD4). Next: the backtest on real data (needs the owner's M15 and H1 CSVs), N6 kind 35 once decided.
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Section FD4' not in h:
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h.rstrip('\n') + '\n' + NOTE)
print('ok docs/HANDOFF.md')
