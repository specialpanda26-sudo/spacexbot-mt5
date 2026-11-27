"""LS5: tiny-account safety check. If even the broker's smallest lot would lose more than X% of the balance at the stop, the trade (or whole burst
group) is refused with a clear reason, on the EA and on the Windows desktop app. X = setting tiny_risk_pct (default 10, 0 = check off).
Nothing is removed. Safe to run twice."""
import sys, re
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, s): open(p, 'w', encoding='utf-8').write(s)
bp, ap, sp, ep, mp = 'backend/burst.py', 'backend/app.py', 'backend/store.py', 'desktop/engine.py', 'ea/SpaceXBridge.mq5'
b, a, s, e, k, m = rd(bp), rd(ap), rd(sp), rd(ep), rd('desktop/basket.py'), rd(mp)
if 'LS5-start' in b: print('already done'); sys.exit(0)
def rep(txt, old, new, name, count=1):
    if txt.count(old) != count: print('anchor problem:', name, txt.count(old)); sys.exit(1)
    return txt.replace(old, new)

# server: the setting and its reader
s = rep(s, "'burst_ceiling': os.getenv('BURST_CEILING', '15'),", "'burst_ceiling': os.getenv('BURST_CEILING', '15'), 'tiny_risk_pct': os.getenv('TINY_RISK_PCT', '10'),", 'store default')
b = rep(b, "# LS4-end\n", '''# LS4-end

# LS5-start
def tiny_pct():
    """LS5: refuse a trade when even the broker's smallest lot would lose more than this percent of the balance at the stop. 0 = check off. Default 10."""
    try: v = float(st.get('tiny_risk_pct'))
    except (TypeError, ValueError): return 10.0
    return 10.0 if v != v else max(0.0, min(100.0, v))
# LS5-end
''', 'burst anchor')
a = rep(a, "bk['max_lot_soft'] = burst.max_lot_soft(who)", "bk['max_lot_soft'] = burst.max_lot_soft(who); bk['tiny_pct'] = burst.tiny_pct()", 'app basket')
a = rep(a, "s['max_lot_soft'] = burst.max_lot_soft(who)", "s['max_lot_soft'] = burst.max_lot_soft(who); s['tiny_pct'] = burst.tiny_pct()", 'app single')

# desktop app
e = rep(e, "    def _place(self, sid, sig, acct, bot):", '''    def tiny_why(self, src, i, acct, price, sl):
        """LS5: text when even the broker's smallest lot would lose more than tiny_pct % of the balance at the stop, else None (0 or missing = off)."""
        try: pct = float((src or {}).get('tiny_pct') or 0)
        except (TypeError, ValueError): return None
        if pct != pct or pct <= 0 or acct['balance'] <= 0: return None
        loss = i['vol_min'] * (abs(price - sl) / i['tick_size']) * i['tick_value']
        if loss > acct['balance'] * pct / 100.0 + 1e-9: return 'even the smallest lot (%g) would lose $%.2f at the stop, more than %g%% of the balance' % (i['vol_min'], loss, pct)
        return None

    def _place(self, sid, sig, acct, bot):''', 'engine _place')
e = rep(e, "        cap, why = self.cap_for(sig, i)          # LC2", "        why = self.tiny_why(sig, i, acct, price, sl)          # LS5\n        if why: return why\n        cap, why = self.cap_for(sig, i)          # LC2", 'engine call')
k = rep(k, "    n = len(ids); step = i['vol_step'] or 0.01;", "    why = e.tiny_why(bk, i, acct, price, sl)          # LS5\n    if why: return why\n    n = len(ids); step = i['vol_step'] or 0.01;", 'basket call')

# EA
m = rep(m, 'double fixedLot = 0, double maxLotSoft = 0)\n{\n   if(!IsDemo()', 'double fixedLot = 0, double maxLotSoft = 0, double tinyPct = 0)\n{\n   if(!IsDemo()', 'EA Execute sig')
m = rep(m, 'double maxLot = 0, double maxLotSoft = 0)\n{\n   string idl[];', 'double maxLot = 0, double maxLotSoft = 0, double tinyPct = 0)\n{\n   string idl[];', 'EA basket sig')
m = rep(m, '   if(tv <= 0 || ts <= 0){ Reject(id, "no tick value"); return; }\n', '''   if(tv <= 0 || ts <= 0){ Reject(id, "no tick value"); return; }
   if(tinyPct > 0)
   {  // LS5: tiny-account check: even the broker's smallest lot must not lose more than tinyPct % of the balance at the stop
      double balT = AccountInfoDouble(ACCOUNT_BALANCE), minLoss = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN) * (MathAbs(price - sl) / ts) * tv;
      if(balT > 0 && minLoss > balT * tinyPct / 100.0 + 1e-9){ Reject(id, "even the smallest lot would lose $" + DoubleToString(minLoss, 2) + " at the stop, more than " + DoubleToString(tinyPct, 1) + "% of the balance"); return; }
   }
''', 'EA single check')
m = rep(m, '   if(tv <= 0 || ts <= 0){ RejectAll(ids, "no tick value"); return; }\n', '''   if(tv <= 0 || ts <= 0){ RejectAll(ids, "no tick value"); return; }
   if(tinyPct > 0)
   {  // LS5: tiny-account check for the whole group
      double balT = AccountInfoDouble(ACCOUNT_BALANCE), minLoss = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN) * (MathAbs(price - sl) / ts) * tv;
      if(balT > 0 && minLoss > balT * tinyPct / 100.0 + 1e-9){ RejectAll(ids, "even the smallest lot would lose $" + DoubleToString(minLoss, 2) + " at the stop, more than " + DoubleToString(tinyPct, 1) + "% of the balance"); return; }
   }
''', 'EA basket check')
m = rep(m, 'StringToDouble(JStr(res, "max_lot_soft")));', 'StringToDouble(JStr(res, "max_lot_soft")), StringToDouble(JStr(res, "tiny_pct")));', 'EA calls', 2)
m = rep(m, '#property version "1.24"', '#property version "1.25"', 'EA version')

wr(bp, b); wr(ap, a); wr(sp, s); wr(ep, e); wr('desktop/basket.py', k); wr(mp, m)
for t in ('tests/test_ls1.py', 'tests/test_lc2.py'):          # these only check that the EA version was raised
    x = rd(t)
    if '"1.24"' in x: wr(t, x.replace('1.24', '1.25'))
print('LS5 applied')
