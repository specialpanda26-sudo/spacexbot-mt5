//+------------------------------------------------------------------+
//| SpaceXBridge.mq5 - polls your Render backend, places its signals |
//| Setup: Tools > Options > Expert Advisors > tick "Allow WebRequest"|
//| and add your Render URL to the list. Attach to ANY chart.        |
//+------------------------------------------------------------------+
#property strict
#property version "1.26"
#define EA_VERSION "1.26"          // keep the same as #property version above: it is sent to the app so the app can say Up to date / Update available
#include <Trade\Trade.mqh>

input string ServerUrl      = "https://your-service.onrender.com"; // no trailing slash
input string EAKey          = "change-me-long-random";             // same as EA_KEY on Render
input string Symbols        = "XAUUSD,EURUSD,GBPUSD,USDJPY";       // names WITHOUT broker suffix
input string SymbolSuffix   = "";                                  // e.g. "m" or ".r" if your broker adds one
input int    PollSeconds    = 5;
input int    BarsPushSeconds= 60;
input bool   AllowLive      = false;   // SAFETY: false = refuses to trade on a real-money account
input int    MaxSpreadPoints= 60;      // skip if spread wider than this (points)
input double MaxLots        = 1.0;     // cap for a NORMAL trade (sized by risk %)
input bool   StakeOn        = true;    // STAKE: strong setups use a bigger share of the balance as margin (the server sends the share)
input double MaxStakeLots   = 100.0;   // STAKE: cap for a big-stake trade (replaces MaxLots for those trades only)
input int    Deviation      = 20;
input long   Magic          = 5150150;
input int    BasketArmPct   = 30;      // BURST: the give-back guard only starts once the group profit reached this % of its target
input int    BasketCheckMs  = 500;     // BURST: how often open baskets are checked (milliseconds)

CTrade trade;
datetime lastBars = 0; bool firstPush = true;
double QuickUsd = 0;          // QP1: take small profits. The server sends it on every poll (USD per position, 0 = off)

//--- tiny JSON helpers (flat values only)
string JStr(const string js, const string key)
{
   int p = StringFind(js, "\"" + key + "\":"); if(p < 0) return "";
   p += StringLen(key) + 3;
   while(p < StringLen(js) && StringGetCharacter(js, p) == ' ') p++;
   if(StringGetCharacter(js, p) == '"'){ int e = StringFind(js, "\"", p + 1); if(e < 0) return ""; return StringSubstr(js, p + 1, e - p - 1); }
   int e = p;
   while(e < StringLen(js)){ ushort ch = StringGetCharacter(js, e); if(ch == ',' || ch == '}' || ch == ']') break; e++; }
   return StringSubstr(js, p, e - p);
}
string Post(const string path, const string body)
{
   char data[], res[]; string rh;
   StringToCharArray(body, data, 0, StringLen(body), CP_UTF8);
   string h = "Content-Type: application/json\r\nX-EA-Key: " + EAKey + "\r\n";
   ResetLastError();
   int code = WebRequest("POST", ServerUrl + path, h, 15000, data, res, rh);
   if(code < 0){ Print("WebRequest error ", GetLastError(), " - add ", ServerUrl, " in Tools>Options>Expert Advisors"); return ""; }
   if(code >= 300){ Print("Server answered HTTP ", code, " for ", path); return ""; }          // an error answer is a failure, not a result
   return CharArrayToString(res, 0, -1, CP_UTF8);
}
long UtcOffset()   // broker server time -> UTC, rounded to 15 min
{
   double off = (double)(TimeGMT() - TimeTradeServer());
   return (long)(MathRound(off / 900.0) * 900.0);
}
string BarsJson(const string sym, ENUM_TIMEFRAMES tf, int count)
{
   MqlRates r[]; long off = UtcOffset();
   int n = CopyRates(sym + SymbolSuffix, tf, 1, count, r);       // start 1 = closed candles only
   if(n <= 0) return "[]";
   string s = "[";
   for(int i = 0; i < n; i++)
   {
      if(i > 0) s += ",";
      s += "[" + (string)((long)r[i].time + off) + "," + DoubleToString(r[i].open, 5) + "," + DoubleToString(r[i].high, 5) + ","
         + DoubleToString(r[i].low, 5) + "," + DoubleToString(r[i].close, 5) + "," + (string)r[i].tick_volume + "]";
   }
   return s + "]";
}
int OurPositions()
{
   int c = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--){ ulong t = PositionGetTicket(i); if(PositionSelectByTicket(t) && PositionGetInteger(POSITION_MAGIC) == Magic) c++; }
   return c;
}
bool IsDemo(){ return AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO; }

input int ReportTries = 4;   // how many times a trade report (open/close) is sent before giving up
void Report(long id, string status, string extra)
{
   string body = "{\"id\":" + (string)id + ",\"status\":\"" + status + "\"" + extra + "}";
   int wait = 1500;
   for(int t = 1; t <= ReportTries; t++)
   {
      if(Post("/api/ea/report", body) != "") return;
      if(t < ReportTries){ Print("Report ", status, " for signal ", id, " not delivered (try ", t, " of ", ReportTries, "), trying again"); Sleep(wait); wait *= 2; }
   }
   Print("Report ", status, " for signal ", id, " could NOT be delivered. The server may miss this trade: ", body);
}
void Reject(long id, string why){ Print("Signal ", id, " rejected: ", why); Report(id, "rejected", ",\"reason\":\"" + why + "\""); }

// STAKE (Section 2): a big-stake position carries the comment SXB<id>S, so it is found again after a restart. Only ONE may be open at a time.
bool BigStakeOpen()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i); if(!PositionSelectByTicket(t)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      string cm = PositionGetString(POSITION_COMMENT); int n = StringLen(cm);
      if(StringFind(cm, "SXB") == 0 && n > 3 && StringGetCharacter(cm, n - 1) == 'S') return true;
   }
   return false;
}
// lots so that the MARGIN is about stakePct of the balance, then cut so the loss at the stop is at most maxRiskPct of the balance,
// then cut to the free margin, the broker max/step and MaxStakeLots. Returns 0 when it cannot be done (the caller then uses normal sizing).
double StakeLots(const string sym, bool buy, double price, double sl, double stakePct, double maxRiskPct, double tv, double ts, double step, double mn, double mx)
{
   if(stakePct <= 0 || step <= 0) return 0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE), m1 = 0;
   if(!OrderCalcMargin(buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, sym, 1.0, price, m1) || m1 <= 0) return 0;
   double byMargin = bal * stakePct / 100.0 / m1;
   double lossPerLot = (MathAbs(price - sl) / ts) * tv; if(lossPerLot <= 0) return 0;
   double byRisk = bal * maxRiskPct / 100.0 / lossPerLot;
   double byFree = AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.95 / m1;
   double lots = MathMin(MathMin(byMargin, byRisk), byFree);
   lots = MathMin(lots, MathMin(mx, MaxStakeLots));
   lots = MathFloor(lots / step + 1e-9) * step;
   return (lots >= mn) ? lots : 0;
}

void Execute(long id, string canon, string side, double sl, double tp, double riskPct, double stakePct = 0, double stakeMaxRisk = 10, double maxLot = 0, double fixedLot = 0, double maxLotSoft = 0, double tinyPct = 0)
{
   if(!IsDemo() && !AllowLive){ Reject(id, "live account blocked (AllowLive=false)"); return; }
   string sym = canon + SymbolSuffix;
   if(!SymbolSelect(sym, true)){ Reject(id, "symbol not found"); return; }
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK), bid = SymbolInfoDouble(sym, SYMBOL_BID);
   if((ask - bid) / pt > MaxSpreadPoints){ Reject(id, "spread too wide"); return; }
   bool buy = (side == "buy"); double price = buy ? ask : bid; int dg = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, dg); tp = NormalizeDouble(tp, dg);
   if(buy && !(sl < price && tp > price)){ Reject(id, "SL/TP wrong side of price (stale signal)"); return; }
   if(!buy && !(sl > price && tp < price)){ Reject(id, "SL/TP wrong side of price (stale signal)"); return; }
   double stopLvl = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   if(MathAbs(price - sl) < stopLvl || MathAbs(price - tp) < stopLvl){ Reject(id, "inside broker stop level"); return; }
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0){ Reject(id, "no tick value"); return; }
   if(tinyPct > 0)
   {  // LS5: tiny-account check: even the broker's smallest lot must not lose more than tinyPct % of the balance at the stop
      double balT = AccountInfoDouble(ACCOUNT_BALANCE), minLoss = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN) * (MathAbs(price - sl) / ts) * tv;
      if(balT > 0 && minLoss > balT * tinyPct / 100.0 + 1e-9){ Reject(id, "even the smallest lot would lose $" + DoubleToString(minLoss, 2) + " at the stop, more than " + DoubleToString(tinyPct, 1) + "% of the balance"); return; }
   }
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * riskPct / 100.0;
   double lots = riskMoney / ((MathAbs(price - sl) / ts) * tv);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(fixedLot > 0) lots = MathMax(fixedLot, mn);          // LS1: the person chose the lot (smallest or fixed); 0 = size by risk
   lots = MathFloor(lots / step + 1e-9) * step;
   if(lots < mn){ Reject(id, "min lot would risk more than allowed"); return; }
   lots = MathMin(lots, MathMin(mx, MaxLots));
   string cm = "SXB" + (string)id;
   if(StakeOn && stakePct > 0 && fixedLot <= 0)          // LS1: a lot the person chose is never raised by a big stake
   {
      stakePct = MathMin(stakePct, 50.0); stakeMaxRisk = MathMax(0.5, MathMin(stakeMaxRisk, 25.0));
      if(BigStakeOpen()) Print("Signal ", id, ": a big-stake trade is already open, this one uses normal sizing");
      else
      {
         double sl2 = StakeLots(sym, buy, price, sl, stakePct, stakeMaxRisk, tv, ts, step, mn, mx);
         if(sl2 > 0 && sl2 > lots){ lots = sl2; cm += "S"; Print("Signal ", id, ": big stake, ", DoubleToString(lots, 2), " lots (about ", DoubleToString(stakePct, 1), "% of the balance as margin, loss at the stop capped at ", DoubleToString(stakeMaxRisk, 1), "%)"); }
         else Print("Signal ", id, ": big stake not possible (lot size, margin or loss cap), normal sizing");
      }
   }
   if(maxLot > 0)
   {  // LC2: the person's biggest lot for any one trade (0 = no cap). It comes last, so it also limits a big-stake trade.
      if(maxLot < mn - 1e-12){ if(maxLotSoft > 0) maxLot = mn; else { Reject(id, "your biggest lot is below the broker minimum lot"); return; } }          // LS1: the safe default never blocks a trade
      if(lots > maxLot + 1e-12){ lots = MathFloor(maxLot / step + 1e-9) * step; Print("Signal ", id, ": lot cut to your biggest lot, ", DoubleToString(lots, 2)); }
   }
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   bool ok = buy ? trade.Buy(lots, sym, 0, sl, tp, cm) : trade.Sell(lots, sym, 0, sl, tp, cm);
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      Report(id, "open", ",\"ticket\":" + (string)trade.ResultOrder() + ",\"lots\":" + DoubleToString(lots, 2) + ",\"price\":" + DoubleToString(trade.ResultPrice(), dg));
   else Reject(id, "order failed " + (string)trade.ResultRetcode());
}

//--- BURST BASKET (Section 3): a burst group arrives all at once, is opened together and is closed together.
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

void ExecuteBasket(long gid, string canon, string side, double sl, double tp, double riskPct, double each, int gb, string idsCsv, double grpTgt, double lossPct, double fixedLot = 0, double maxLot = 0, double maxLotSoft = 0, double tinyPct = 0)
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
   if(tinyPct > 0)
   {  // LS5: tiny-account check for the whole group
      double balT = AccountInfoDouble(ACCOUNT_BALANCE), minLoss = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN) * (MathAbs(price - sl) / ts) * tv;
      if(balT > 0 && minLoss > balT * tinyPct / 100.0 + 1e-9){ RejectAll(ids, "even the smallest lot would lose $" + DoubleToString(minLoss, 2) + " at the stop, more than " + DoubleToString(tinyPct, 1) + "% of the balance"); return; }
   }
   // riskPct is ONE entry's share (the server already split the normal risk of one trade across the group)
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * riskPct / 100.0;
   double lotsRaw = riskMoney / ((MathAbs(price - sl) / ts) * tv);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(fixedLot > 0) lotsRaw = MathMax(fixedLot, mn);          // LOT2: the person chose the lot of each entry
   double lots = MathFloor(lotsRaw / step + 1e-9) * step; int want = n;
   if(lots < mn)
   {  // one entry's share is below the smallest lot: open only as many minimum-lot entries as the TOTAL risk of the group allows
      want = (int)MathFloor(lotsRaw * n / mn + 1e-9); lots = mn;
      if(want < 2){ RejectAll(ids, "min lot too big for a group"); return; }
      if(want > n) want = n;
   }
   lots = MathMin(lots, MathMin(mx, MaxLots));
   if(maxLot > 0)
   {  // LC2: the person's biggest lot for any one trade (0 = no cap): every entry of the group is cut to it
      if(maxLot < mn - 1e-12){ if(maxLotSoft > 0) maxLot = mn; else { RejectAll(ids, "your biggest lot is below the broker minimum lot"); return; } }          // LS1
      if(lots > maxLot + 1e-12) lots = MathFloor(maxLot / step + 1e-9) * step;
   }
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   double balBefore = AccountInfoDouble(ACCOUNT_BALANCE);
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
      double tgtMoney = (grpTgt > 0) ? grpTgt : each * k;                                 // the group target is for the WHOLE group, even if the group was trimmed
      GlobalVariableSet(GV("T", gid), tgtMoney); GlobalVariableSet(GV("B", gid), (double)gb); GlobalVariableSet(GV("P", gid), 0.0);
      GlobalVariableSet(GV("L", gid), (lossPct > 0) ? balBefore * lossPct / 100.0 : 0.0);   // group loss limit in money, from the balance when the group opened
      Print("Basket ", gid, ": ", k, " of ", n, " opened, ", DoubleToString(lots, 2), " lots each, target ", DoubleToString(GlobalVariableGet(GV("T", gid)), 2), ", loss limit ", DoubleToString(GlobalVariableGet(GV("L", gid)), 2), ", give-back ", gb, "%");
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

void ManageQuick()          // QP1: each of our positions closes by itself once its OWN profit (plus swap) reaches QuickUsd
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
      double lossMoney = GlobalVariableCheck(GV("L", gid)) ? GlobalVariableGet(GV("L", gid)) : 0.0;
      if(lossMoney > 0 && sum[j] <= -lossMoney)
      {
         Print("Basket ", gid, " hit its loss limit: ", DoubleToString(sum[j], 2), " (limit -", DoubleToString(lossMoney, 2), ") - closing the group");
         GlobalVariableSet(GV("S", gid), sum[j]); GlobalVariableSet(GV("X", gid), (double)TimeCurrent());
         CloseBasket(gid); continue;
      }
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
      GlobalVariableDel(GV("T", gid)); GlobalVariableDel(GV("B", gid)); GlobalVariableDel(GV("P", gid)); GlobalVariableDel(GV("L", gid)); GlobalVariableDel(GV("X", gid)); GlobalVariableDel(GV("S", gid));
   }
}

int OnInit()
{
   EventSetMillisecondTimer(BasketCheckMs);
   Print("SpaceXBridge ", EA_VERSION, " started. Demo account: ", IsDemo(), "  AllowLive: ", AllowLive);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ EventKillTimer(); Comment(""); }

//--- 1.26: update notice. An EA cannot rewrite and compile itself, so it only tells you. Re-paste the code from the app, then compile (F7).
bool VersionNewer(const string latest, const string mine)
{
   string a[], b[]; int na = StringSplit(latest, '.', a), nb = StringSplit(mine, '.', b);
   if(na < 1 || nb < 1) return false;
   for(int i = 0; i < MathMax(na, nb); i++)
   {
      long x = (i < na) ? StringToInteger(a[i]) : 0, y = (i < nb) ? StringToInteger(b[i]) : 0;
      if(x != y) return x > y;
   }
   return false;
}
string noticedVersion = "";
void CheckUpdate(const string latest)
{
   if(latest == "" || !VersionNewer(latest, EA_VERSION)) { if(noticedVersion != "") { Comment(""); noticedVersion = ""; } return; }
   Comment("SpaceXBridge " + EA_VERSION + ": a newer version (" + latest + ") is ready. Open the app, tap Copy code, paste it in MetaEditor, press F7.");
   if(noticedVersion == latest) return;          // one line in the Experts tab per new version, not one every poll
   noticedVersion = latest;
   Print("SpaceXBridge update available: you have ", EA_VERSION, ", newest is ", latest, ". Open the app, tap Copy code, paste it into SpaceXBridge.mq5 in MetaEditor and press F7.");
}

void PollServer();
void OnTimer()
{
   ManageQuick();                                                                      // QP1: small profits are taken here, twice a second
   ManageBaskets();                                                                    // burst baskets are watched every BasketCheckMs
   static uint lastPoll = 0;
   if(GetTickCount() - lastPoll < (uint)(PollSeconds * 1000)) return;                  // the server is still polled every PollSeconds
   lastPoll = GetTickCount(); PollServer();
}
string SymJson()
{  // optional: the smallest lot, tick value and tick size of each market, so the server can warn BEFORE a group is refused for min lot
   string list[]; int n = StringSplit(Symbols, ',', list); string s = ""; int k = 0;
   for(int i = 0; i < n; i++)
   {
      StringTrimLeft(list[i]); StringTrimRight(list[i]);
      string sy = list[i] + SymbolSuffix;
      double mn = SymbolInfoDouble(sy, SYMBOL_VOLUME_MIN), tv = SymbolInfoDouble(sy, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(sy, SYMBOL_TRADE_TICK_SIZE);
      if(mn <= 0 || tv <= 0 || ts <= 0) continue;
      if(k++ > 0) s += ",";
      s += "\"" + list[i] + "\":{\"vol_min\":" + DoubleToString(mn, 4) + ",\"tick_value\":" + DoubleToString(tv, 8) + ",\"tick_size\":" + DoubleToString(ts, 8) + "}";
   }
   return (s == "") ? "" : ",\"sym\":{" + s + "}";
}
void PollServer()
{
   string acct = "{\"balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",\"equity\":" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2)
               + ",\"open\":" + (string)OurPositions() + ",\"demo\":" + (IsDemo() ? "true" : "false") + ",\"allow_live\":" + (AllowLive ? "true" : "false")
               + ",\"login\":" + (string)AccountInfoInteger(ACCOUNT_LOGIN) + ",\"ver\":\"" + EA_VERSION + "\"" + SymJson() + "}";
   string bars = "";
   if(TimeLocal() - lastBars >= BarsPushSeconds || firstPush)
   {
      string list[]; int n = StringSplit(Symbols, ',', list);
      bars = ",\"bars\":{";
      for(int i = 0; i < n; i++)
      {
         StringTrimLeft(list[i]); StringTrimRight(list[i]);
         if(i > 0) bars += ",";
         bars += "\"" + list[i] + "\":{\"M15\":" + BarsJson(list[i], PERIOD_M15, firstPush ? 450 : 6) + ",\"H1\":" + BarsJson(list[i], PERIOD_H1, firstPush ? 320 : 4) + ",\"M5\":" + BarsJson(list[i], PERIOD_M5, firstPush ? 450 : 14) + "}";
      }
      bars += "}"; lastBars = TimeLocal();
   }
   string res = Post("/api/ea/sync", "{\"account\":" + acct + bars + "}");
   if(res == "") return;
   if(bars != "") firstPush = false;
   CheckUpdate(JStr(res, "ea_latest"));                                                 // 1.26: the server says the newest EA version; we only warn, we never change ourselves
   QuickUsd = StringToDouble(JStr(res, "qp"));                                         // QP1: 0 when the person has it off (or an old server sends nothing)
   long bgid = (long)StringToInteger(JStr(res, "gid"));
   if(bgid > 0)   // a burst group arrived: all its entries at once
   {
      ExecuteBasket(bgid, JStr(res, "symbol"), JStr(res, "side"), StringToDouble(JStr(res, "sl")), StringToDouble(JStr(res, "tp")),
                    StringToDouble(JStr(res, "risk_pct")), StringToDouble(JStr(res, "each")), (int)StringToInteger(JStr(res, "gb")), JStr(res, "ids"),
                    StringToDouble(JStr(res, "tgt")), StringToDouble(JStr(res, "loss")), StringToDouble(JStr(res, "lot")), StringToDouble(JStr(res, "max_lot")), StringToDouble(JStr(res, "max_lot_soft")), StringToDouble(JStr(res, "tiny_pct")));
      return;
   }
   long id = (long)StringToInteger(JStr(res, "id"));
   if(id > 0 && StringFind(res, "\"signal\":null") < 0)
      Execute(id, JStr(res, "symbol"), JStr(res, "side"), StringToDouble(JStr(res, "sl")), StringToDouble(JStr(res, "tp")), StringToDouble(JStr(res, "risk_pct")),
               StringToDouble(JStr(res, "stake_pct")), StringToDouble(JStr(res, "stake_max_risk_pct")), StringToDouble(JStr(res, "max_lot")), StringToDouble(JStr(res, "lot")), StringToDouble(JStr(res, "max_lot_soft")), StringToDouble(JStr(res, "tiny_pct")));
}

//--- report closes (SL/TP/manual) back to the backend
void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &rq, const MqlTradeResult &rs)
{
   if(t.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(t.deal)) return;
   // no magic check here: a trade closed by hand (phone or terminal) has magic 0. Our trades are found below by their SXB comment.
   long en = HistoryDealGetInteger(t.deal, DEAL_ENTRY);
   long dr = HistoryDealGetInteger(t.deal, DEAL_REASON);
   double exitPx = HistoryDealGetDouble(t.deal, DEAL_PRICE);                  // Section 4: the price this closing deal really got
   int exitDg = (int)SymbolInfoInteger(HistoryDealGetString(t.deal, DEAL_SYMBOL), SYMBOL_DIGITS); if(exitDg < 0 || exitDg > 8) exitDg = 5;
   if(en != DEAL_ENTRY_OUT && en != DEAL_ENTRY_OUT_BY) return;
   ulong pid = (ulong)HistoryDealGetInteger(t.deal, DEAL_POSITION_ID);
   double pnl = 0; long sid = 0, gid = 0;
   if(HistorySelectByPosition(pid))
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong d = HistoryDealGetTicket(i);
         pnl += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
         string cm = HistoryDealGetString(d, DEAL_COMMENT);
         if(StringFind(cm, "SXB") == 0){ sid = CmId(cm); gid = CmGid(cm); }
      }
   if(sid > 0)
   {
      string why = "other";                                    // what really closed it
      if(GlobalVariableCheck("SXB_Q" + (string)pid)) why = "quick";                       // QP1: closed by the small-profit switch
      else if(gid > 0 && GlobalVariableCheck(GV("X", gid))) why = "basket";
      else if(dr == DEAL_REASON_TP) why = "tp";
      else if(dr == DEAL_REASON_SL) why = "sl";
      else if(dr == DEAL_REASON_CLIENT || dr == DEAL_REASON_MOBILE || dr == DEAL_REASON_WEB) why = "manual";
      else if(dr == DEAL_REASON_EXPERT) why = "bot";
      string extra = ",\"pnl\":" + DoubleToString(pnl, 2) + ",\"reason\":\"" + why + "\"";
      if(exitPx > 0) extra += ",\"price\":" + DoubleToString(exitPx, exitDg);
      if(why == "basket" && GlobalVariableCheck(GV("S", gid))) extra += ",\"gpnl\":" + DoubleToString(GlobalVariableGet(GV("S", gid)), 2);
      Report(sid, "closed", extra);
   }
}
