"""CH1: Chat tab shell. Offline static checks. Run: python tests/test_ch1.py (ends N/N passed)"""
import os, re, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
idx = open(os.path.join(R, 'static', 'index.html'), encoding='utf-8').read(); js = open(os.path.join(R, 'static', 'chat.js'), encoding='utf-8').read()
res = []
def T(n, ok): res.append((n, bool(ok)))
T('nav button for chat exists and starts hidden', re.search(r'<button data-go="chat" id="navChat" hidden>', idx))
T('view-chat section exists', 'id="view-chat"' in idx)
T('chat is a known view and a signed-in-only route', '"connect","chat"' in idx and 'connect|chat|' in idx)
T('chat.js is loaded by the page', '/static/chat.js' in idx)
T('tab is owner-only until OPEN is switched on', 'var OPEN = false;' in js and 'u.admin' in js)
T('messages are written with textContent, never innerHTML from the person', 'm.className' in js and 't.textContent = text' in js and 'innerHTML = text' not in js)
T('plug-in points for later sections are there', 'setReply' in js and 'tools: tools' in js)
T('uses site colour variables, no hard-coded brand colours', 'var(--green)' in js and 'var(--surface)' in js and not re.search(r'#[0-9a-fA-F]{6}', js))
bad = [n for n, ok in res if not ok]
for n, ok in res: print(('PASS ' if ok else 'FAIL ') + n)
print('%d/%d passed' % (len(res) - len(bad), len(res))); sys.exit(1 if bad else 0)
