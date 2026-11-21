"""Section 5b: the update card never says "fixes". Text: "A new update is available for spaceXBot. Update now to get the latest features." Needs apply_upd5.py first. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
edit('static/update.js', r'''"A new version of spaceXBot is ready. Update now to get the latest fixes and features."''',
 r'''"A new update is available for spaceXBot. Update now to get the latest features."''', 'A new update is available for spaceXBot')
edit('tests/test_update5.py', r'''  out.title = (all(ov).find(n => n.tag === 'h2') || {}).textContent;''',
 r'''  out.title = (all(ov).find(n => n.tag === 'h2') || {}).textContent;
  out.fix = all(ov).filter(n => n.className !== 'unote' && /fix/i.test(n.textContent)).length;
  out.said = all(ov).some(n => n.textContent === 'A new update is available for spaceXBot. Update now to get the latest features.');''', 'out.said')
edit('tests/test_update5.py', r'''T('title is Update available', o['title'] == 'Update available')''',
 r'''T('title is Update available', o['title'] == 'Update available')
T('the card text says a new update is available and never mentions fixes (the release note line is separate)', o['said'] is True and o['fix'] == 0)''', "never mentions fixes")
