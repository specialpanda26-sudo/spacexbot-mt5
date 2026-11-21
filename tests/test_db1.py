"""DB1 checks: the server waking up. Run: python tests/test_db1.py"""
import os, sys, types
os.environ.update(DEV_AUTH='1', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'sxb_db1.db'))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
try: import psycopg2
except ImportError:
    psycopg2 = types.ModuleType('psycopg2')
    class OperationalError(Exception): pass
    class InterfaceError(Exception): pass
    psycopg2.OperationalError, psycopg2.InterfaceError = OperationalError, InterfaceError
    sys.modules['psycopg2'] = psycopg2
from backend.app import app
from backend import store as st
R = []
def T(n, ok): R.append((n, bool(ok))); print(('PASS ' if ok else 'FAIL ') + n)
OE = psycopg2.OperationalError

def flaky(n):
    c = {'n': 0}
    def f():
        c['n'] += 1
        if c['n'] <= n: raise OE('SSL connection has been closed unexpectedly')
        return 'ok'
    return f, c

st.PG = True
f, c = flaky(2); T('two dead connections in a row still work (old code retried once)', st._retry(f)() == 'ok' and c['n'] == 3)
f, c = flaky(1); T('one dead connection works', st._retry(f)() == 'ok' and c['n'] == 2)
f, c = flaky(9)
try: st._retry(f)(); raised = False
except OE: raised = True
T('a database that is really down still raises after 3 tries', raised and c['n'] == 3)
class Conn:
    closed = False
    def close(self): self.closed = True
class Pool: pass
p = Pool(); p._pool = [Conn(), Conn()]; st._pool = p
f, c = flaky(1); st._retry(f)()
T('a lost connection throws the saved ones away', st._pool is None and all(x.closed for x in p._pool))
st.PG = False
f, c = flaky(1)
try: st._retry(f)(); raised = False
except OE: raised = True
T('local SQLite is not retried', raised and c['n'] == 1)

cl = app.test_client()
real = st.q
def boom(*a, **k): raise OE('connection to server at "db.secret-host.supabase.co" failed: FATAL: password authentication failed for user "postgres.abc123"')
st.q = boom
r = cl.get('/healthz'); T('/healthz stays ok when the database is down', r.status_code == 200 and r.get_data(as_text=True) == 'ok')
d = cl.get('/api/health/deep').get_json(); txt = str(d)
T('deep health names the wrong password in plain words', 'password is wrong' in d['database'])
T('deep health never leaks the host or user', 'secret-host' not in txt and 'abc123' not in txt)
r = cl.get('/api/me', headers={'Authorization': 'Bearer dev:a@x.com'})
T('a crashing route names the kind of error', r.status_code == 500 and 'Something hiccuped (OperationalError)' in r.get_json()['error'])
st.q = real
d = cl.get('/api/health/deep').get_json()
T('deep health says ok when the database works', d['database'] == 'ok' and 'sign_in' in d and 'email' in d)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
