"""Burst mode, Section 3 (basket close). tests/test_burst3.py is written just before this by the same command.
SERVER: a burst group now goes to the EA ALL AT ONCE as one 'basket' (not one entry per poll), and the EA may report the close reason 'basket'.
        One alert per group instead of one per entry.
EA:     SpaceXBridge.mq5 opens the whole group together, adds up the floating profit of the group, and closes the whole group when the profit
        reaches the target (USD per entry x entries opened) or when the give-back guard fires. It reports the close reason as basket.
        It also reports tp / sl / manual / bot for every other close (the server already accepted these; the EA never sent them).
An OLD EA with this server just ignores a basket (the entries expire after 3 minutes, nothing half-opens). A NEW EA with an OLD server works as before.
Each old text must be found exactly once or NOTHING is changed. Safe to run twice."""
import sys, os

BASKET_PY = '''def basket(s, uid=''):
    """If the pending signal `s` belongs to a burst group, return the WHOLE group for the EA: {gid, symbol, side, sl, tp, risk_pct, each, gb, ids:'1,2,3'}.
    Only entries still pending, of this person only. Anything that is not a burst group (a normal single trade, a normal multi-entry group) -> None."""
    if not s: return None
    g = (st.q('SELECT grp FROM signals WHERE id=?', (s['id'],), True) or {}).get('grp')
    m = meta(g) if g else None
    if not m: return None
    ids = [r['id'] for r in st.q("SELECT id FROM signals WHERE grp=? AND status='pending' AND COALESCE(uid,'')=? ORDER BY id", (g, uid or ''))]
    if not ids: return None
    return {'gid': int(g), 'symbol': s['symbol'], 'side': s['side'], 'sl': s['sl'], 'tp': s['tp'], 'risk_pct': s['risk_pct'],
            'each': m.get('each'), 'gb': m.get('gb', 0), 'ids': ','.join(str(i) for i in ids)}


# ---------------- what the app shows ----------------'''

SYNC_NEW = '''bk = burst.basket(s, who) if s else None          # a burst group goes out ALL AT ONCE as one basket (the old way would send one entry per poll)
    if bk:
        for i in bk['ids'].split(','): st.x("UPDATE signals SET status='sent' WHERE id=?", (int(i),)); lag.stamp(int(i), 'sent')
        return jsonify(signal=None, basket=bk, bot=links.bot_on(who), symbols=st.get('symbols'))
    if s: st.x("UPDATE signals SET status='sent' WHERE id=?", (s['id'],)); lag.stamp(s['id'], 'sent')'''

NOTE_A = '''bg = s.get('grp') if s.get('grp') and burst.meta(s['grp']) else None          # a burst group: ONE alert for the whole group, not one per entry
            kk = f'bg{bg}-{stt}' if bg else f'sig{sid}-{stt}'
            try: gp = float(d['gpnl']) if bg and d.get('gpnl') is not None else s['pnl']
            except (TypeError, ValueError): gp = s['pnl']
            title = f"{s['symbol']} {'burst ' if bg else ''}{'opened' if stt == 'open' else 'closed'}"'''

# ---------------------------------------------------------------- EA pieces (MQL5)
EA_INPUTS = r'''input long   Magic          = 5150150;
input int    BasketArmPct   = 30;      // BURST: the give-back guard only starts once the group profit reached this % of its target
input int    BasketCheckMs  = 500;     // BURST: how often open baskets are checked (milliseconds)'''

EA_BLOCK = r'''//--- BURST BASKET (Section 3): a burst group arrives all at once, is opened together and is closed together.
// A basket position carries the comment  SXB<signal id>G<group id>. The target, the give-back share and the best profit seen live in terminal
// global variables (SXB_T/B/P<gid>), so a restart of MT5 does not forget a basket that is still open. SXB_X<gid> = "closing now" (and when).
long CmNum(const string cm, int from)
{
   long v = 0; int n = StringLen(cm);
   for(int i = from; i < n; i++){ ushort ch = StringGetCharacter(cm, i); if(ch < '0' || ch > '9') break; v = v * 10 + (ch - '0'); }
   return v;
}
long CmId(const string cm){ return (StringFind(cm, "SXB") == 0) ? CmNum(cm, 3) : 0; }
long CmGid(const string cm){ int p = StringFind(cm, "G", 3); return (StringFind(cm, "SXB") == 0 && p > 0) ? CmNum(cm, p + 1) : 0; }
string GV(const string k, long gid){ return "SXB_" + k + (string)gid; }
void RejectAll(const long &ids[], string why){ for(int i = 0; i < ArraySize(ids); i++) Reject(ids[i], why); }

void ExecuteBasket(long gid, string canon, string side, double sl, double tp, double riskPct, double each, int gb, string idsCsv)
{
   string idl[]; int n = StringSplit(idsCsv, ',', idl); if(n <= 0) return;
   long ids[]; ArrayResize(ids, n); for(int i = 0; i < n; i++) ids[i] = (long)StringToInteger(idl[i]);
   if(!IsDemo() && !AllowLive){ RejectAll(ids, "live account blocked (AllowLive=false)"); return; }
   string sym = canon + SymbolSuffix;
   if(!SymbolSelect(sym, true)){ RejectAll(ids, "symbol not found"); return; }
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK), bid = SymbolInfoDouble(sym, SYMBOL_BID);
   if((ask - bid) / pt > MaxSpreadPoints){ RejectAll(ids, "spread too wide"); return; }
   bool buy = (side == "buy"); double price = buy ? ask : bid; int dg = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, dg); tp = NormalizeDouble(tp, dg);
   if(buy && !(sl < price && tp > price)){ RejectAll(ids, "SL/TP wrong side of price (stale signal)"); return; }
   if(!buy && !(sl > price && tp < price)){ RejectAll(ids, "SL/TP wrong side of price (stale signal)"); return; }
   double stopLvl = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   if(MathAbs(price - sl) < stopLvl || MathAbs(price - tp) < stopLvl){ RejectAll(ids, "inside broker stop level"); return; }
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0){ RejectAll(ids, "no tick value"); return; }
   // riskPct is ONE entry's share (the server already split the normal risk of one trade across the group)
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * riskPct / 100.0;
   double lotsRaw = riskMoney / ((MathAbs(price - sl) / ts) * tv);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double lots = MathFloor(lotsRaw / step + 1e-9) * step; int want = n;
   if(lots < mn)
   {  // one entry's share is below the smallest lot: open only as many minimum-lot entries as the TOTAL risk of the group allows
      want = (int)MathFloor(lotsRaw * n / mn + 1e-9); lots = mn;
      if(want < 2){ RejectAll(ids, "min lot too big for a group"); return; }
      if(want > n) want = n;
   }
   lots = MathMin(lots, MathMin(mx, MaxLots));
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   long okId[]; ulong okTk[]; double okPx[]; ArrayResize(okId, n); ArrayResize(okTk, n); ArrayResize(okPx, n); int k = 0;
   for(int i = 0; i < n; i++)
   {
      if(i >= want){ Reject(ids[i], "min lot: group trimmed to keep the risk"); continue; }
      string cm = "SXB" + (string)ids[i] + "G" + (string)gid;
      bool ok = buy ? trade.Buy(lots, sym, 0, sl, tp, cm) : trade.Sell(lots, sym, 0, sl, tp, cm);
      if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      { okId[k] = ids[i]; okTk[k] = trade.ResultOrder(); okPx[k] = trade.ResultPrice(); k++; }
      else Reject(ids[i], "order failed " + (string)trade.ResultRetcode());
   }
   if(k > 0)
   {  // remember the basket BEFORE the slow reports, so the profit watch can start at once
      GlobalVariableSet(GV("T", gid), each * k); GlobalVariableSet(GV("B", gid), (double)gb); GlobalVariableSet(GV("P", gid), 0.0);
      Print("Basket ", gid, ": ", k, " of ", n, " opened, ", DoubleToString(lots, 2), " lots each, target ", DoubleToString(each * k, 2), ", give-back ", gb, "%");
   }
   for(int i = 0; i < k; i++)
      Report(okId[i], "open", ",\"ticket\":" + (string)okTk[i] + ",\"lots\":" + DoubleToString(lots, 2) + ",\"price\":" + DoubleToString(okPx[i], dg));
}

void CloseBasket(long gid)
{
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      if(CmGid(PositionGetString(POSITION_COMMENT)) != gid) continue;
      if(!trade.PositionClose(tk, Deviation)) Print("Basket ", gid, ": close failed for ", tk, " retcode ", trade.ResultRetcode(), " (will retry)");
   }
}

void ManageBaskets()
{
   long g[]; double sum[]; int ng = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i); if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      long gid = CmGid(PositionGetString(POSITION_COMMENT)); if(gid <= 0) continue;
      double pr = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      int j = -1; for(int q = 0; q < ng; q++) if(g[q] == gid){ j = q; break; }
      if(j < 0){ j = ng; ng++; ArrayResize(g, ng); ArrayResize(sum, ng); g[j] = gid; sum[j] = 0; }
      sum[j] += pr;
   }
   for(int j = 0; j < ng; j++)
   {
      long gid = g[j];
      if(!GlobalVariableCheck(GV("T", gid))) continue;                                   // no target stored: not a basket this EA opened
      if(GlobalVariableCheck(GV("X", gid))){ CloseBasket(gid); continue; }               // already closing: finish it (retry what failed)
      double target = GlobalVariableGet(GV("T", gid)), gbp = GlobalVariableGet(GV("B", gid)), peak = GlobalVariableGet(GV("P", gid));
      if(sum[j] > peak){ peak = sum[j]; GlobalVariableSet(GV("P", gid), peak); }
      bool hit = (sum[j] >= target);
      bool back = (!hit && gbp > 0 && peak >= target * BasketArmPct / 100.0 && sum[j] <= peak * (1.0 - gbp / 100.0));
      if(hit || back)
      {
         Print("Basket ", gid, hit ? " reached its target: " : " is giving the profit back: ", DoubleToString(sum[j], 2), " (best ", DoubleToString(peak, 2), ", target ", DoubleToString(target, 2), ") - closing the group");
         GlobalVariableSet(GV("S", gid), sum[j]); GlobalVariableSet(GV("X", gid), (double)TimeCurrent());
         CloseBasket(gid);
      }
   }
   // forget finished baskets (no position left, and long enough ago that every close was reported)
   for(int i = GlobalVariablesTotal() - 1; i >= 0; i--)
   {
      string nm = GlobalVariableName(i); if(StringFind(nm, "SXB_T") != 0) continue;
      long gid = (long)StringToInteger(StringSubstr(nm, 5)); bool live = false;
      for(int j = 0; j < ng; j++) if(g[j] == gid){ live = true; break; }
      if(live) continue;
      datetime now = TimeCurrent();
      if(now - GlobalVariableTime(nm) < 120) continue;
      if(GlobalVariableCheck(GV("X", gid)) && now - (datetime)GlobalVariableGet(GV("X", gid)) < 60) continue;
      GlobalVariableDel(GV("T", gid)); GlobalVariableDel(GV("B", gid)); GlobalVariableDel(GV("P", gid)); GlobalVariableDel(GV("X", gid)); GlobalVariableDel(GV("S", gid));
   }
}

int OnInit()'''

EA_TIMER = r'''void PollServer();
void OnTimer()
{
   ManageBaskets();                                                                    // burst baskets are watched every BasketCheckMs
   static uint lastPoll = 0;
   if(GetTickCount() - lastPoll < (uint)(PollSeconds * 1000)) return;                  // the server is still polled every PollSeconds
   lastPoll = GetTickCount(); PollServer();
}
void PollServer()'''

EA_BASKET_RX = r'''long bgid = (long)StringToInteger(JStr(res, "gid"));
   if(bgid > 0)   // a burst group arrived: all its entries at once
   {
      ExecuteBasket(bgid, JStr(res, "symbol"), JStr(res, "side"), StringToDouble(JStr(res, "sl")), StringToDouble(JStr(res, "tp")),
                    StringToDouble(JStr(res, "risk_pct")), StringToDouble(JStr(res, "each")), (int)StringToInteger(JStr(res, "gb")), JStr(res, "ids"));
      return;
   }
   long id = (long)StringToInteger(JStr(res, "id"));'''

EA_CLOSE = r'''if(sid > 0)
   {
      string why = "other";                                    // what really closed it
      if(gid > 0 && GlobalVariableCheck(GV("X", gid))) why = "basket";
      else if(dr == DEAL_REASON_TP) why = "tp";
      else if(dr == DEAL_REASON_SL) why = "sl";
      else if(dr == DEAL_REASON_CLIENT || dr == DEAL_REASON_MOBILE || dr == DEAL_REASON_WEB) why = "manual";
      else if(dr == DEAL_REASON_EXPERT) why = "bot";
      string extra = ",\"pnl\":" + DoubleToString(pnl, 2) + ",\"reason\":\"" + why + "\"";
      if(why == "basket" && GlobalVariableCheck(GV("S", gid))) extra += ",\"gpnl\":" + DoubleToString(GlobalVariableGet(GV("S", gid)), 2);
      Report(sid, "closed", extra);
   }'''

EDITS = [
 ('backend/burst.py', '# ---------------- what the app shows ----------------', BASKET_PY, 'def basket(s'),
 ('backend/app.py', 'if s: st.x("UPDATE signals SET status=\'sent\' WHERE id=?", (s[\'id\'],)); lag.stamp(s[\'id\'], \'sent\')', SYNC_NEW, 'bk = burst.basket(s, who)'),
 ('backend/app.py', "in ('tp', 'sl', 'manual', 'bot', 'other')", "in ('tp', 'sl', 'manual', 'bot', 'basket', 'other')", "'bot', 'basket', 'other'"),
 ('backend/app.py', 'title = f"{s[\'symbol\']} {\'opened\' if stt == \'open\' else \'closed\'}"', NOTE_A, "bg = s.get('grp')"),
 ('backend/app.py', 'body = f"{s[\'side\'].upper()} lots {s[\'lots\']}" if stt == \'open\' else f"P/L {s[\'pnl\']}"',
  'body = f"{s[\'side\'].upper()} lots {s[\'lots\']}" if stt == \'open\' else f"{\'Burst \' if bg else \'\'}P/L {gp}"', "{'Burst ' if bg else ''}P/L {gp}"),
 ('backend/app.py', "sbauth.notify(title, body, key=f'sig{sid}-{stt}', only=only)", "sbauth.notify(title, body, key=kk, only=only)", 'body, key=kk'),
 ('backend/app.py', "if stt == 'open': push.notify(1, f'sig{sid}-open',", "if stt == 'open': push.notify(1, kk,", 'push.notify(1, kk,'),
 ('backend/app.py', "f'sig{sid}-closed', sym=s['symbol'], pnl=s['pnl'], **aud)", "kk, sym=s['symbol'], pnl=gp, **aud)", "kk, sym=s['symbol'], pnl=gp"),
 ('tests/test_reason1.py', "app_src.count('rsn.pack(s)') == 1 and", "app_src.count('rsn.pack(s)') == 2 and", "app_src.count('rsn.pack(s)') == 2"),          # Section 2's burst scan is a second place that saves the reason
 ('ea/SpaceXBridge.mq5', '#property version "1.00"', '#property version "1.10"', 'version "1.10"'),
 ('ea/SpaceXBridge.mq5', 'input long   Magic          = 5150150;', EA_INPUTS, 'BasketArmPct'),
 ('ea/SpaceXBridge.mq5', 'int OnInit()', EA_BLOCK, 'void ExecuteBasket('),
 ('ea/SpaceXBridge.mq5', 'EventSetTimer(PollSeconds);', 'EventSetMillisecondTimer(BasketCheckMs);', 'EventSetMillisecondTimer'),
 ('ea/SpaceXBridge.mq5', 'void OnTimer()', EA_TIMER, 'void PollServer()'),
 ('ea/SpaceXBridge.mq5', 'long id = (long)StringToInteger(JStr(res, "id"));', EA_BASKET_RX, 'long bgid ='),
 ('ea/SpaceXBridge.mq5', 'long en = HistoryDealGetInteger(t.deal, DEAL_ENTRY);', 'long en = HistoryDealGetInteger(t.deal, DEAL_ENTRY);\n   long dr = HistoryDealGetInteger(t.deal, DEAL_REASON);', 'long dr ='),
 ('ea/SpaceXBridge.mq5', 'double pnl = 0; long sid = 0;', 'double pnl = 0; long sid = 0, gid = 0;', 'long sid = 0, gid = 0;'),
 ('ea/SpaceXBridge.mq5', 'if(StringFind(cm, "SXB") == 0) sid = (long)StringToInteger(StringSubstr(cm, 3));', 'if(StringFind(cm, "SXB") == 0){ sid = CmId(cm); gid = CmGid(cm); }', 'sid = CmId(cm)'),
 ('ea/SpaceXBridge.mq5', 'if(sid > 0) Report(sid, "closed", ",\\"pnl\\":" + DoubleToString(pnl, 2));', EA_CLOSE, 'string why = "other";'),
]
if not os.path.isdir('backend') or not os.path.isdir('ea'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
if 'def look(' not in open('backend/burst.py', encoding='utf-8').read() or 'def _burst_scan(' not in open('backend/app.py', encoding='utf-8').read(): print('STOP: apply Sections 1 and 2 first'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:70]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
