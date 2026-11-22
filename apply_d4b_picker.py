"""D4b: FBS / Deriv MT5 picker on the Take button + label on the running card. Run: python apply_d4b_picker.py
Safe to run twice. If an old text is not found exactly once, NOTHING is changed."""
import os, sys, subprocess
I, J = 'static/index.html', 'static/running.js'
VAR = 'var D = null, ERR = "", BUSY = false, UID = null, SIG = "", RES = null;'
FN = '''var ACCT = "FBS";      /* which MT5 account the next Take is for (a label only) */
  function acctPick() {
    var h = '<div class="jrow" style="margin-top:8px"><span class="note" style="align-self:center">Taking it on:</span>';
    ["FBS", "Deriv MT5"].forEach(function (n) { h += '<button class="btn' + (ACCT === n ? " primary" : "") + '" type="button" data-act="acct" data-a="' + n + '">' + n + "</button>"; });
    return h + "</div>";
  }
  '''
TK = 'h += \'<div class="jrow"><button class="btn primary" data-act="take" data-id="\''
AP = '{ return api("/api/assist/take", "POST", { id: id }); }'
RS = 'if (a === "res") { RES = { id: id'
E = [
 (I, VAR, FN + VAR, 'function acctPick'),
 (I, TK, TK.replace("h += ", "h += acctPick() + ", 1), 'acctPick() +'),
 (I, AP, AP.replace('{ id: id }', '{ id: id, acct: ACCT }'), 'acct: ACCT'),
 (I, RS, 'if (a === "acct") { ACCT = b.dataset.a === "Deriv MT5" ? "Deriv MT5" : "FBS"; return paint(true); }\n    ' + RS, 'a === "acct"'),
 (J, 'esc(span(t.minutes))', '(t.acct ? esc(t.acct) + " \\u00b7 " : "") + esc(span(t.minutes))', 't.acct ?'),
]
files, bad = {}, []
for p, old, new, mk in E:
    t = files.get(p)
    if t is None: t = files[p] = open(p, encoding='utf-8').read()
    if mk in t: print('skip (already there):', p, mk); continue
    if t.count(old) != 1: bad.append((p, old[:50], t.count(old))); continue
    files[p] = t.replace(old, new, 1); print('edited:', p, mk)
if bad:
    for b in bad: print('STOP: old text found %d times in %s -> %s' % (b[2], b[0], b[1]))
    print('Nothing was changed.'); sys.exit(1)
for p, t in files.items():
    open(p + '.new', 'w', encoding='utf-8').write(t); os.replace(p + '.new', p)
print('edits done. Running the related tests...')
fl = ['tests/' + f for f in sorted(os.listdir('tests')) if f.startswith('test_') and f.endswith('.py') and 'assist' in open('tests/' + f, encoding='utf-8').read()]
fl += [x for x in ('tests/test_d3.py', 'tests/test_d3b.py', 'tests/test_d4.py', 'tests/test_d4b.py') if x not in fl]
fails = []
for f in fl:
    print('running', f, flush=True)
    ok = lambda: subprocess.run([sys.executable, f], capture_output=True, text=True, timeout=120).returncode == 0
    try:
        if not ok() and not ok(): fails.append(f); print('FAIL', f)
    except subprocess.TimeoutExpired: fails.append(f); print('TIMEOUT', f)
print('RESULT:', 'ALL RELATED TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
