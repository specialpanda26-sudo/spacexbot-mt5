"""Group loss limit + group target in the MT5 bridge (ea/SpaceXBridge.mq5).
The server already sends tgt (USD for the whole group) and loss (percent of the balance) with every basket. The EA ignored both.
Now: the group target is the whole-group USD target, and the group loss limit closes the whole group when its total loss reaches loss% of the balance taken when it opened.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
F = 'ea/SpaceXBridge.mq5'
s = open(F, encoding='utf-8').read()
if 'GV("L", gid)' in s:
    print('already applied'); raise SystemExit
E = [
 ('void ExecuteBasket(long gid, string canon, string side, double sl, double tp, double riskPct, double each, int gb, string idsCsv)',
  'void ExecuteBasket(long gid, string canon, string side, double sl, double tp, double riskPct, double each, int gb, string idsCsv, double grpTgt, double lossPct)'),
 ('      GlobalVariableSet(GV("T", gid), each * k); GlobalVariableSet(GV("B", gid), (double)gb); GlobalVariableSet(GV("P", gid), 0.0);\n',
  '      double tgtMoney = (grpTgt > 0) ? grpTgt : each * k;                                 // the group target is for the WHOLE group, even if the group was trimmed\n'
  '      GlobalVariableSet(GV("T", gid), tgtMoney); GlobalVariableSet(GV("B", gid), (double)gb); GlobalVariableSet(GV("P", gid), 0.0);\n'
  '      GlobalVariableSet(GV("L", gid), (lossPct > 0) ? balBefore * lossPct / 100.0 : 0.0);   // group loss limit in money, from the balance when the group opened\n'),
 (' " lots each, target ", DoubleToString(each * k, 2), ", give-back ", gb, "%");'.strip(),
  '" lots each, target ", DoubleToString(GlobalVariableGet(GV("T", gid)), 2), ", loss limit ", DoubleToString(GlobalVariableGet(GV("L", gid)), 2), ", give-back ", gb, "%");'),
 ('   long okId[]; ulong okTk[]; double okPx[]; ArrayResize(okId, n);',
  '   double balBefore = AccountInfoDouble(ACCOUNT_BALANCE);\n   long okId[]; ulong okTk[]; double okPx[]; ArrayResize(okId, n);'),
 ('      bool hit = (sum[j] >= target);\n',
  '      double lossMoney = GlobalVariableCheck(GV("L", gid)) ? GlobalVariableGet(GV("L", gid)) : 0.0;\n'
  '      if(lossMoney > 0 && sum[j] <= -lossMoney)\n'
  '      {\n'
  '         Print("Basket ", gid, " hit its loss limit: ", DoubleToString(sum[j], 2), " (limit -", DoubleToString(lossMoney, 2), ") - closing the group");\n'
  '         GlobalVariableSet(GV("S", gid), sum[j]); GlobalVariableSet(GV("X", gid), (double)TimeCurrent());\n'
  '         CloseBasket(gid); continue;\n'
  '      }\n'
  '      bool hit = (sum[j] >= target);\n'),
 ('GlobalVariableDel(GV("P", gid)); GlobalVariableDel(GV("X", gid));',
  'GlobalVariableDel(GV("P", gid)); GlobalVariableDel(GV("L", gid)); GlobalVariableDel(GV("X", gid));'),
 ('StringToDouble(JStr(res, "risk_pct")), StringToDouble(JStr(res, "each")), (int)StringToInteger(JStr(res, "gb")), JStr(res, "ids"));',
  'StringToDouble(JStr(res, "risk_pct")), StringToDouble(JStr(res, "each")), (int)StringToInteger(JStr(res, "gb")), JStr(res, "ids"),\n                    StringToDouble(JStr(res, "tgt")), StringToDouble(JStr(res, "loss")));'),
]
for a, b in E:
    assert s.count(a) == 1, 'not found exactly once: ' + a[:60]
for a, b in E: s = s.replace(a, b)
open(F, 'w', encoding='utf-8').write(s)
print('done')
