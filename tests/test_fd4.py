"""Section FD4: the sample Weekly brief is labelled and hidden for a signed-in, verified person."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__))
S = open(os.path.join(H, '..', 'static', 'index.html'), encoding='utf-8').read()
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print('FAIL', name)

chk('title says sample data', 'card(["Weekly market brief (sample data)",""]' in S and 'card(["Weekly market brief",""]' not in S)
chk('fake() hides the brief with the same ready() rule', 'w.closest(".card")' in S and 'c.style.display = ready() ? "none" : ""' in S)
chk('autobot hiding kept', 'if (a) a.style.display = ready() ? "none" : "";' in S)
chk('fake() is still called in paint()', 'function paint() {\n    fake();' in S)
chk('brief note kept', 'Sample data. It describes a past week, it does not forecast the next one.' in S)
chk('guarded when the card is missing', 'w && w.closest ? w.closest(".card") : null; if (c)' in S)
print('%d/%d passed' % (ok, ok + bad))
sys.exit(1 if bad else 0)
