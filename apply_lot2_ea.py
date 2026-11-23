import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s: print('already done:', path, old[:40]); return
    if old not in s: sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
E = 'ea/SpaceXBridge.mq5'
sub(E, 'string idsCsv, double grpTgt, double lossPct)\n{', 'string idsCsv, double grpTgt, double lossPct, double fixedLot = 0)\n{')
sub(E, '   double lots = MathFloor(lotsRaw / step + 1e-9) * step; int want = n;\n   if(lots < mn)\n   {  // one entry',
       '   if(fixedLot > 0) lotsRaw = MathMax(fixedLot, mn);          // LOT2: the person chose the lot of each entry\n   double lots = MathFloor(lotsRaw / step + 1e-9) * step; int want = n;\n   if(lots < mn)\n   {  // one entry')
sub(E, 'StringToDouble(JStr(res, "tgt")), StringToDouble(JStr(res, "loss")));', 'StringToDouble(JStr(res, "tgt")), StringToDouble(JStr(res, "loss")), StringToDouble(JStr(res, "lot")));')
print('LOT2 done')
