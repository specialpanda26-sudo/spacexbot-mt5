import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s: print('already done:', path, old[:40]); return
    if old not in s: sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
J = 'backend/journal.py'
sub(J, "def snapshot(uid, admin=False, broker='', result='all', limit=LIMIT, now=None):",
'''def stats_from(uid):
    """RS2: seconds (UTC) from which the Journal numbers count, or 0 = everything."""
    try: return max(0, int(float(st.get('statsfrom:%s' % (uid or '')) or 0)))
    except (TypeError, ValueError): return 0


def snapshot(uid, admin=False, broker='', result='all', limit=LIMIT, now=None):''')
sub(J, "    return {'rows': shown, 'open': open_now(uid, admin), 'total': len(show), 'stats': numbers(rows), 'pairs': by_pair(rows),",
       "    cut = stats_from(uid); cnt = [r for r in rows if r['t'] >= cut] if cut else rows          # RS2\n    nums = numbers(cnt)\n    if cut: nums['from'] = cut\n    return {'rows': shown, 'open': open_now(uid, admin), 'total': len(show), 'stats': nums, 'pairs': by_pair(cnt),")
A = 'backend/app.py'
sub(A, "@app.get('/api/trade/<int:tid>')",
'''@app.post('/api/stats/restart')
@need(verified=True)
def stats_restart_api(u):
    """RS2: the Journal numbers count from now. {"undo": true} counts everything again. Deletes nothing and touches no limit."""
    key = 'statsfrom:%s' % (u['uid'] or '')
    if _j().get('undo'): st.x('DELETE FROM kv WHERE k=?', (key,))
    else: st.put(key, int(time.time()) + 1)
    return jsonify(ok=True)

@app.get('/api/trade/<int:tid>')''')
H = 'static/index.html'
sub(H, "+(u.admin?' <button class=\"btn\" id=\"jWipe\">Clear all trades</button>':' <button class=\"btn\" id=\"jReset\">Reset my stats</button>')+'</div>';",
       "+(u.admin?' <button class=\"btn\" id=\"jWipe\">Clear all trades</button>':' <button class=\"btn\" id=\"jReset\">Reset my stats</button>')+(s&&s.from?' <button class=\"btn\" id=\"jUndo\">Count all trades again</button>':' <button class=\"btn\" id=\"jFrom\">Start stats from now</button>')+'</div>'+(s&&s.from?'<div class=\"note\">Won, Lost and Net count only trades closed after '+new Date(s.from*1000).toLocaleString()+'. Nothing was deleted.</div>':'');")
sub(H, 'function jn(){var el=$("#jNow");',
'''document.addEventListener("click",function(e){var b=e.target&&e.target.closest?e.target.closest("#jFrom,#jUndo"):null;if(!b)return;var undo=b.id==="jUndo";
 b.disabled=true;SXA.api("/api/stats/restart",{method:"POST",body:undo?{undo:true}:{}}).then(function(){b.disabled=false;try{SXJ.rows=[];SXJ.stats=null;SXJ.total=0;SXJ.pairs=[];jr();sr();renderTrades()}catch(x){}},function(){alert("Could not do that. Check your connection and try again.");b.disabled=false})});
function jn(){var el=$("#jNow");''')
print('RS2 done')
