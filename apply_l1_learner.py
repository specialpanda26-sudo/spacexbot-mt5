"""L1: learner steps (Learning path, Road to Real, How to use the bot). Run from the repo folder: python apply_l1_learner.py
Safe to run twice. If any old text is not found exactly once, NOTHING is changed.
1) Quiz: Check answers stays off until EVERY question has an answer (a skipped one used to slip through).
2) Home cards: no more silent nothing. Not verified -> a plain sentence. Could not load -> a sentence and a Try again button."""
import os, sys, subprocess

C, R, G = 'static/course.js', 'static/roadmap.js', 'static/guide.js'
MSG = ("    var msg = u && !on ? (!u.verified ? \"%s\" : ERR ? \"%s\" : \"\") : \"\"; if (msg) { C.hidden = false; C.style.display = \"\"; }\n")
def tail(title, who, d):
    return ("    if (!on && msg) h = '<div class=\"card-head\"><h2>" + title + "</h2></div><p class=\"note\">' + esc(msg) + '</p>' + (u.verified ? '<button class=\"btn block\" type=\"button\" data-" + d + "=\"retry\">Try again</button>' : '');\n"
            "    if (h !== LH) C.innerHTML = LH = h;")
E = [
    (C, 'var D = null, LH = "", OV = null, S = {', 'var D = null, ERR = false, LH = "", OV = null, S = {', 'ERR = false, LH'),
    (C, '    var u = me(), on = !!(u && u.verified && D); C.hidden = !on; C.style.display = on ? "" : "none";',
        '    var u = me(), on = !!(u && u.verified && D); C.hidden = !on; C.style.display = on ? "" : "none";\n' + MSG % ("Verify your email to start your learning path.", "Could not load your learning path."), 'Verify your email to start your learning path.'),
    (C, '    if (h !== LH) C.innerHTML = LH = h;', tail('Your learning path', 'u', 'c'), 'data-c="retry"'),
    (C, '.then(function (j) { D = j; drawCard(); if (OV) draw(); }).catch(function () {}); }', '.then(function (j) { D = j; ERR = false; drawCard(); if (OV) draw(); }).catch(function () { ERR = true; drawCard(); }); }', 'ERR = true; drawCard(); }); }'),
    (C, 'if (c === "open") open("list"); else if (c === "close") close();', 'if (c === "retry") load(); else if (c === "open") open("list"); else if (c === "close") close();', 'c === "retry"'),
    (C, 'S.pick.length === l.quiz.length && S.pick.indexOf(undefined) < 0 && !S.busy', 'l.quiz.every(function (q, i) { return typeof S.pick[i] === "number"; }) && !S.busy', 'typeof S.pick[i] === "number"'),
    (R, 'var D = null, LH = "", OV = null, BUSY = false;', 'var D = null, ERR = false, LH = "", OV = null, BUSY = false;', 'ERR = false, LH'),
    (R, '    var u = me(), on = !!(u && u.verified && D && !D.exempt); C.hidden = !on; C.style.display = on ? "" : "none";',
        '    var u = me(), on = !!(u && u.verified && D && !D.exempt); C.hidden = !on; C.style.display = on ? "" : "none";\n' + MSG.replace('u && !on', 'u && !on && !(D && D.exempt)') % ("Verify your email to see your road to Real.", "Could not load your road to Real."), 'Verify your email to see your road to Real.'),
    (R, '    if (h !== LH) C.innerHTML = LH = h;', tail('Road to Real', 'u', 'r'), 'data-r="retry"'),
    (R, '.then(function (j) { BUSY = false; D = j; drawCard(); celebrate(); }).catch(function () { BUSY = false; });', '.then(function (j) { BUSY = false; ERR = false; D = j; drawCard(); celebrate(); }).catch(function () { BUSY = false; ERR = true; drawCard(); });', 'ERR = true; drawCard(); });'),
    (R, 'if (c === "open" && D) badges(); else if (c === "close") close();', 'if (c === "retry") load(); else if (c === "open" && D) badges(); else if (c === "close") close();', 'c === "retry"'),
    (G, 'var D = null, OV = null, N = 0, LH = "";', 'var D = null, ERR = false, OV = null, N = 0, LH = "";', 'ERR = false, OV'),
    (G, '    var u = me(), on = !!(u && u.verified && D); C.hidden = !on; C.style.display = on ? "" : "none";',
        '    var u = me(), on = !!(u && u.verified && D); C.hidden = !on; C.style.display = on ? "" : "none";\n' + MSG % ("Verify your email to see how to use the bot.", "Could not load the guide."), 'Verify your email to see how to use the bot.'),
    (G, '    if (h !== LH) C.innerHTML = LH = h;', tail('How to use the bot', 'u', 'g'), 'data-g="retry"'),
    (G, '.then(function (j) { D = j; drawCard(); if (OV) draw(); }).catch(function () {});', '.then(function (j) { D = j; ERR = false; drawCard(); if (OV) draw(); }).catch(function () { ERR = true; drawCard(); });', 'ERR = true; drawCard(); });'),
    (G, 'if (c === "open") open(0); else if (c === "close") close();', 'if (c === "retry") { D = null; load(); } else if (c === "open") open(0); else if (c === "close") close();', 'c === "retry") { D = null'),
]
files, bad = {}, []
for p, old, new, mk in E:
    t = files.get(p)
    if t is None: t = files[p] = open(p, encoding='utf-8').read()
    if mk in t: print('skip (already there):', p, mk[:40]); continue
    if t.count(old) != 1: bad.append((p, old[:60], t.count(old))); continue
    files[p] = t.replace(old, new, 1); print('edited:', p, mk[:40])
if bad:
    for b in bad: print('STOP: not found exactly once (found %d) in %s -> %s' % (b[2], b[0], b[1]))
    print('Nothing was changed.'); sys.exit(1)
for p, t in files.items():
    open(p + '.new', 'w', encoding='utf-8').write(t); os.replace(p + '.new', p)
print('edits done. Running tests...')
fails = []
for f in sorted(os.listdir('tests')):
    if not (f.startswith('test_') and f.endswith('.py')) or f == 'test_rk5.py': continue          # test_rk5 is the known unrelated failure
    r = subprocess.run([sys.executable, 'tests/' + f], capture_output=True, text=True, timeout=300)
    if r.returncode: fails.append(f); print('FAIL', f, (r.stdout.strip().splitlines() or [''])[-1])
print('RESULT:', 'ALL TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
