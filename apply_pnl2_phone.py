"""Profit not showing, second cause: phone-mode results (assist_log, logged by the person with 'Log how it ended') were never read by the Journal or the
Profit and Loss card, which only read the signals table. Now they are merged in as broker 'Phone'. Only taken trades with an amount count (an outcome with no
amount cannot be added up, and nothing is invented). Their ids are negative so they never clash with a real signal id.
The old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
F = 'backend/journal.py'
s = open(F, encoding='utf-8').read()
if 'phone-mode' in s:
    print('already applied'); raise SystemExit
A = "    return out\n\n\ndef _detail(r):"
assert s.count(A) == 1, 'anchor not found exactly once'
NEW = '''    if uid:                                                  # phone-mode trades the person logged themselves (assist_log), broker 'Phone'
        try:
            for r in st.q("SELECT l.sid AS sid,l.pnl AS pnl,l.lots AS lots,l.done AS done,l.ts AS ts,s.symbol AS symbol,s.side AS side,s.strategy AS strategy,s.entry AS entry,s.sl AS sl,s.tp AS tp,s.created AS created,s.reason AS reason "
                          "FROM assist_log l JOIN signals s ON s.id=l.sid WHERE l.uid=? AND l.action='taken' AND l.pnl IS NOT NULL", (uid,)) or []:
                p = _num(r.get('pnl'))
                if p is None: continue
                out.append({'id': -int(r['sid']), 't': int(r.get('done') or r.get('ts') or r.get('created') or 0), 'opened': int(r.get('ts') or r.get('created') or 0), 'symbol': r['symbol'],
                            'side': str(r['side'] or '').lower(), 'strategy': r['strategy'], 'strategy_name': si.label(r['strategy']), 'pnl': round(p, 2),
                            'result': 'win' if p > 0 else 'loss', 'broker': 'Phone', 'entry': r.get('entry'), 'fill': None, 'sl': r.get('sl'),
                            'tp': r.get('tp'), 'lots': r.get('lots'), 'why': rsn.short(r.get('reason')), '_raw': r.get('reason')})
        except Exception as e: print('phone-mode rows skipped', e)
        out.sort(key=lambda r: (r['t'], r['id']), reverse=True)
    return out


def _detail(r):'''
s = s.replace(A, NEW)
open(F, 'w', encoding='utf-8').write(s)
print('done')
