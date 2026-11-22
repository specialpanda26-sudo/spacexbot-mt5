"""CY1 tests: Auto-cycle choices (server side). No network. Run: python tests/test_cycle1.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_cy1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, cycle, groupcap
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
def clean(): st.x("DELETE FROM kv WHERE k LIKE 'cycle:%' OR k LIKE 'gcap:%' OR k LIKE 'pref:%'")
def bad(d, uid=''):
    try: cycle.save(uid, d); return False
    except ValueError: return True

clean(); T('default: off, 10 new groups a day', cycle.get('') == {'on': False, 'max_per_day': 10})
g = cycle.save('', {'on': True}); T('switch on is saved, the day limit keeps its default', g == {'on': True, 'max_per_day': 10})
g = cycle.save('', {'max_per_day': 25}); T('day limit saved and the switch is kept', g == {'on': True, 'max_per_day': 25})
T('on must be true or false', bad({'on': 1}) and bad({'on': 'yes'}))
T('day limit must be a whole number 1..100', bad({'max_per_day': 0}) and bad({'max_per_day': 101}) and bad({'max_per_day': 2.5}) and bad({'max_per_day': 'x'}) and bad({'max_per_day': True}) and bad({'max_per_day': float('nan')}))
T('a refused save changed nothing', cycle.get('') == {'on': True, 'max_per_day': 25})
T('not an object is refused', bad([1, 2]))
st.put('cycle:', '{"on": true, "max_per_day": 9999}'); T('a bad saved value falls back to the default', cycle.get('')['max_per_day'] == 10)
st.put('cycle:', 'not json'); T('unreadable saved data means off', cycle.get('') == {'on': False, 'max_per_day': 10})

clean(); cycle.save('', {'on': True, 'max_per_day': 5})
T('cycle on but the group target is off: no rules', cycle.rules('', 6) is None)
groupcap.save('', {'on': True, 'target_usd': 0.7})
r = cycle.rules('', 6); T('group target 0.70 USD and 6 entries: the cycle runs on 0.70 for the whole group', r == {'tgt': 0.7, 'n': 6, 'max_per_day': 5})
T('a single trade is not a group: no rules', cycle.rules('', 1) is None)
groupcap.save('', {'target_usd': 0}); T('group target 0: no rules', cycle.rules('', 6) is None)
groupcap.save('', {'target_usd': 0.7}); cycle.save('', {'on': False}); T('cycle off: no rules even with a group target', cycle.rules('', 6) is None)
cycle.save('', {'on': True}); groupcap.save('', {'on': False}); T('group switch off: no rules', cycle.rules('', 6) is None)

cycle.save('', {'on': False}); T('off: no warning', cycle.why_not('', 6) == '')
cycle.save('', {'on': True}); T('group target off: tells the person to switch it on', 'group profit target' in cycle.why_not('', 6))
groupcap.save('', {'on': True, 'target_usd': 0}); T('group target 0: tells the person to set it', 'above 0' in cycle.why_not('', 6))
groupcap.save('', {'target_usd': 0.7}); T('one entry: tells the person to choose 2 or more', '2 or more' in cycle.why_not('', 1))
T('everything set: no warning', cycle.why_not('', 6) == '')

clean(); cycle.save('u1', {'on': True, 'max_per_day': 3}); T("one person's choices never reach another", cycle.get('u2') == {'on': False, 'max_per_day': 10} and cycle.get('') == {'on': False, 'max_per_day': 10})

r = c.get('/api/cycle'); T('the endpoint needs a signed-in person', r.status_code in (401, 403))
clean(); me = H('amy@x.com'); c.get('/api/me', headers=me)
r = c.get('/api/cycle', headers=me); j = r.get_json() if r.status_code == 200 else {}
T('GET shows the choices, the group target and a limits range', r.status_code == 200 and j.get('settings') == {'on': False, 'max_per_day': 10} and 'group' in j and j.get('limits') == {'max_per_day': [1, 100]})
r = c.post('/api/cycle', json={'on': True, 'max_per_day': 12}, headers=me); j = r.get_json()
T('POST saves and returns the view, with a plain-words note while the group target is off', r.status_code == 200 and j['settings'] == {'on': True, 'max_per_day': 12} and 'group profit target' in j['note'])
r = c.post('/api/cycle', json={'max_per_day': 0}, headers=me); T('POST with a bad number is a 400 with the message', r.status_code == 400 and 'whole number' in r.get_json()['error'])
T('a refused POST changed nothing', c.get('/api/cycle', headers=me).get_json()['settings']['max_per_day'] == 12)
r = c.post('/api/groupcap', json={'on': True, 'target_usd': 0.7}, headers=me); j = c.get('/api/cycle', headers=me).get_json()
T('after the group target is set the note is empty and the groupcap choices are untouched', j['note'] == '' and j['group'] == {'on': True, 'target_usd': 0.7, 'loss_pct': 0.0})
T("another person's choices stay separate", c.get('/api/cycle', headers=H('bob@x.com')).get_json()['settings'] == {'on': False, 'max_per_day': 10})

bad_ = [n for n, ok in R if not ok]
print('\n%d passed, %d failed' % (len(R) - len(bad_), len(bad_)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_ else 0)
