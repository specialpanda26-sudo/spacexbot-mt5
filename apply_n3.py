"""Section N3: billing alerts. Edits backend/push.py (notify_user), backend/payments.py (alerts 38-41 at the points where a payment changes state), backend/alerts.py (timed job for 42-44) and docs/HANDOFF.md.
New file backend/billalerts.py and tests/test_bill3.py come from the cat blocks. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')

# ---- push.py: one person, whatever their plan state
edit('backend/push.py', 'def send_data(uid, data):',
'''def notify_user(uid, kind, key=None, **facts):
    """Billing alerts for ONE person, whatever their plan state. broadcast() only reaches paid people and admins, but "prompt sent", "payment did not go through" and "plan ended" belong to people who have no plan right now. Background thread, never raises. key makes it once per person."""
    if not configured(): return
    try:
        from .pushcopy import compose
        t, b, i = compose(kind, **facts)
    except Exception as e: print('[push] notify_user failed', kind, e); return
    def run():
        try: send(uid, kind, b, t, key, img=i)
        except Exception as e: print('[push] failed', e)
    threading.Thread(target=run, daemon=True).start()

def send_data(uid, data):''', 'def notify_user(uid, kind')

# ---- payments.py
P = 'backend/payments.py'
edit(P, "def _receipt(p):",
'''def _push(uid, kind, key, **f):
    """N3 billing alert to this one person. A failed alert never touches the payment."""
    try:
        from . import push; push.notify_user(uid, kind, key, **f)
    except Exception as e: print('billing push failed', e)
def _push_paid(p, kind):
    try:
        from . import billalerts; _push(p['uid'], kind, 'pay%d-%s' % (kind, p['ref']), until=billalerts.until_for(p['uid']))
    except Exception as e: print('billing push failed', e)

def _receipt(p):''', 'def _push_paid(')
edit(P, "    note(ref, 'prompt accepted by gateway | provider=%s network=%s' % (prov, body.get('network_code', '-')))\n    return ref",
        "    note(ref, 'prompt accepted by gateway | provider=%s network=%s' % (prov, body.get('network_code', '-')))\n    _push(uid, 39, 'pay39-' + ref)\n    return ref", "'pay39-' + ref")
edit(P, "        _receipt(p)\n        return 'paid'", "        _receipt(p)\n        _push_paid(p, 38)\n        return 'paid'", '_push_paid(p, 38)')
edit(P, "_mark(p['ref'], 'failed', FAIL_REASON.get(cb['code'], 'other')); return 'failed'",
        "_mark(p['ref'], 'failed', FAIL_REASON.get(cb['code'], 'other')); _push(p['uid'], 40, 'pay40-' + p['ref']); return 'failed'", "_push(p['uid'], 40, 'pay40-' + p['ref']); return 'failed'")
edit(P, "        _receipt(p)\n\ndef _row(ref):", "        _receipt(p)\n        _push_paid(p, 41)\n    elif state == 'failed' and n: _push(p['uid'], 40, 'pay40-' + p['ref'])\n\ndef _row(ref):", '_push_paid(p, 41)')
edit(P, '''    st.x("UPDATE payments SET status='expired',extra='no_response' WHERE provider='finoq' AND status='pending' AND created<?", (now - 15 * 60,))''',
        '''    _expire('finoq', now - 15 * 60)''', "_expire('finoq'")
edit(P, '''    st.x("UPDATE payments SET status='expired',extra='no_response' WHERE provider='paypal' AND status='pending' AND created<?", (now - 4 * 3600,))''',
        '''    _expire('paypal', now - 4 * 3600)''', "_expire('paypal'")
edit(P, "def reconcile():", '''def _expire(provider, cutoff):
    """A prompt nobody answered: mark it expired (one row at a time, only the update that wins tells the person) and send alert 40."""
    for p in st.q("SELECT ref,uid FROM payments WHERE provider=? AND status='pending' AND created<?", (provider, cutoff)):
        if st.x("UPDATE payments SET status='expired',extra='no_response' WHERE ref=? AND status='pending'", (p['ref'],), count=True): _push(p['uid'], 40, 'pay40-' + p['ref'])

def reconcile():''', 'def _expire(')

# ---- alerts.py: the timed job
A = 'backend/alerts.py'
edit(A, 'def _self_test_job():', '''def _billing_job():
    from . import billalerts
    billalerts.run()

def _self_test_job():''', 'def _billing_job')
edit(A, '    register_job("self_test", 60, _self_test_job)\n', '    register_job("self_test", 60, _self_test_job)\n    register_job("billing_plan", 600, _billing_job)\n', 'register_job("billing_plan"')

# ---- HANDOFF
H = 'docs/HANDOFF.md'
SEC = """## Section N3 (billing alerts) DONE (Nov 21)
- apply_n3.py + backend/billalerts.py + tests/test_bill3.py. Kinds 38 (payment received, M-Pesa), 39 (M-Pesa prompt sent), 40 (payment did not go through), 41 (PayPal confirmed), 42 (plan ends in 3 days), 43 (ends tomorrow), 44 (ended).
- 38-41 are sent from backend/payments.py where a payment really changes state: stk_push after the gateway accepted the prompt (39); settle_deposit after activate + receipt (38, until = the new end date); a failed callback (40); _pp_apply after activate (41) or on a failed capture (40); the new _expire(provider, cutoff) used by reconcile() when a prompt nobody answered expires (40, only the update that wins sends). Repeat callbacks, underpaid payments and a gateway that refused the prompt send nothing (the person already sees the error on screen).
- They go through the new push.notify_user(uid, kind, key, **facts): ONE person, whatever their plan state (push.broadcast only reaches paid people and admins, which would hide 'prompt sent', 'failed' and 'plan ended' from the very people who need them). Key pay<kind>-<ref> = once per payment. Billing is a bypass category: quiet hours and the daily cap never block it; the person's own Billing switch in the alert settings still does.
- 42/43/44: billalerts.run() is a job in the alerts loop (register_job billing_plan, every 600 s, only while the server is awake: see the Render free note). which(left): more than 3 days nothing, 1-3 days = 42, under 1 day = 43, ended up to 2 days ago = 44, older nothing. Once per person per plan end date (key plan<kind>-<plan_until>); extending gives a new end date so the cycle starts again. Admins get none. A person with no registered phone is skipped by the query.
- Same facts as the in-app cards (8b). The tap route is #plans (the phone maps it to the profile screen).
- NOT tested: a real FCM send, a real M-Pesa or PayPal payment. The first 42 only fires if the server happens to be awake in the 1-3 day window (free Render): ping /healthz from an uptime monitor.
- Next: N5 (market alerts) then N6, then 4C, the backtest, 9b.

"""
edit(H, '## STATUS BOARD (Nov 21, newest; read this first)\n', SEC + '## STATUS BOARD (Nov 21, newest; read this first)\n', '## Section N3 (billing alerts)')
edit(H, '- N3  billing alerts: kinds 38-41 from payments (hook: payments.activate()), 42/43/44 plan ends in 3 days / tomorrow / ended.', '- N3  DONE (see Section N3 below). Billing alerts: kinds 38-41 from payments, 42/43/44 plan ends in 3 days / tomorrow / ended.', '- N3  DONE (see Section N3')
