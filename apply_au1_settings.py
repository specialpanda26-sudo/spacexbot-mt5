"""AU1 patch (settings audit): 7 owner settings had NO field in the Admin panel, so they could only be changed through server environment variables.
Now each one has a labelled field with its allowed range, checked by the server before saving:
  Main settings: news_before_min, news_after_min, cooldown_min, max_ccy_exposure (safety gates, so they sit in plain view, not under Advanced).
  Advanced:      multi_entries, regime_min_trades, practice_trades_needed.
Files: backend/app.py (server range check), static/index.html (fields), docs/HANDOFF.md.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_au1_settings.py"""
import sys
A, H, D = 'backend/app.py', 'static/index.html', 'docs/HANDOFF.md'
SRV = ("('practice_trades_needed', 0, 100)):",
       "('practice_trades_needed', 0, 100),\n                     ('news_before_min', 0, 240), ('news_after_min', 0, 240), ('cooldown_min', 0, 1440), ('max_ccy_exposure', 1, 10), ('multi_entries', 1, 10), ('regime_min_trades', 5, 500)):          # AU1: the six numbers that had no field, checked before anything is saved\n                     ")
UI = [
 ('["news_lock","News lock (no trades around big news)","c"],',
  '["news_lock","News lock (no trades around big news)","c"],["news_before_min","News lock: minutes before the news","n",0,240],["news_after_min","News lock: minutes after the news","n",0,240],["cooldown_min","Wait minutes before the same market trades again","n",0,1440],["max_ccy_exposure","Most trades leaning the same way on one currency","n",1,10],'),
 ('["max_trades_day","Max trades a day (0 = off)","n",0,100],',
  '["max_trades_day","Max trades a day (0 = off)","n",0,100],["multi_entries","Entries per signal when a person has not chosen (several-entries mode)","n",1,10],["regime_min_trades","Regime switch: trades needed before a strategy is paused (at least 5)","n",5,500],["practice_trades_needed","Practice trades a new person must finish first (0 = none)","n",0,100],'),
]
def patch(path, pairs, mark):
    s = open(path, encoding='utf-8').read()
    if mark in s: print(path, 'already patched'); return
    for o, n in pairs:
        if s.count(o) != 1: sys.exit('STOP: anchor found %d times in %s: %s' % (s.count(o), path, o[:70]))
    for o, n in pairs: s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s); print('patched', path)
patch(A, [SRV], "('cooldown_min', 0, 1440)")
patch(H, UI, '"news_before_min","News lock: minutes before')
MARK = '## Section AU1 (settings audit)'; h = open(D, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has AU1')
else:
    open(D, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 24)
- Audit: every key of store.DEFAULTS was checked against static/. 7 had no field anywhere: news_before_min, news_after_min, cooldown_min, max_ccy_exposure, multi_entries, regime_min_trades, practice_trades_needed. (The feed switch has its own card, /api/admin/feed.)
- Now in the Admin panel with ranges, server-checked in backend/app.py admin_set: news before/after 0-240, cooldown 0-1440, same-currency trades 1-10, entries 1-10, regime trades 5-500, practice trades 0-100. News + cooldown + currency exposure are in Main settings (safety gates); the other three are in Advanced.
- tests/test_au1.py also fails if a new server setting is added without a field.
- Not touched: the Find a setting search does not cover Admin settings. Advanced is still a collapsed section (Admin panel); say if it should be opened by default.
''')
    print('HANDOFF updated')
