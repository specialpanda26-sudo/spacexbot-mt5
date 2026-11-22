"""LIVE1: the live 'Bot running' phone notification gets its on/off switch. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
A = 'backend/accounts.py'
edit(A, "NOTIF = ('trade', 'risk', 'news', 'daily', 'tips', 'system', 'billing')", "NOTIF = ('trade', 'risk', 'news', 'daily', 'tips', 'system', 'billing', 'live')", "'billing', 'live')")
edit(A, "'system': 1, 'billing': 1}", "'system': 1, 'billing': 1, 'live': 1}", "'billing': 1, 'live': 1}")
P = 'static/index.html'
edit(P, "pfT(\"n.tips\",\"Tips and updates\",\"New features and learning tips.\",n.tips)+'</div>'+",
        "pfT(\"n.tips\",\"Tips and updates\",\"New features and learning tips.\",n.tips)+pfT(\"n.live\",\"Live bot status\",\"A Bot running notification on your phone while the bot is on. Android app only.\",n.live==null?1:n.live)+'</div>'+", 'pfT("n.live"')
T = 'tests/test_accounts.py'
edit(T, "'system': 1, 'billing': 1} and j['prof']['av'] == 3)", "'system': 1, 'billing': 1, 'live': 1} and j['prof']['av'] == 3)", "'billing': 1, 'live': 1} and")
