"""SC1: AI screen assistant, server side. Run from the repo folder: python apply_sc1.py (safe to run twice). Needs backend/screenread.py first."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print('skip (already there):', path, marker[:40]); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('edited', path)

edit('backend/store.py', "'max_trades_day': os.getenv('MAX_TRADES_DAY', '0'),", "'max_trades_day': os.getenv('MAX_TRADES_DAY', '0'), 'screen_on': '0',", "'screen_on': '0'")
edit('backend/app.py', "st.init(); assist.init()", "from . import screenread\nst.init(); assist.init(); screenread.init()", 'screenread.init()')
edit('backend/app.py', "for k in ('btc_sunday_bounce', 'btc_short_pullback', 'orb_session'):", "for k in ('btc_sunday_bounce', 'btc_short_pullback', 'orb_session', 'screen_on'):", "'orb_session', 'screen_on'")
edit('backend/app.py', "@app.get('/api/course')", '''@app.get('/api/screen/status')
@need(verified=True)
def screen_status(u):
    """SC1: is the screen assistant on, and how many reads are left today (trade and learn)."""
    return jsonify(screenread.status(u['uid'], bool(u['active'])))

@app.post('/api/screen/read')
@need(verified=True)
def screen_read(u):
    """SC1: one picture (base64 JPEG) in, the AI's read of the chart plus what the bot says about it out. Nothing is placed. The picture is never stored."""
    if (request.content_length or 0) > screenread.MAX_BODY: return jsonify(error='That picture is too big. Send one under about 600 KB.'), 413
    j = _j(); code, out = screenread.handle(u['uid'], str(j.get('context') or 'trade'), bool(u['active']), j.get('image'))
    return jsonify(out), code

@app.get('/api/course')''', "def screen_read(u)")
edit('.env.example', "# --- testing only: never set on Render ---", """# --- AI screen assistant (SC1). Off until the owner sets screen_on=1 in the admin settings ---
ANTHROPIC_API_KEY=           # key of the vision model that reads chart pictures. Only here on Render, never in the app
VISION_MODEL=claude-sonnet-5-5   # model name used for the reads
SCREEN_DAILY_CAP=60          # reads per person per day (paid plans)
SCREEN_LEARN_CAP=10          # reads per person per day inside the learning path (any verified person)
# --- testing only: never set on Render ---""", 'SCREEN_DAILY_CAP')
edit('README.md', "## Known limits", """## AI screen assistant (SC1, server side)
The AI only READS a chart picture; the bot's own strategies and safety rules answer (a dry run, nothing is placed). Set ANTHROPIC_API_KEY on Render, then `screen_on` = 1 in the admin settings. Paid plans use context `trade`, the learning path uses `learn`. The picture is never stored.

## Known limits""", 'AI screen assistant (SC1')
s = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Section SC1 (AI screen assistant, server side) DONE' not in s:
    s = s.rstrip('\n') + """

## Section SC1 (AI screen assistant, server side) DONE (Nov 22)
- New: backend/screenread.py, tests/test_sc1.py (36 checks; 17 deliberate breaks each went red: switch, plan, JPEG check, size, gap, daily cap, bias check, learn gate, blocked verdict, picture stored, unknown strategy ids, teach list, disagree, admin 0/1, default off, model error, no-data), apply_sc1.py (idempotent; edits backend/store.py default screen_on=0, backend/app.py import/init + GET /api/screen/status + POST /api/screen/read + screen_on in the 0/1 admin check, .env.example, README).
- OWNER'S RULE (Nov 22): the AI does NOT act on its own. It only READS the chart; then it TALKS to the bot in the back end (screenread.ask_bot = a dry run of the same scan: prefs, automode, strategy switches, brain.evaluate, risk gates). The bot answers in plain words: agree / disagree / no_setup / blocked ("this cannot work right now: <reason>. It does not trade.") / bot_only / no_data. Entry, stop and target are ALWAYS the bot's own, never the AI's. SC1 places nothing and saves no signal (test: signals table unchanged).
- Two contexts. trade = paid plan, cap SCREEN_DAILY_CAP (60). learn = the learning path (lessons + practice trades, C2/C3): any verified person, no plan, cap SCREEN_LEARN_CAP (10), the bot's trading gates (bot off, EA offline, max open, loss limits) are NOT applied so the lesson works, only the market rules (news lock, exposure) are described; the reply carries `teach` = plain descriptions of the strategies the chart looks like (strategy_info.desc). It must never create a signal or trade in learn.
- Rules kept: off by default (setting screen_on, admin 0/1); JPEG only, base64 up to 800000 characters (413); 10 s between reads (429); the picture lives only inside handle(), never in a table, a log or an error message (test searches every table and the log); the AI answer is checked against a strict shape, anything else = "I could not read this chart"; a down AI service = 502 in plain words and still counts for the gap.
- Provider: screenread.call_model (default Anthropic vision through requests; env ANTHROPIC_API_KEY, VISION_MODEL default claude-sonnet-5-5). NOT tested against the real service (no key / no network here): the first real read must be tried by hand with a real chart picture; the prompt may need tuning.
- Honest limits: ask_bot copies the scan steps of app._scan_tf (it does not call it, to leave the live scan untouched), so if _scan_tf changes, ask_bot must be changed the same way. It reads the candles the server already holds for that market (the person's own, else the owner's feed); a market with no candles gets no_data. Only XAUUSD / BTCUSD aliases are mapped by name; other names must equal a symbol the server tracks. The learning path itself is unchanged: a read does not count as a lesson or a practice trade (owner can ask for that later).
- Next: SC2 (website + app page: the "Screen assistant" card on the Bot tab and a "Ask the AI about this chart" step inside the learning path screens, desktop-browser capture, new IL2.eye cartoon).
"""
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(s + '\n'); print('HANDOFF updated')
else: print('skip (already there): HANDOFF SC1')
print('SC1 applied')
