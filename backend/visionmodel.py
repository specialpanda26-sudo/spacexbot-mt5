"""SC1b: which AI model reads the chart picture. One function, ask(jpeg_b64, prompt) -> the model's text. The owner picks the provider in the admin panel
(setting vision_provider) and may set a model name (setting vision_model). KEYS LIVE ONLY IN ENV VARS ON RENDER: never in the database, never in a reply, never in an error
message. Web addresses are fixed here (or OPENAI_BASE_URL from the env for 'custom'), so the admin panel cannot point the server at an address of its choosing.
Providers: anthropic (Anthropic messages API), grok / gemini / custom (any OpenAI-style /chat/completions endpoint that accepts an image_url)."""
import os, re
import requests
from . import store as st

class ModelError(Exception): pass

NOT_SET = 'The AI reader is not set up yet. The owner must add its key on the server.'
PROVIDERS = {
    'anthropic': {'label': 'Anthropic (Claude)', 'kind': 'anthropic', 'key': 'ANTHROPIC_API_KEY', 'model': 'claude-sonnet-5-5', 'url': 'https://api.anthropic.com/v1/messages'},
    'grok': {'label': 'Grok (xAI)', 'kind': 'openai', 'key': 'XAI_API_KEY', 'model': 'grok-4', 'url': 'https://api.x.ai/v1'},
    'gemini': {'label': 'Gemini (Google)', 'kind': 'openai', 'key': 'GEMINI_API_KEY', 'model': 'gemini-2.5-flash', 'url': 'https://generativelanguage.googleapis.com/v1beta/openai'},
    'custom': {'label': 'Any OpenAI-style service', 'kind': 'openai', 'key': 'OPENAI_API_KEY', 'model': '', 'url': ''},
}
DEFAULT = 'anthropic'
MODEL_OK = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}$')
TIMEOUT = 25

def provider():
    p = st.get('vision_provider') or DEFAULT
    return p if p in PROVIDERS else DEFAULT

def model_for(p):
    """Admin's model name first; for Anthropic the old VISION_MODEL env still works; then the provider's default (custom has none)."""
    m = (st.get('vision_model') or '').strip()
    if not m and p == 'anthropic': m = os.getenv('VISION_MODEL', '').strip()
    return m or PROVIDERS[p]['model']

def base_url(p):
    if p == 'custom': return os.getenv('OPENAI_BASE_URL', '').strip().rstrip('/')
    return PROVIDERS[p]['url']

def key_set(p): return bool(os.getenv(PROVIDERS[p]['key'], '').strip())

def status():
    p = provider()
    return {'provider': p, 'model': model_for(p), 'providers': [
        {'id': i, 'label': d['label'], 'key_env': d['key'], 'key_set': key_set(i), 'default_model': d['model'] or None, 'url_env': 'OPENAI_BASE_URL' if i == 'custom' else None}
        for i, d in PROVIDERS.items()], 'note': 'Keys are set on Render as environment variables. They are never shown or stored here.'}

def configure(j):
    """Admin change: {'provider': id, 'model': name}. Switching provider without a model clears the model, so a name for one service is never sent to another.
    -> (ok, error text)."""
    if 'provider' in j:
        if not isinstance(j['provider'], str) or j['provider'] not in PROVIDERS: return False, 'provider must be one of: ' + ', '.join(PROVIDERS)
    if 'model' in j and not (isinstance(j['model'], str) and (j['model'] == '' or MODEL_OK.match(j['model']))): return False, 'model must be a plain model name (letters, digits, . _ : / -).'
    if 'provider' in j:
        if j['provider'] != provider(): st.put('vision_model', '')
        st.put('vision_provider', j['provider'])
    if 'model' in j: st.put('vision_model', j['model'])
    return True, ''

def _http(url, headers, body):
    try: r = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)
    except requests.RequestException: raise ModelError('The AI reader did not answer. Try again in a moment.')
    if r.status_code in (401, 403): raise ModelError('The AI reader rejected its key (%d). The owner must check the key on the server.' % r.status_code)
    if r.status_code != 200: raise ModelError('The AI reader did not answer (%d). Try again in a moment.' % r.status_code)
    try: return r.json()
    except ValueError: raise ModelError('The AI reader sent something unreadable.')

def _anthropic(p, key, model, jpeg_b64, prompt):
    body = {'model': model, 'max_tokens': 600, 'messages': [{'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': jpeg_b64}}, {'type': 'text', 'text': prompt}]}]}
    d = _http(PROVIDERS[p]['url'], {'x-api-key': key, 'anthropic-version': '2023-06-01'}, body)
    try: return ''.join(b.get('text', '') for b in d.get('content', []) if b.get('type') == 'text')
    except (AttributeError, TypeError): raise ModelError('The AI reader sent something unreadable.')

def _openai(p, key, model, jpeg_b64, prompt):
    base = base_url(p)
    if not base.startswith('https://'): raise ModelError(NOT_SET if not base else 'The owner must set OPENAI_BASE_URL to an https:// address.')
    if not model: raise ModelError('The owner must pick a model name for this service in the admin panel.')
    body = {'model': model, 'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + jpeg_b64}}]}]}
    d = _http(base + '/chat/completions', {'Authorization': 'Bearer ' + key}, body)
    try: c = d['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError): raise ModelError('The AI reader sent something unreadable.')
    if isinstance(c, list): c = ''.join(x.get('text', '') for x in c if isinstance(x, dict))
    return c if isinstance(c, str) else ''

def ask(jpeg_b64, prompt, which=None):
    """The picture goes to the chosen model; its text comes back. Raises ModelError with plain words."""
    p = which or provider(); key = os.getenv(PROVIDERS[p]['key'], '').strip()
    if not key: raise ModelError(NOT_SET)
    return (_anthropic if PROVIDERS[p]['kind'] == 'anthropic' else _openai)(p, key, model_for(p), jpeg_b64, prompt)
