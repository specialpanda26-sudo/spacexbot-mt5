"""SC1b: choose the AI model that reads the chart (Anthropic / Grok / Gemini / any OpenAI-style service). Run from the repo folder: python apply_sc1b.py (safe to run twice).
Needs backend/visionmodel.py (paste block 1 first) and SC1 applied."""
import sys, os
if not os.path.exists('backend/visionmodel.py'): print('STOP: backend/visionmodel.py is missing, paste block 1 first'); sys.exit(1)
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, s): open(p, 'w', encoding='utf-8').write(s)
def edit(path, old, new, marker):
    s = rd(path)
    if marker in s: print('skip (already there):', path, marker[:40]); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    wr(path, s.replace(old, new, 1)); print('edited', path)

TINY = ('/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABQODxIPDRQSEBIXFRQYHjIhHhwcHj0sLiQySUBMS0dARkVQWnNiUFVtVkVGZIhlbXd7gYKBTmCNl4x9lnN+gXz/2wBDARUXFx4aHjshITt8U0ZTfHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHx8fHz/wAARCABkAKADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDq6KKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKAP/Z')

# ---- backend/screenread.py: use visionmodel instead of the one built-in Anthropic call ----
P = 'backend/screenread.py'; s = rd(P)
if 'vm.ask(' in s: print('skip (already there):', P)
else:
    a = s.find('def _anthropic(jpeg_b64):'); b = s.find('call_model = _anthropic')
    if a < 0 or b < a: print('STOP: cannot find the old _anthropic block in', P); sys.exit(1)
    b = s.find('\n', b) + 1
    new = ('def _prompt(): return PROMPT % \', \'.join(sorted(si.INFO))\n'
           'def _anthropic(jpeg_b64): return vm.ask(jpeg_b64, _prompt(), \'anthropic\')      # kept for the tests\n'
           'def _chosen(jpeg_b64): return vm.ask(jpeg_b64, _prompt())                   # the provider the owner picked (backend/visionmodel.py)\n\n'
           'call_model = _chosen      # call_model(jpeg_b64) -> text. Tests replace it.\n')
    s = s[:a] + new + s[b:]
    for old, rep in (("class ModelError(Exception): pass", "ModelError = vm.ModelError"),
                     ("strategy_info as si\n", "strategy_info as si, visionmodel as vm\n")):
        if s.count(old) != 1: print('STOP: cannot find exactly once in', P, '->', old); sys.exit(1)
        s = s.replace(old, rep, 1)
    s = s.rstrip('\n') + '''

TINY = '%s'      # a blank 160x100 JPEG for the admin test button

def check_model():
    """Admin test button: send a blank picture to the chosen provider and run the answer through the SAME shape check as a real read. Nothing is saved or counted."""
    p = vm.provider(); out = {'provider': p, 'model': vm.model_for(p)}
    try: text = call_model(TINY)
    except ModelError as e: return dict(out, ok=False, error=str(e))
    if parse(text) is None: return dict(out, ok=False, error='The service answered, but not in the shape the bot needs (one JSON object). Try another model name.')
    return dict(out, ok=True, text='Connected. The service answered in the right shape.')
''' % TINY
    wr(P, s); print('edited', P)

# ---- backend/app.py: admin routes ----
edit('backend/app.py', "@app.get('/api/admin/btc')", '''@app.get('/api/admin/screenmodel')
@need(admin=True)
def admin_screenmodel_get(u): return jsonify(screenread.vm.status())

@app.post('/api/admin/screenmodel')
@need(admin=True)
def admin_screenmodel_set(u):
    """SC1b: pick the AI provider / model that reads chart pictures, or {check:true} to test it. Keys are env vars on Render and never pass through here."""
    j = _j()
    if j.get('check'): return jsonify(screenread.check_model())
    ok, err = screenread.vm.configure(j)
    if not ok: return jsonify(error=err), 400
    return jsonify(screenread.vm.status())

@app.get('/api/admin/btc')''', "def admin_screenmodel_get")

# ---- docs ----
edit('.env.example', "SCREEN_DAILY_CAP=60 ", """# Pick the provider in the admin panel (Screen assistant > AI model). Set ONLY the key of the one you pick. Keys stay here, never in the app or the database.
XAI_API_KEY=                 # Grok (xAI)
GEMINI_API_KEY=              # Gemini (Google AI Studio)
OPENAI_API_KEY=              # 'custom': any OpenAI-style service ...
OPENAI_BASE_URL=             # ... and its address, https:// only, e.g. https://api.example.com/v1 (no trailing /chat/completions)
SCREEN_DAILY_CAP=60 """, 'XAI_API_KEY')
edit('README.md', "The picture is never stored.\n", "The picture is never stored.\nWhich AI reads the picture is the owner's choice (admin: `GET/POST /api/admin/screenmodel`, body `{provider, model}` or `{check:true}`): `anthropic`, `grok`, `gemini` or `custom` (any OpenAI-style service). Set only that provider's key on Render (ANTHROPIC_API_KEY, XAI_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY + OPENAI_BASE_URL).\n", 'screenmodel')
s = rd('docs/HANDOFF.md')
if '## Section SC1b' in s: print('skip (already there): HANDOFF SC1b')
else:
    wr('docs/HANDOFF.md', s.rstrip('\n') + """

## Section SC1b (model switch) DONE (Nov 22)
- New: backend/visionmodel.py (providers anthropic / grok / gemini / custom; ask(jpeg_b64, prompt) -> text; status(); configure()), tests/test_sc1b.py, apply_sc1b.py. screenread.call_model now = the provider the owner picked; screenread.ModelError is visionmodel.ModelError; screenread.check_model() = the admin test button (blank JPEG through the same parse() shape check, nothing saved, nothing counted).
- Admin: GET /api/admin/screenmodel (provider, effective model, per provider: key_set true/false, key env name, default model) and POST {provider, model} or {check:true}. Switching provider without a model clears the saved model so one service's model name is never sent to another. Settings: vision_provider (default anthropic), vision_model (default empty = provider default; for Anthropic the old VISION_MODEL env still works).
- Keys only in env vars on Render: ANTHROPIC_API_KEY, XAI_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY + OPENAI_BASE_URL (custom). Never stored, never returned, never in an error (test). Addresses are fixed in code; custom takes OPENAI_BASE_URL from the env only and must be https:// (the admin panel cannot choose an address).
- Honest limits: NOT run against any real service (no keys / no network here). Default model names (grok-4, gemini-2.5-flash) are my best guess and may need changing in the admin panel; OpenAI-style requests send no max_tokens (some models reject that field), so a reply is bounded only by the 25 s timeout. Gemini is reached through its OpenAI-compatible address. Run the test button, then one real chart read by hand, before trusting a provider. No admin-panel card yet (the routes work; the card can come with SC2's admin switch).
- Next: SC3 (Android native overlay + screen capture, needs an APK rebuild).
""")
    print('HANDOFF updated')
print('SC1b applied')
