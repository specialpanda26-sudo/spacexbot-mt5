"""Checks X1: every X closes with one tap and never cancels something else. Plain python. Run: python tests/test_x1.py"""
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
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
