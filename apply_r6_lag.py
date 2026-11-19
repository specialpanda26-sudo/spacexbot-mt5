"""R6 step 1: hook the timing notes into the EA path and the Deriv path. Only adds lines. Run once from the repo root."""
import re, sys
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if s.count(old) != 1: sys.exit('NOT FOUND exactly once in %s: %r' % (path, old[:60]))
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)

edit('backend/app.py', [
    ("\n_last_scan = {}", "\nfrom . import lag\n_last_scan = {}"),
    ("    botstate.note(uid, sym, 'signal')\n", "    lag.created(sid, m15[-1]['t'], uid)\n    botstate.note(uid, sym, 'signal')\n"),
    ("    for sym in bz:\n        try: _scan(sym, who)", "    if bz: lag.got(who, 'ea')\n    for sym in bz:\n        try: _scan(sym, who)"),
    ("    if s: st.x(\"UPDATE signals SET status='sent' WHERE id=?\", (s['id'],))\n", "    if s: st.x(\"UPDATE signals SET status='sent' WHERE id=?\", (s['id'],)); lag.stamp(s['id'], 'sent')\n"),
    ("    if stt == 'open': st.x(\"UPDATE signals SET status='open',ticket=?", "    if stt == 'open': lag.stamp(sid, 'opened')\n    if stt == 'open': st.x(\"UPDATE signals SET status='open',ticket=?"),
    ("@app.get('/api/plans')\n", "@app.get('/api/admin/lag')\n@need(admin=True)\ndef admin_lag(u): return jsonify(lag.report())\n\n@app.get('/api/plans')\n"),
])
edit('backend/deriv.py', [
    ("from . import store as st, brokers as bk, bars, links, push, sbauth, learn\n", "from . import store as st, brokers as bk, bars, links, push, sbauth, learn, lag\n"),
    ("                    if rows: bars.merge(sym, tf, rows, uid=uid)\n                scan(sym, uid)", "                    if rows: bars.merge(sym, tf, rows, uid=uid)\n                lag.got(uid, 'deriv')\n                scan(sym, uid)"),
    ("claimed: nobody else can buy this signal\n", "claimed: nobody else can buy this signal\n    lag.stamp(s['id'], 'sent')\n"),
    ("    if kind == 'open':\n        st.x(\"UPDATE signals SET status='open',ticket=?,lots=?,fill=?,note=?,broker='Deriv'", "    if kind == 'open':\n        lag.stamp(s['id'], 'opened')\n        st.x(\"UPDATE signals SET status='open',ticket=?,lots=?,fill=?,note=?,broker='Deriv'"),
])
print('R6 step 1 hooks added')
