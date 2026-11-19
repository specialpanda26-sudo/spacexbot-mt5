"""R8 multi-entry. Only adds: a signals.grp column, backend/multi.py settings, group-aware exposure and loss streak, and a Deriv loop that opens every waiting entry.
With multi_entries = 1 (the default) nothing changes. Run once from the repo root."""
import sys
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if s.count(old) != 1: sys.exit('NOT FOUND exactly once in %s: %r' % (path, old[:70]))
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)

edit('backend/store.py', [
    ("for col in ('uid TEXT', 'broker TEXT'):", "for col in ('uid TEXT', 'broker TEXT', 'grp INTEGER'):"),
    ("ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker TEXT;\n", "ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker TEXT;\nALTER TABLE signals ADD COLUMN IF NOT EXISTS grp BIGINT;\n"),
    ("'feed_on': os.getenv('FEED_ON', '0'), ", "'multi_entries': os.getenv('MULTI_ENTRIES', '1'), 'multi_min_score': os.getenv('MULTI_MIN_SCORE', '3'), 'feed_on': os.getenv('FEED_ON', '0'), "),
])
edit('supabase_schema.sql', [
    ("ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker TEXT;", "ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker TEXT;\nALTER TABLE signals ADD COLUMN IF NOT EXISTS grp BIGINT;"),
])
edit('backend/app.py', [
    ("\nfrom . import lag\n", "\nfrom . import lag, multi\n"),
    ("    sid = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)',\n",
     "    n = multi.entries(uid, s['score']); base = links.risk(uid) if uid else st.fget('risk_pct')          # R8: 1 unless the owner allows more and the setup is strong\n    sid = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)',\n"),
    ("links.risk(uid) if uid else st.fget('risk_pct'), s['strategy']", "multi.share(base, n), s['strategy']"),
    ("    lag.created(sid, m15[-1]['t'], uid)\n",
     "    lag.created(sid, m15[-1]['t'], uid)\n"
     "    if n > 1:\n"
     "        st.x('UPDATE signals SET grp=? WHERE id=?', (sid, sid))\n"
     "        for _ in range(n - 1):\n"
     "            sib = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',\n"
     "                       (sym, s['side'], s['entry'], s['sl'], s['tp'], multi.share(base, n), s['strategy'], s['score'], 'pending', int(time.time()), uid or None, sid))\n"
     "            lag.created(sib, m15[-1]['t'], uid)\n"
     "        print('multi-entry', sym, s['side'], n, 'entries sharing', base, 'percent')\n"),
])
edit('backend/risk.py', [
    ("def exposure(uid=''):", "def _setups(rows):\n    \"\"\"R8: entries opened together for one setup (same grp) count as ONE result; their profit and loss are added up.\"\"\"\n    out, at = [], {}\n    for x in rows:\n        g = x['grp']\n        if g and g in at: at[g]['pnl'] += x['pnl']; continue\n        o = {'pnl': x['pnl'], 'closed': x['closed']}; out.append(o)\n        if g: at[g] = o\n    return out\n\ndef exposure(uid=''):"),
    ("    net = {}\n    for r in st.q(\"SELECT symbol,side FROM signals WHERE status IN('pending','sent','open') AND COALESCE(uid,'')=?\", (uid,)):\n        for c, v in",
     "    net, seen = {}, set()\n    for r in st.q(\"SELECT id,symbol,side,grp FROM signals WHERE status IN('pending','sent','open') AND COALESCE(uid,'')=?\", (uid,)):\n        k = r['grp'] or -r['id']          # R8: every entry of one setup counts once\n        if k in seen: continue\n        seen.add(k)\n        for c, v in"),
    ("    last = st.q(\"SELECT pnl,closed FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? ORDER BY closed DESC LIMIT ?\", (uid, k))\n",
     "    last = _setups(st.q(\"SELECT pnl,closed,grp FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? ORDER BY closed DESC LIMIT ?\", (uid, k * 12)))[:k]\n"),
])
edit('backend/deriv.py', [
    ("def _trade(sess, uid, acct, bal, now):\n", "def _trade_one(sess, uid, acct, bal, now):\n"),
    ("def _track(sess, uid, acct):",
     "def _trade(sess, uid, acct, bal, now):\n"
     "    \"\"\"R8: open every entry that is waiting (up to 12), one after the other, so a multi-entry setup is not spread over minutes.\n"
     "    Stops at once if one buy could not be confirmed (it stays 'sent') or nothing moved.\"\"\"\n"
     "    for _ in range(12):\n"
     "        pend = lambda: st.q(\"SELECT COUNT(*) n FROM signals WHERE uid=? AND status='pending'\", (uid,), True)['n']\n"
     "        before = pend()\n"
     "        if not before: return\n"
     "        _trade_one(sess, uid, acct, bal, now)\n"
     "        if pend() >= before or st.q(\"SELECT COUNT(*) n FROM signals WHERE uid=? AND status='sent'\", (uid,), True)['n']: return\n\n"
     "def _track(sess, uid, acct):"),
])
print('R8 multi-entry added')
