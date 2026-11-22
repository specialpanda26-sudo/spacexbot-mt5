"""Supabase auth checks, offline (the network call is faked). Run: python tests/test_sbauth.py"""
import os, sys
os.environ.update(SUPABASE_URL='https://x.supabase.co', SUPABASE_ANON_KEY='anon', SUPABASE_SERVICE_KEY='svc')
os.environ.pop('DEV_AUTH', None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend import sbauth
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
class Resp:
    def __init__(s, code, js=None): s.status_code = code; s._j = js
    def json(s): return s._j
calls = []
def fake_get(url, headers=None, timeout=0):
    calls.append((url, headers))
    if headers['Authorization'] == 'Bearer good':
        return Resp(200, {'id': 'uuid-1', 'email': 'a@b.com', 'email_confirmed_at': '2026-01-01', 'user_metadata': {'full_name': 'Amy W'}})
    if headers['Authorization'] == 'Bearer unconfirmed': return Resp(200, {'id': 'uuid-2', 'email': 'c@d.com', 'email_confirmed_at': None, 'user_metadata': {}})
    return Resp(401, {})
sbauth.requests.get = fake_get
u = sbauth.verify('good')
T('valid token -> user', u == {'uid': 'uuid-1', 'email': 'a@b.com', 'name': 'Amy W', 'verified': True, 'last_sign_in': ''})
T('sends the anon key', calls[0][1]['apikey'] == 'anon' and calls[0][0] == 'https://x.supabase.co/auth/v1/user')
sbauth.verify('good'); T('second check is cached', len(calls) == 1)
T('unconfirmed email -> verified False', sbauth.verify('unconfirmed')['verified'] is False)
T('bad token -> None', sbauth.verify('nope') is None)
T('dev tokens are off without DEV_AUTH', sbauth.verify('dev:x@y.com') is None)
dels = []
sbauth.requests.delete = lambda url, headers=None, timeout=0: (dels.append((url, headers)) or Resp(200))
T('delete uses the service key', sbauth.delete_user('uuid-1') and dels[0][0].endswith('/auth/v1/admin/users/uuid-1') and dels[0][1]['apikey'] == 'svc')
T('public config has url + anon key only', sbauth.public_config() == {'url': 'https://x.supabase.co', 'key': 'anon'})
os.environ['SUPABASE_URL'] = ''
T('unconfigured -> None, no crash', sbauth.verify('good') is None)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
