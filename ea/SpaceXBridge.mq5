//+------------------------------------------------------------------+
//| SpaceXBridge.mq5 - polls your Render backend, places its signals |
//| Setup: Tools > Options > Expert Advisors > tick "Allow WebRequest"|
//| and add your Render URL to the list. Attach to ANY chart.        |
//+------------------------------------------------------------------+
#property strict
#property version "1.00"
#include <Trade\Trade.mqh>

input string ServerUrl      = "https://your-service.onrender.com"; // no trailing slash
input string EAKey          = "change-me-long-random";             // same as EA_KEY on Render
input string Symbols        = "XAUUSD,EURUSD,GBPUSD,USDJPY";       // names WITHOUT broker suffix
input string SymbolSuffix   = "";                                  // e.g. "m" or ".r" if your broker adds one
input int    PollSeconds    = 5;
input int    BarsPushSeconds= 60;
input bool   AllowLive      = false;   // SAFETY: false = refuses to trade on a real-money account
input int    MaxSpreadPoints= 60;      // skip if spread wider than this (points)
input double MaxLots        = 1.0;
input int    Deviation      = 20;
input long   Magic          = 5150150;

CTrade trade;
datetime lastBars = 0; bool firstPush = true;

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

void Report(long id, string status, string extra)
{
   Post("/api/ea/report", "{\"id\":" + (string)id + ",\"status\":\"" + status + "\"" + extra + "}");
}
void Reject(long id, string why){ Print("Signal ", id, " rejected: ", why); Report(id, "rejected", ",\"reason\":\"" + why + "\""); }

void Execute(long id, string canon, string side, double sl, double tp, double riskPct)
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
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * riskPct / 100.0;
   double lots = riskMoney / ((MathAbs(price - sl) / ts) * tv);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), mx = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step) * step;
   if(lots < mn){ Reject(id, "min lot would risk more than allowed"); return; }
   lots = MathMin(lots, MathMin(mx, MaxLots));
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   bool ok = buy ? trade.Buy(lots, sym, 0, sl, tp, "SXB" + (string)id) : trade.Sell(lots, sym, 0, sl, tp, "SXB" + (string)id);
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      Report(id, "open", ",\"ticket\":" + (string)trade.ResultOrder() + ",\"lots\":" + DoubleToString(lots, 2) + ",\"price\":" + DoubleToString(trade.ResultPrice(), dg));
   else Reject(id, "order failed " + (string)trade.ResultRetcode());
}

int OnInit()
{
   EventSetTimer(PollSeconds);
   Print("SpaceXBridge started. Demo account: ", IsDemo(), "  AllowLive: ", AllowLive);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ EventKillTimer(); }

void OnTimer()
{
   string acct = "{\"balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",\"equity\":" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2)
               + ",\"open\":" + (string)OurPositions() + ",\"demo\":" + (IsDemo() ? "true" : "false") + ",\"allow_live\":" + (AllowLive ? "true" : "false")
               + ",\"login\":" + (string)AccountInfoInteger(ACCOUNT_LOGIN) + "}";
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
   long id = (long)StringToInteger(JStr(res, "id"));
   if(id > 0 && StringFind(res, "\"signal\":null") < 0)
      Execute(id, JStr(res, "symbol"), JStr(res, "side"), StringToDouble(JStr(res, "sl")), StringToDouble(JStr(res, "tp")), StringToDouble(JStr(res, "risk_pct")));
}

//--- report closes (SL/TP/manual) back to the backend
void OnTradeTransaction(const MqlTradeTransaction &t, const MqlTradeRequest &rq, const MqlTradeResult &rs)
{
   if(t.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(t.deal)) return;
   if(HistoryDealGetInteger(t.deal, DEAL_MAGIC) != Magic) return;
   long en = HistoryDealGetInteger(t.deal, DEAL_ENTRY);
   if(en != DEAL_ENTRY_OUT && en != DEAL_ENTRY_OUT_BY) return;
   ulong pid = (ulong)HistoryDealGetInteger(t.deal, DEAL_POSITION_ID);
   double pnl = 0; long sid = 0;
   if(HistorySelectByPosition(pid))
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong d = HistoryDealGetTicket(i);
         pnl += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
         string cm = HistoryDealGetString(d, DEAL_COMMENT);
         if(StringFind(cm, "SXB") == 0) sid = (long)StringToInteger(StringSubstr(cm, 3));
      }
   if(sid > 0) Report(sid, "closed", ",\"pnl\":" + DoubleToString(pnl, 2));
}
