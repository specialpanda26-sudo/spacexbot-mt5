"""PL2: a managed plan forces burst ON for that account and wins over Auto mode. Patches backend/burst.py and backend/app.py. Safe to run twice."""
def patch(path, pairs, tag='PL2'):
    s = open(path, encoding='utf-8').read()
    if tag in s: print(path, 'already patched, skipping'); return
    for old, new in pairs:
        assert s.count(old) == 1, path + ' anchor missing: ' + old[:55]
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s); print(path, 'patched')

patch('backend/burst.py', [
 ("def get(uid=''):\n    \"\"\"The person's choices",
  "def plan_active(uid=''):\n    \"\"\"PL2: does this account have a managed plan? (burst is then mandatory and Auto mode cannot pause it)\"\"\"\n    return _clamp(_raw(uid).get('plan_usd'), 0, PLAN_MAX, 0, int) >= PLAN_MIN\n\n\ndef get(uid=''):\n    \"\"\"The person's choices"),
 ("return {'on': j.get('on') is True, 'idle_min'",
  "return {'on': j.get('on') is True or plan_active(uid), 'idle_min'"),          # PL2: forced on while a plan is active
 ("    if automode.on(): return False, AUTO_WHY          # BX1\n",
  "    if automode.on() and not plan_active(uid): return False, AUTO_WHY          # BX1 (PL2: a managed plan wins over Auto mode)\n"),
 ("    chk = dict(cur); chk.update(new)          # LS1:",
  "    if d.get('on') is False and (_clamp(new.get('plan_usd', cur.get('plan_usd')), 0, PLAN_MAX, 0, int) >= PLAN_MIN): raise ValueError('Burst must stay on while a managed plan is active. Set the plan to 0 first to turn burst off.')          # PL2\n    chk = dict(cur); chk.update(new)          # LS1:"),
])
patch('backend/app.py', [
 ("    if automode.on(): burst_look.note(uid, 'Auto mode is ON, so burst is paused.",
  "    if automode.on() and not burst.plan_active(uid): burst_look.note(uid, 'Auto mode is ON, so burst is paused."),
], tag='burst.plan_active')
