"""QP1: 'Take small profits' (a per-person switch + a USD number). When on, each position the bot opened closes by itself as soon as ITS OWN profit reaches the number.
 - backend/quickprofit.py (new file, cat it first): kv 'qp:<uid>' {on, usd}; usd_for(uid) is what the closers use (0 = off, or paused by the owner's manual_close).
 - backend/app.py: GET/POST /api/quickprofit; /api/ea/sync sends qp (USD, 0 = off) to the MT5 bridge on every poll; the EA close reason 'quick' is accepted.
 - backend/deriv.py: _track sells an open Deriv trade at market when its live profit reaches the number (closedby 'quick').
 - ea/SpaceXBridge.mq5 (version 1.22): ManageQuick() runs twice a second and closes every SXB position whose profit + swap reaches qp.
 - static/index.html: loads static/quick_ui.js (new file, cat it first), the card on the Bot tab.
Run from the repo root: python apply_qp1.py   Safe to run twice (a step already done says 'already ok'). Nothing is written if any step cannot find its place exactly once."""
import sys, os

EDITS = []
def edit(path, old, new):
    EDITS.append((path, old, new))

edit('backend/app.py', "from . import manual_close, burst_scope, btc_switch, tradeon, course, roadmap, guide, deriv_oauth, testlab\n",
     "from . import manual_close, burst_scope, btc_switch, tradeon, course, roadmap, guide, deriv_oauth, testlab\nfrom . import quickprofit          # QP1: take small profits\n")
edit('backend/app.py', "return jsonify(signal=None, basket=bk, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'))",
     "return jsonify(signal=None, basket=bk, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'), qp=quickprofit.usd_for(who))")
edit('backend/app.py', "return jsonify(signal=s, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'))",
     "return jsonify(signal=s, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'), qp=quickprofit.usd_for(who))")
edit('backend/app.py', "('tp', 'sl', 'manual', 'bot', 'basket', 'other')", "('tp', 'sl', 'manual', 'bot', 'basket', 'quick', 'other')")
edit('backend/app.py', "@app.get('/api/cycle')          # CY1: Auto-cycle choices\n",
'''@app.get('/api/quickprofit')          # QP1: take small profits
@need(verified=True)
def qp_get(u): return jsonify(quickprofit.view(_mine(u)))

@app.post('/api/quickprofit')
@need(verified=True)
def qp_set(u):
    j = _j()
    try: quickprofit.save(_mine(u), j)
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in quickprofit.KEYS}})
    return jsonify(quickprofit.view(_mine(u)))

@app.get('/api/cycle')          # CY1: Auto-cycle choices
''')

DV = "        if isinstance(p, dict) and str(p.get('is_sold')).lower() not in ('1', 'true'): live[r['id']] = p.get('profit')          # BX1\n"
edit('backend/deriv.py', DV, DV + '''        if isinstance(p, dict) and str(p.get('is_sold')).lower() not in ('1', 'true'):          # QP1: take small profits, one trade at a time
            try:
                from . import quickprofit, deriv_group
                q = quickprofit.usd_for(uid); pr = float(p.get('profit'))
                if q > 0 and pr >= q:
                    fin = deriv_group._sell(sess, cid, pr)
                    if fin is not None and st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=? AND status='open'", (fin, int(time.time()), r['id']), True):
                        st.put('closedby:%d' % r['id'], 'quick'); live.pop(r['id'], None); _report(uid, r['id'], 'closed', 'tp' if fin > 0 else 'other'); done = True; continue
            except ConnectionError: raise
            except Exception as e: print('[deriv] quick profit failed', repr(e)[:100])
''')

EA = 'ea/SpaceXBridge.mq5'
edit(EA, '#property version "1.21"', '#property version "1.22"')
edit(EA, "datetime lastBars = 0; bool firstPush = true;\n",
     "datetime lastBars = 0; bool firstPush = true;\ndouble QuickUsd = 0;          // QP1: take small profits. The server sends it on every poll (USD per position, 0 = off)\n")
edit(EA, "void ManageBaskets()\n{", '''void ManageQuick()          // QP1: each of our positions closes by itself once its OWN profit (plus swap) reaches QuickUsd
{
   datetime now = TimeCurrent();
   for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)          // forget old "closed by small profit" marks (the close was reported long ago)
   {
      string nm = GlobalVariableName(i);
      if(StringFind(nm, "SXB_Q") == 0 && now - GlobalVariableTime(nm) > 300) GlobalVariableDel(nm);
   }
   if(QuickUsd <= 0) return;
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      if(StringFind(PositionGetString(POSITION_COMMENT), "SXB") != 0) continue;
      double pr = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      if(pr < QuickUsd) continue;
      string qn = "SXB_Q" + (string)PositionGetInteger(POSITION_IDENTIFIER);
      GlobalVariableSet(qn, (double)now);
      if(trade.PositionClose(tk, Deviation)) Print("Small profit: closed position ", tk, " at ", DoubleToString(pr, 2), " (limit ", DoubleToString(QuickUsd, 2), ")");
      else { GlobalVariableDel(qn); Print("Small profit: close failed for ", tk, " retcode ", trade.ResultRetcode(), " (will retry)"); }
   }
}

void ManageBaskets()
{''')
edit(EA, "   ManageBaskets();", "   ManageQuick();                                                                      // QP1: small profits are taken here, twice a second\n   ManageBaskets();")
edit(EA, '   if(bars != "") firstPush = false;\n', '   if(bars != "") firstPush = false;\n   QuickUsd = StringToDouble(JStr(res, "qp"));                                         // QP1: 0 when the person has it off (or an old server sends nothing)\n')
edit(EA, '      if(gid > 0 && GlobalVariableCheck(GV("X", gid))) why = "basket";',
     '      if(GlobalVariableCheck("SXB_Q" + (string)pid)) why = "quick";                       // QP1: closed by the small-profit switch\n      else if(gid > 0 && GlobalVariableCheck(GV("X", gid))) why = "basket";')

edit('static/index.html', '<script src="/static/share_ui.js"></script>', '<script src="/static/share_ui.js"></script><script src="/static/quick_ui.js"></script>')

for need_file in ('backend/quickprofit.py', 'static/quick_ui.js'):
    if not os.path.exists(need_file): sys.exit('STOP: %s is missing. Create it first (the cat command), then run this again.' % need_file)

# plan first: nothing is written unless every step is clear
files, plan = {}, []
for path, old, new in EDITS:
    if path not in files: files[path] = open(path, encoding='utf-8').read()
    s = files[path]
    if new in s: plan.append((path, 'ok')); continue
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:70].replace('\n', ' ')))
    files[path] = s.replace(old, new); plan.append((path, 'edit'))
changed = {p for p, a in plan if a == 'edit'}
for p in sorted(changed): open(p, 'w', encoding='utf-8', newline='').write(files[p]); print(p, ': edited')
if not changed: print('already ok, nothing to do')
