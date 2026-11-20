"""Clear 1: (a) the Journal tab shows Won / Lost / Net / Win rate at the top (new numbers 'won' and 'lost' in GET /api/journal);
(b) owner-only 'Clear all trades' button (POST /api/admin/clear-trades, body {"confirm":"CLEAR"}) that deletes the owner's finished trades
(closed / cancelled / expired) and the matching Journal and Stats numbers, so everything restarts from zero. Open and waiting trades are KEPT
(a live trade is never orphaned). Other people's trades are never touched. NOT undoable.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
import os, sys, subprocess

J = 'backend/journal.py'; A = 'backend/app.py'; H = 'static/index.html'; T = 'tests/test_all.py'

ENDPOINT = r'''@app.post('/api/admin/clear-trades')
@need(admin=True)
def clear_trades_api(u):
    """Owner only: delete this owner's FINISHED trades (closed / cancelled / expired) so the Journal and Stats restart from zero. Open and waiting trades are
    kept. Rows another person's phone-mode log still points at are kept too. Body must be {"confirm": "CLEAR"}. Not undoable."""
    j = _j()
    if str(j.get('confirm') or '') != 'CLEAR': return jsonify(error='send {"confirm": "CLEAR"}'), 400
    uid = u['uid'] or ''
    base = "FROM signals WHERE COALESCE(uid,'') IN (?,?) AND COALESCE(status,'') NOT IN (?,?,?)"
    args = ('', uid, 'open', 'pending', 'sent')
    try: ids = [r['id'] for r in st.q('SELECT id ' + base + ' AND id NOT IN (SELECT sid FROM assist_log WHERE uid<>?)', args + (uid,))]
    except Exception: ids = [r['id'] for r in st.q('SELECT id ' + base, args)]
    n = 0
    for i in range(0, len(ids), 200):
        part = ids[i:i + 200]; ph = ','.join('?' * len(part))
        n += st.x('DELETE FROM signals WHERE id IN (%s)' % ph, tuple(part), count=True) or 0
        st.x('DELETE FROM kv WHERE k IN (%s)' % ph, tuple('closedby:%s' % x for x in part))
    if uid:
        try: st.x('DELETE FROM assist_log WHERE uid=?', (uid,))
        except Exception: pass
    st.x('DELETE FROM kv WHERE k=?', ('pnlreset:%s' % uid,))
    return jsonify(ok=True, trades=n)

'''

JSUM = r'''function jsum(){var s=SXJ.stats,u=null,h="";try{u=SXA.user()}catch(e){}
 if(SXJ.state==="ok"&&s&&s.trades)h='<div class="stats">'+kp("Won",m2(s.won))+kp("Lost",m2(-s.lost))+kp("Net",m2(s.net))+kp("Win rate",s.win_rate.toFixed(1)+"%")+'</div><div class="note">'+s.wins+" wins · "+s.losses+" losses · "+s.trades+" closed trades</div>";
 if(u&&u.admin)h+='<div style="margin:8px 0"><button class="btn" id="jWipe">Clear all trades</button></div>';
 return h}
document.addEventListener("click",function(e){var b=e.target&&e.target.closest?e.target.closest("#jWipe"):null;if(!b)return;
 if(!confirm("Delete ALL your finished trades and their win/loss numbers? This cannot be undone."))return;
 if(!confirm("Last check: clear everything and start from zero?"))return;
 b.disabled=true;
 SXA.api("/api/admin/clear-trades",{method:"POST",body:{confirm:"CLEAR"}}).then(function(j){alert("Cleared "+((j&&j.trades)||0)+" trades. Starting from zero.");b.disabled=false;try{SXJ.rows=[];SXJ.stats=null;SXJ.total=0;SXJ.pairs=[];jr();sr();renderTrades()}catch(x){}},function(){alert("Could not clear. Are you signed in as the owner?");b.disabled=false})});
function jr(){var f=X.jf'''

EDITS = [
 (J, "'net': round(gp - gl, 2), 'per_trade'", "'won': round(gp, 2), 'lost': round(gl, 2), 'net': round(gp - gl, 2), 'per_trade'"),
 (A, "@app.get('/api/trade/<int:tid>')\n", ENDPOINT + "@app.get('/api/trade/<int:tid>')\n"),
 (H, "function jr(){var f=X.jf", JSUM),
 (H, ' $("#jList").innerHTML=L.slice(0,60)', ' $("#jList").innerHTML=jsum()+(L.slice(0,60)'),
 (H, """:"Nothing here yet.")+'</p>'}""", """:"Nothing here yet.")+'</p>')}"""),
]

def main():
    files = {}
    for f, old, new in EDITS:
        if f not in files:
            if not os.path.exists(f): print('STOP: missing', f, '(run from the repo folder)'); return 1
            files[f] = open(f, encoding='utf-8').read()
    done = 0
    for i, (f, old, new) in enumerate(EDITS, 1):
        c = files[f].count(old)
        if files[f].count(new) >= 1 and (c == 0 or new.count(old) >= 1): pass
        elif c == 1: files[f] = files[f].replace(old, new); done += 1
        else: print('STOP: edit %d does not fit %s (found %d times). Nothing changed.' % (i, f, c)); return 1
    for f, txt in files.items():
        with open(f + '.new', 'w', encoding='utf-8') as h: h.write(txt)
    for f in files: os.replace(f + '.new', f)
    print('edits applied: %d of %d (the rest were already there)' % (done, len(EDITS)))
    r = subprocess.run([sys.executable, T], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print('\n'.join(l for l in out if l.startswith('FAIL')) or '(no failing test)')
    print(out[-1] if out else 'no test output'); print('RESULT:', 'OK' if r.returncode == 0 else 'TESTS FAILED')
    return r.returncode

sys.exit(main())
