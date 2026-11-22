"""Test Lab (owner only): buttons that SHOW a fake situation without waiting for it to happen. It only hands the page the words and the kind of screen to draw.
It never places a trade, never touches money, never writes to the database, and is dead unless the Render switch TEST_LAB=1 is on and the caller is an admin
(the admin check is on the route in app.py). Every message below is copied from the real code (tests/test_testlab.py checks that, so they cannot drift)."""
import os

def enabled(): return os.getenv('TEST_LAB', '').strip() == '1'

# id, group, button label, kind ('deriv' = the toast after Deriv login, 'pay' = the payment screen), what, ok, the real words (only for kind 'deriv')
_ROWS = [
 ('deriv_ok',      'Deriv login', 'Success',        'deriv', 'ok',     True,  'Deriv connected. Demo account found.'),
 ('deriv_cancel',  'Deriv login', 'Cancelled',      'deriv', 'fail',   False, 'Deriv login was cancelled. Nothing was connected.'),
 ('deriv_expired', 'Deriv login', 'Took too long',  'deriv', 'fail',   False, 'The login took too long. Tap Log in with Deriv again.'),
 ('deriv_long',    'Deriv login', 'Token too long', 'deriv', 'fail',   False, 'Deriv sent a login we could not keep safely. Tap Log in with Deriv again, or paste a token instead.'),
 ('pay_ok',        'Payment',     'Success',        'pay',   'ok',     True,  ''),
 ('pay_fail',      'Payment',     'Failed',         'pay',   'fail',   False, ''),
 ('pay_slow',      'Payment',     'Slow',           'pay',   'slow',   False, ''),
 ('pay_cancel',    'Payment',     'Cancelled',      'pay',   'cancel', False, ''),
]
_BY = {r[0]: r for r in _ROWS}

def cases(): return [{'id': r[0], 'group': r[1], 'label': r[2]} for r in _ROWS]

def run(case):
    """-> (payload, None) or (None, plain-words reason). Pure: no database, no network, no side effect."""
    if not enabled(): return None, 'Test Lab is off. Set TEST_LAB=1 on Render to use it.'
    r = _BY.get(str(case or ''))
    if not r: return None, 'That test case does not exist.'
    return {'case': r[0], 'group': r[1], 'label': r[2], 'kind': r[3], 'what': r[4], 'ok': r[5], 'msg': r[6], 'fake': True}, None
