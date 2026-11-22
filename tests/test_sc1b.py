"""SC1b checks: which AI reads the chart (provider switch, keys, test button). Fake web service, no network. Run: python tests/test_sc1b.py"""
import os, sys, time, glob, json, base64
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_sc1b_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD', SCREEN_LEARN_CAP='20')
for k in ('ANTHROPIC_API_KEY', 'XAI_API_KEY', 'GEMINI_API_KEY', 'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'VISION_MODEL'): os.environ.pop(k, None)
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, screenread as sr, visionmodel as vm, bars, brain, alerts
import requests
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
B64 = 'QUJD'; PROMPT = 'read this'
GOOD = {'readable': True, 'symbol': 'XAUUSD', 'timeframe': 'M15', 'trend': 'up', 'bias': 'buy', 'patterns': [], 'support': [1990], 'resistance': [2010], 'last_price': 2000, 'strategies': [], 'note': 'ok'}
SECRETS = {'ANTHROPIC_API_KEY': 'SECRET-ANT-111', 'XAI_API_KEY': 'SECRET-XAI-222', 'GEMINI_API_KEY': 'SECRET-GEM-333', 'OPENAI_API_KEY': 'SECRET-OAI-444'}

class Resp:
    def __init__(s, code=200, data=None, bad=False): s.status_code = code; s._d = data; s._bad = bad
    def json(s):
        if s._bad: raise ValueError('no json')
        return s._d
sent = []
def web(resp):
    def post(url, json=None, headers=None, timeout=None):
        sent.append({'url': url, 'json': json, 'headers': headers, 'timeout': timeout})
        if isinstance(resp, Exception): raise resp
        return resp
    vm.requests.post = post
ANT_OK = lambda t: Resp(200, {'content': [{'type': 'text', 'text': t}]})
OAI_OK = lambda t: Resp(200, {'choices': [{'message': {'content': t}}]})
def admin(body=None, who='boss@x.com'): return c.post('/api/admin/screenmodel', json=body or {}, headers=H(who))
def err(fn):
    try: fn(); return ''
    except vm.ModelError as e: return str(e)

# ---- defaults, admin only ----
T('default provider is anthropic, model = its default', vm.provider() == 'anthropic' and vm.model_for('anthropic') == 'claude-sonnet-5-5')
T('signed out: 401', c.get('/api/admin/screenmodel').status_code == 401 and c.post('/api/admin/screenmodel', json={}).status_code == 401)
T('not an admin: 403 on read and change', c.get('/api/admin/screenmodel', headers=H('amy@x.com')).status_code == 403 and admin({'provider': 'grok'}, 'amy@x.com').status_code == 403)
T('a refused change changed nothing', vm.provider() == 'anthropic')
j = c.get('/api/admin/screenmodel', headers=H('boss@x.com')).get_json()
T('status lists the four providers with key_set false', [p['id'] for p in j['providers']] == ['anthropic', 'grok', 'gemini', 'custom'] and not any(p['key_set'] for p in j['providers']))

# ---- keys are never shown ----
os.environ.update(SECRETS)
r = c.get('/api/admin/screenmodel', headers=H('boss@x.com')); j = r.get_json()
T('keys set: status says true per provider', all(p['key_set'] for p in j['providers']))
T('no key value appears in the status reply', not any(v in r.get_data(as_text=True) for v in SECRETS.values()))

# ---- choosing ----
T('unknown provider: 400, nothing changed', admin({'provider': 'bing'}).status_code == 400 and admin({'provider': ['grok']}).status_code == 400 and vm.provider() == 'anthropic')
T('model with odd characters: 400', admin({'model': 'x; rm -rf'}).status_code == 400 and admin({'model': 5}).status_code == 400 and admin({'model': 'a' * 90}).status_code == 400)
j = admin({'provider': 'grok', 'model': 'grok-test-1'}).get_json()
T('grok with a model: saved and shown', j['provider'] == 'grok' and j['model'] == 'grok-test-1' and vm.provider() == 'grok')
j = admin({'provider': 'gemini'}).get_json()
T('switching provider without a model clears the old model name', j['provider'] == 'gemini' and j['model'] == 'gemini-2.5-flash' and not st.get('vision_model'))
j = admin({'provider': 'gemini'}).get_json()
T('choosing the same provider again keeps a saved model', admin({'model': 'gem-x'}).get_json()['model'] == 'gem-x' and admin({'provider': 'gemini'}).get_json()['model'] == 'gem-x')
admin({'provider': 'anthropic'}); os.environ['VISION_MODEL'] = 'claude-old-env'
T('anthropic: the old VISION_MODEL env still works', vm.model_for('anthropic') == 'claude-old-env')
admin({'provider': 'grok'}); T('the env model is not sent to another provider', vm.model_for('grok') == 'grok-4'); os.environ.pop('VISION_MODEL')

# ---- what is sent to each service ----
admin({'provider': 'anthropic', 'model': 'claude-test'}); sent.clear(); web(ANT_OK('hello'))
T('anthropic: text comes back', vm.ask(B64, PROMPT) == 'hello')
q = sent[0]
T('anthropic: address, key header, model, picture block', q['url'] == 'https://api.anthropic.com/v1/messages' and q['headers'].get('x-api-key') == SECRETS['ANTHROPIC_API_KEY']
  and q['json']['model'] == 'claude-test' and q['json']['messages'][0]['content'][0]['source']['data'] == B64 and q['timeout'] == vm.TIMEOUT)
admin({'provider': 'grok', 'model': 'grok-test'}); sent.clear(); web(OAI_OK('from grok'))
T('grok: text comes back', vm.ask(B64, PROMPT) == 'from grok')
q = sent[0]; parts = q['json']['messages'][0]['content']
T('grok: x.ai address, Bearer key, model', q['url'] == 'https://api.x.ai/v1/chat/completions' and q['headers'] == {'Authorization': 'Bearer ' + SECRETS['XAI_API_KEY']} and q['json']['model'] == 'grok-test')
T('grok: prompt and the picture as a data address', parts[0] == {'type': 'text', 'text': PROMPT} and parts[1]['image_url']['url'] == 'data:image/jpeg;base64,' + B64)
admin({'provider': 'gemini', 'model': ''}); sent.clear(); web(OAI_OK('from gemini')); vm.ask(B64, PROMPT)
T('gemini: google address and its own key', sent[0]['url'] == 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions' and sent[0]['headers']['Authorization'] == 'Bearer ' + SECRETS['GEMINI_API_KEY'])
T('only the chosen provider\'s key is sent', SECRETS['XAI_API_KEY'] not in json.dumps(sent[0]) and SECRETS['ANTHROPIC_API_KEY'] not in json.dumps(sent[0]))
web(Resp(200, {'choices': [{'message': {'content': [{'type': 'text', 'text': 'part A '}, {'type': 'text', 'text': 'part B'}]}}]}))
T('a reply made of parts is joined', vm.ask(B64, PROMPT) == 'part A part B')

# ---- custom service ----
admin({'provider': 'custom'}); web(OAI_OK('x'))
T('custom: no address set -> owner must set it up', 'owner must add' in err(lambda: vm.ask(B64, PROMPT)))
os.environ['OPENAI_BASE_URL'] = 'http://insecure.example.com/v1'; n = len(sent)
T('custom: http:// refused and nothing is sent', 'https://' in err(lambda: vm.ask(B64, PROMPT)) and len(sent) == n)
os.environ['OPENAI_BASE_URL'] = 'https://api.example.com/v1/'
T('custom: no model name -> plain words, nothing sent', 'pick a model' in err(lambda: vm.ask(B64, PROMPT)) and len(sent) == n)
admin({'model': 'my-vision'}); sent.clear(); web(OAI_OK('from custom')); T('custom: works with address + model', vm.ask(B64, PROMPT) == 'from custom')
T('custom: address from the env, trailing slash handled, own key', sent[0]['url'] == 'https://api.example.com/v1/chat/completions' and sent[0]['headers']['Authorization'] == 'Bearer ' + SECRETS['OPENAI_API_KEY'])
T('the address cannot be set from the admin panel', admin({'provider': 'custom', 'url': 'https://evil.example'}).status_code == 200 and sent[-1]['url'].startswith('https://api.example.com'))
admin({'provider': 'custom'}); web(OAI_OK('again')); vm.ask(B64, PROMPT)
T('(after that call) still the env address', sent[-1]['url'].startswith('https://api.example.com/v1/'))

# ---- failures in plain words, never the key ----
admin({'provider': 'grok', 'model': 'g'}); n = len(sent)
os.environ.pop('XAI_API_KEY'); web(OAI_OK('x'))
T('no key: owner must add it, nothing sent', 'owner must add' in err(lambda: vm.ask(B64, PROMPT)) and len(sent) == n)
os.environ['XAI_API_KEY'] = SECRETS['XAI_API_KEY']
for name, resp, want in (('401', Resp(401, {}), 'rejected its key'), ('403', Resp(403, {}), 'rejected its key'), ('500', Resp(500, {}), 'did not answer (500)'),
                         ('429', Resp(429, {}), 'did not answer (429)'), ('not JSON', Resp(200, bad=True), 'unreadable'), ('no choices', Resp(200, {'x': 1}), 'unreadable'),
                         ('network down', requests.ConnectionError('boom ' + SECRETS['XAI_API_KEY']), 'did not answer')):
    web(resp); m = err(lambda: vm.ask(B64, PROMPT))
    T('grok %s -> plain words' % name, want in m)
    T('grok %s -> the key is not in the message' % name, SECRETS['XAI_API_KEY'] not in m)
admin({'provider': 'anthropic'}); web(Resp(401, {})); m = err(lambda: vm.ask(B64, PROMPT))
T('anthropic 401 -> rejected key, key not shown', 'rejected its key' in m and SECRETS['ANTHROPIC_API_KEY'] not in m)
web(Resp(200, {'content': 'not a list'})); T('anthropic odd reply -> unreadable', 'unreadable' in err(lambda: vm.ask(B64, PROMPT)))

# ---- the real read goes through the chosen provider ----
st.put('screen_on', '1')
rows = [(1_700_000_000 + i * 900, 2000, 2001, 1999, 2000, 1) for i in range(130)]
bars.merge('XAUUSD', 'M15', rows); bars.merge('XAUUSD', 'H1', rows)
IMG = base64.b64encode(b'\xff\xd8\xff\xe0' + b'PIXELS-77' + b'\x00' * 50).decode()
def read(who='amy@x.com'):
    st.put('screen:last:dev-' + who, 0); return c.post('/api/screen/read', json={'image': IMG, 'context': 'learn'}, headers=H(who))
admin({'provider': 'grok', 'model': 'grok-e2e'}); sent.clear(); web(OAI_OK(json.dumps(GOOD)))
r = read(); j = r.get_json()
T('screen read: goes to grok, comes back checked', r.status_code == 200 and j['read']['readable'] and j['read']['symbol'] == 'XAUUSD' and sent and sent[0]['url'].startswith('https://api.x.ai/'))
T('screen read: the real prompt (with the strategy list) and the picture were sent', 'Answer with ONE JSON object' in sent[0]['json']['messages'][0]['content'][0]['text'] and IMG in json.dumps(sent[0]['json']))
web(OAI_OK('I think it goes up')); j = read().get_json()
T('screen read: a model that answers in the wrong shape -> unreadable, no bot verdict', j['read']['readable'] is False and j['bot'] is None)
web(Resp(500, {})); r = read(); T('screen read: service down -> 502 in plain words', r.status_code == 502 and 'did not answer' in r.get_json()['error'])
os.environ.pop('XAI_API_KEY'); r = read(); T('screen read: grok chosen but no key -> 502, owner must add it', r.status_code == 502 and 'owner must add' in r.get_json()['error'])
os.environ['XAI_API_KEY'] = SECRETS['XAI_API_KEY']

# ---- the test button ----
nrows = st.q('SELECT COUNT(*) n FROM screen_reads', (), True)['n']
web(OAI_OK(json.dumps({'readable': False, 'note': 'blank picture'}))); sent.clear(); j = admin({'check': True}).get_json()
T('test button: ok when the answer has the right shape', j['ok'] is True and j['provider'] == 'grok' and j['model'] == 'grok-e2e')
T('test button: sends a real JPEG and the real prompt', base64.b64decode(sent[0]['json']['messages'][0]['content'][1]['image_url']['url'].split(',', 1)[1])[:3] == b'\xff\xd8\xff')
web(OAI_OK('Sure! Here is my opinion')); j = admin({'check': True}).get_json()
T('test button: wrong shape -> not ok, says to try another model', j['ok'] is False and 'shape' in j['error'])
web(Resp(401, {})); j = admin({'check': True}).get_json()
T('test button: rejected key -> not ok, in plain words', j['ok'] is False and 'rejected its key' in j['error'])
os.environ.pop('XAI_API_KEY'); j = admin({'check': True}).get_json()
T('test button: no key -> not ok', j['ok'] is False and 'owner must add' in j['error']); os.environ['XAI_API_KEY'] = SECRETS['XAI_API_KEY']
T('test button: admin only', admin({'check': True}, 'amy@x.com').status_code == 403)
T('test button: counted nowhere (screen_reads unchanged)', st.q('SELECT COUNT(*) n FROM screen_reads', (), True)['n'] == nrows)
T('test button: changes no setting', vm.provider() == 'grok' and vm.model_for('grok') == 'grok-e2e')
for f in glob.glob(DB + '*'): os.remove(f)
p = sum(1 for _, o in R if o); print('%d/%d passed' % (p, len(R))); sys.exit(0 if p == len(R) else 1)
