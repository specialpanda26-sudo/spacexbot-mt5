"""LC2: the MT5 EA and the desktop app obey the person's biggest lot (max_lot). Safe to run twice."""
import sys

def rep(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s:
        print('already done:', path); return
    if s.count(old) != 1:
        print('NOT FOUND (%d matches): %s -> %s' % (s.count(old), path, old[:60].replace('\n', ' '))); sys.exit(1)
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched:', path)

E = 'desktop/engine.py'
rep(E, '''    def _place(self, sid, sig, acct, bot):''', '''    def cap_for(self, src, i):
        """LC2: the biggest lot for this trade = the smaller of the app's own cap and the person's max_lot from the server (0 or missing = no server cap).
        Returns (cap, None), or (None, why) when the person's biggest lot is below what the broker allows."""
        cap = self.cfg['max_lots']
        try: ml = float((src or {}).get('max_lot') or 0)
        except (TypeError, ValueError): ml = 0.0
        if ml != ml or ml < 0: ml = 0.0
        if ml > 0:
            if ml < i['vol_min'] - 1e-12: return None, 'your biggest lot is below the broker minimum lot'
            cap = min(cap, ml)
        return cap, None

    def _place(self, sid, sig, acct, bot):''')
rep(E, '''        lots = self._lots(acct['balance'] * risk / 100.0 / ((abs(price - sl) / i['tick_size']) * i['tick_value']), i, c['max_lots'])''',
'''        cap, why = self.cap_for(sig, i)          # LC2: obey the person's biggest lot
        if why: return why
        lots = self._lots(acct['balance'] * risk / 100.0 / ((abs(price - sl) / i['tick_size']) * i['tick_value']), i, cap)''')

B = 'desktop/basket.py'
rep(B, '''    lots = round(min(lots, i['vol_max'], c['max_lots']), nd)
    placed = []''', '''    cap, why = e.cap_for(bk, i)          # LC2: obey the person's biggest lot (it only ever lowers the lot)
    if why: return why
    lots = math.floor(min(lots, i['vol_max'], cap) / step + 1e-9) * step; lots = round(lots, nd)
    placed = []''')

A = 'ea/SpaceXBridge.mq5'
rep(A, '#property version "1.22"', '#property version "1.23"')
rep(A, '''double riskPct, double stakePct = 0, double stakeMaxRisk = 10)
{''', '''double riskPct, double stakePct = 0, double stakeMaxRisk = 10, double maxLot = 0)
{''')
rep(A, '''   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   bool ok = buy ? trade.Buy(lots''', '''   if(maxLot > 0)
   {  // LC2: the person's biggest lot for any one trade (0 = no cap). It comes last, so it also limits a big-stake trade.
      if(maxLot < mn - 1e-12){ Reject(id, "your biggest lot is below the broker minimum lot"); return; }
      if(lots > maxLot + 1e-12){ lots = MathFloor(maxLot / step + 1e-9) * step; Print("Signal ", id, ": lot cut to your biggest lot, ", DoubleToString(lots, 2)); }
   }
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   bool ok = buy ? trade.Buy(lots''')
rep(A, '''double lossPct, double fixedLot = 0)
{''', '''double lossPct, double fixedLot = 0, double maxLot = 0)
{''')
rep(A, '''   lots = MathMin(lots, MathMin(mx, MaxLots));
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   double balBefore''', '''   lots = MathMin(lots, MathMin(mx, MaxLots));
   if(maxLot > 0)
   {  // LC2: the person's biggest lot for any one trade (0 = no cap): every entry of the group is cut to it
      if(maxLot < mn - 1e-12){ RejectAll(ids, "your biggest lot is below the broker minimum lot"); return; }
      if(lots > maxLot + 1e-12) lots = MathFloor(maxLot / step + 1e-9) * step;
   }
   trade.SetExpertMagicNumber(Magic); trade.SetDeviationInPoints(Deviation); trade.SetTypeFillingBySymbol(sym);
   double balBefore''')
rep(A, '''StringToDouble(JStr(res, "loss")), StringToDouble(JStr(res, "lot")));''',
      '''StringToDouble(JStr(res, "loss")), StringToDouble(JStr(res, "lot")), StringToDouble(JStr(res, "max_lot")));''')
rep(A, '''StringToDouble(JStr(res, "stake_pct")), StringToDouble(JStr(res, "stake_max_risk_pct")));''',
      '''StringToDouble(JStr(res, "stake_pct")), StringToDouble(JStr(res, "stake_max_risk_pct")), StringToDouble(JStr(res, "max_lot")));''')
print('LC2 applied. Now RECOMPILE ea/SpaceXBridge.mq5 in MetaEditor (version 1.23).')
