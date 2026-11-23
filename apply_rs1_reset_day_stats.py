import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s: print('already done:', path, old[:40]); return
    if old not in s: sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
R = 'backend/risk.py'
sub(R, "def global_gate(now=None, uid='', burst=False):",
'''def day_since(uid='', now=None):
    """RS1: where today's loss count starts: the day start, or later when the person restarted it."""
    now = now or time.time(); base = int(now - now % 86400)
    try: t = int(float(st.get('dayok:' + (uid or '')) or 0))
    except (TypeError, ValueError): t = 0
    return max(base, t)

def global_gate(now=None, uid='', burst=False):''')
sub(R, "if bal and _pnl_since(since, uid) <= -bal * st.fget('max_daily_loss_pct') / 100:", "if bal and _pnl_since(day_since(uid, now), uid) <= -bal * st.fget('max_daily_loss_pct') / 100:")
sub('backend/risk_alerts.py', "risk._pnl_since(int(now - now % 86400), uid)", "risk._pnl_since(risk.day_since(uid, now), uid)")
A = 'backend/app.py'
sub(A, "bal = float(a.get('balance') or 0); since = st.day_start()\n    dpnl", "bal = float(a.get('balance') or 0); since = risk.day_since(sc)\n    dpnl")
sub(A, "@app.get('/api/trade/<int:tid>')",
'''def _may_reset(u):
    """RS1: the owner, or anyone on a confirmed demo account. A real account keeps its loss limits."""
    return bool(u['admin']) or st.acct(u['uid'] or '').get('demo') is True

@app.post('/api/risk/reset-day')
@need(verified=True)
def risk_reset_day_api(u):
    """RS1: today's loss count starts again from now. The daily loss limit stays on for every new loss."""
    if not _may_reset(u): return jsonify(error='On a real account the daily loss limit cannot be restarted here. Ask the owner.'), 403
    uid = _mine(u); st.put('dayok:' + uid, int(time.time()) + 1)
    return jsonify(ok=True)

@app.post('/api/stats/reset')
@need(verified=True)
def stats_reset_api(u):
    """RS1: a person deletes THEIR OWN finished trades and starts from zero. Open and waiting trades stay. Owner: use Clear all trades."""
    if u['admin']: return jsonify(error='Owner: use Clear all trades.'), 400
    if not _may_reset(u): return jsonify(error='On a real account the stats cannot be reset here. Ask the owner.'), 403
    uid = u['uid'] or ''
    if not uid: return jsonify(error='No account'), 400
    ids = [r['id'] for r in st.q("SELECT id FROM signals WHERE COALESCE(uid,'')=? AND COALESCE(status,'') NOT IN (?,?,?)", (uid, 'open', 'pending', 'sent'))]
    n = 0
    for i in range(0, len(ids), 200):
        part = ids[i:i + 200]; ph = ','.join('?' * len(part))
        n += st.x('DELETE FROM signals WHERE id IN (%s)' % ph, tuple(part), count=True) or 0
        st.x('DELETE FROM kv WHERE k IN (%s)' % ph, tuple('closedby:%s' % x for x in part))
    for k in ('pnlreset:%s' % uid, 'dayok:%s' % uid):
        st.x('DELETE FROM kv WHERE k=?', (k,))
    return jsonify(ok=True, trades=n)

@app.get('/api/trade/<int:tid>')''')
H = 'static/index.html'
sub(H, """if(u&&u.admin)h+='<div style="margin:8px 0"><button class="btn" id="jWipe">Clear all trades</button></div>';""",
       """if(u)h+='<div style="margin:8px 0"><button class="btn" id="jDay">Restart daily loss count</button>'+(u.admin?' <button class="btn" id="jWipe">Clear all trades</button>':' <button class="btn" id="jReset">Reset my stats</button>')+'</div>';""")
sub(H, 'function jn(){var el=$("#jNow");',
'''document.addEventListener("click",function(e){var b=e.target&&e.target.closest?e.target.closest("#jDay,#jReset"):null;if(!b)return;var day=b.id==="jDay";
 if(!confirm(day?"Restart today's loss count from now? The daily loss limit stays on for every new loss.":"Delete ALL your finished trades and start your stats from zero? This cannot be undone."))return;
 b.disabled=true;SXA.api(day?"/api/risk/reset-day":"/api/stats/reset",{method:"POST",body:{}}).then(function(j){alert(day?"Done. Today's loss count starts again from now.":"Cleared "+((j&&j.trades)||0)+" trades. Starting from zero.");b.disabled=false;try{SXJ.rows=[];SXJ.stats=null;SXJ.total=0;SXJ.pairs=[];jr();sr();renderTrades()}catch(x){}},function(){alert("Could not do that. On a real account only the owner can restart it.");b.disabled=false})});
function jn(){var el=$("#jNow");''')
print('RS1 done')
