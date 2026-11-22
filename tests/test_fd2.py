"""Section FD2: the Session limits note must not show a pair taken from the made-up price table."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__))
S = open(os.path.join(H, '..', 'static', 'index.html'), encoding='utf-8').read()
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print('FAIL', name)

chk('one writer of the note', S.count('$("#uFocus").textContent=') == 1)
chk('no Focus pair text', 'Focus pair now' not in S)
chk('no score text', '" setup, score "' not in S)
chk('note no longer calls focus()', 'var f=focus();$("#uFocus")' not in S)
chk('auto on sentence', 'Auto-switch is on. The bot moves to a pair when a live setup appears.' in S)
chk('auto off sentence kept', 'Auto-switch is off. The bot stays on the pair you chose.' in S)
chk('note element still there', '<p class="note" id="uFocus"></p>' in S)
print('%d/%d passed' % (ok, ok + bad))
sys.exit(1 if bad else 0)
