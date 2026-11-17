"""Applies the video-1 upgrade. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import sys
EDITS = [
 ('backend/strategies.py', "ALL = [ema_pullback,", "from .jg_pullback import jg_pullback\nALL = [jg_pullback, ema_pullback,", 'from .jg_pullback import jg_pullback'),
 ('backend/strategies.py', "TREND = {'ema_pullback',", "TREND = {'jg_pullback', 'ema_pullback',", "TREND = {'jg_pullback'"),
 ('backend/brain.py', "    return {'side': side, 'entry': round(entry, 5)",
  "    if len(grp) == 1 and grp[0].get('tp'):      # a lone strategy that brings its own target (video-1 setup)\n        t = grp[0]['tp']\n        if (side == 'buy' and t > entry) or (side == 'sell' and t < entry): tp = t\n    return {'side': side, 'entry': round(entry, 5)", "a lone strategy that brings its own target"),
 ('tools/backtest.py', "if hit_tp: res = rr; break", "if hit_tp: res = abs(tp - s['entry']) / abs(s['entry'] - sl); break", "abs(tp - s['entry'])"),
]
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) or open(path, encoding='utf-8', newline='').read()
    if marker in t: print('already applied:', path, marker[:40]); new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:50]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
