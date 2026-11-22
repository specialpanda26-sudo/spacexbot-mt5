"""X1: static/index.html + tests/test_x1.py. Every X / close works with ONE tap and never cancels something else.
1) closeOv / sxGo / closeSheet / closeCmd no longer wipe or hide something that was opened right after the close.
2) The back arrow on 'About you' no longer signs the person out (it only closes).
3) The banner X is a bigger target, stops the tap reaching the banner body, and phone buttons skip the double-tap delay."""
def rw(p, f):
    s = open(p, encoding='utf-8').read(); n = f(s)
    assert n != s, 'nothing changed in ' + p
    open(p, 'w', encoding='utf-8').write(n)
def rep(s, a, b):
    assert s.count(a) == 1, a[:60]
    return s.replace(a, b)
def page(s):
    s = rep(s, 'function closeOv(){ovEl.classList.remove("open");setTimeout(function(){ovEl.hidden=true;ovEl.innerHTML=""},300)}',
      'function closeOv(){var n=ovEl.firstChild;ovEl.classList.remove("open");setTimeout(function(){if(ovEl.firstChild!==n||ovEl.classList.contains("open"))return;ovEl.hidden=true;ovEl.innerHTML=""},300)}/*X1: a newer overlay is never wiped*/')
    s = rep(s, 'setTimeout(function(){ovEl.classList.remove("open");ovEl.hidden=true;ovEl.innerHTML=""},h?150:0)}',
      'var n=ovEl.firstChild;setTimeout(function(){if(ovEl.firstChild!==n)return;ovEl.classList.remove("open");ovEl.hidden=true;ovEl.innerHTML=""},h?150:0)}')
    s = rep(s, 'setTimeout(function(){w.hidden=true;if(lastFocus&&lastFocus.focus)lastFocus.focus({preventScroll:true})},reduce?0:400)}',
      'setTimeout(function(){if(w.classList.contains("open"))return;w.hidden=true;if(lastFocus&&lastFocus.focus)lastFocus.focus({preventScroll:true})},reduce?0:400)}')
    s = rep(s, 'w.classList.remove("open");setTimeout(function(){w.hidden=true},reduce?0:220)}',
      'w.classList.remove("open");setTimeout(function(){if(w.classList.contains("open"))return;w.hidden=true},reduce?0:220)}')
    s = rep(s, '$(".x",ovEl).onclick=function(){if(cb){back&&back();return}SXA.signOut();U=null;slot();auth("login")};',
      '$(".x",ovEl).onclick=function(){if(cb){back&&back();return}closeOv()};/*X1: Back no longer signs out*/')
    s = rep(s, 'el.addEventListener("click",function(e){var g=el.dataset.go;hide();if(e.target.closest(".x")||!g)return;',
      'el.addEventListener("click",function(e){var g=el.dataset.go;hide();if(e.target.closest(".x")){e.stopPropagation();return}if(!g)return;')
    s = rep(s, '.sxbn .x{border:0;background:none;color:#9AA5BF;font:900 22px/1 var(--font);width:34px;height:34px;border-radius:10px}',
      '.sxbn .x{border:0;background:none;color:#9AA5BF;font:900 22px/1 var(--font);width:44px;height:44px;margin:-6px -4px -6px 0;border-radius:12px;touch-action:manipulation}\n.sxbn,.icon-btn,.ov .x,.up-ov button,button.x{touch-action:manipulation}')
    return s
rw('static/index.html', page)
open('tests/test_x1.py', 'w', encoding='utf-8').write('''"""Checks X1: every X closes with one tap and never cancels something else. Plain python. Run: python tests/test_x1.py"""
import os, sys
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
T('closeOv only wipes the overlay it was called for', 'function closeOv(){var n=ovEl.firstChild;' in S and 'if(ovEl.firstChild!==n||ovEl.classList.contains("open"))return;' in S)
T('sxGo only wipes the overlay it was called for', 'var n=ovEl.firstChild;setTimeout(function(){if(ovEl.firstChild!==n)return;' in S)
T('closeSheet and closeCmd do not hide a sheet reopened in the meantime', 'if(w.classList.contains("open"))return;w.hidden=true;if(lastFocus' in S and 'if(w.classList.contains("open"))return;w.hidden=true},reduce?0:220)' in S)
T('Back on About you no longer signs out', 'back&&back();return}closeOv()}' in S and 'SXA.signOut();U=null;slot();auth("login")};' not in S)
T('banner X only hides the banner (one tap, no tab jump)', 'if(e.target.closest(".x")){e.stopPropagation();return}if(!g)return;' in S)
T('banner X is a 44px target', 'width:44px;height:44px;margin:-6px -4px -6px 0' in S)
T('buttons skip the double-tap delay', 'touch-action:manipulation' in S)
print('\\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
''')
print('X1 applied')
