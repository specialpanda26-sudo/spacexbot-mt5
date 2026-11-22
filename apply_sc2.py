"""Section SC2: the Screen assistant card with the talking panel (website / desktop browser).
 - static/index.html: new IL2.eye cartoon (the site's character with a magnifier over candles) inside the rk2 picture closure, and the script tag for static/screen.js.
 - docs/HANDOFF.md: SC2 section.
static/screen.js itself is a new file (pasted with cat). Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
# 1 the eye cartoon: three candles, a magnifier sweeping over them, sparkles, the same character as every other IL2 picture
EYE = ("IL2.eye=il('<g transform=\"translate(12 40)\">'+seq([['rect x=\"0\" y=\"34\" width=\"12\" height=\"40\" rx=\"3\"',G],['rect x=\"20\" y=\"14\" width=\"12\" height=\"60\" rx=\"3\"',B],['rect x=\"40\" y=\"40\" width=\"12\" height=\"34\" rx=\"3\"',G]])"
       "+ln('M6 24v10M6 74v8M26 4v10M26 74v6M46 30v10M46 74v8',3)+'</g>'"
       "+'<g class=\"mg\">'+ln('M92 82l14 16',6)+seq([['circle cx=\"78\" cy=\"62\" r=\"22\"',W]])+ln('M66 56q6-8 16-6',3.5,S[1])+'</g>'"
       "+sp('M96 22v10M91 27h10')+sp('M10 112v8M6 116h8'));\n")
edit(P, "sp('M30 24v8M26 28h8'));\n})();\nvar ILM={", "sp('M30 24v8M26 28h8'));\n" + EYE + "})();\nvar ILM={", 'IL2.eye=il(')
# 2 the script, right after the Trade on card script
edit(P, '<script src="/static/trade_on.js"></script>', '<script src="/static/trade_on.js"></script><script src="/static/screen.js"></script>', '/static/screen.js')
# 3 handoff
H = 'docs/HANDOFF.md'
NOTE = '''
## Section SC2 (Screen assistant card + talking panel, website) DONE (Nov 22)
- New static/screen.js (card "Screen assistant" at the top of the Bot tab, like static/trade_on.js), new IL2.eye cartoon in static/index.html (apply_sc2.py), tests/test_sc2.py. Server code untouched.
- Flow: Watch -> getDisplayMedia (desktop browsers; a phone browser gets a plain-words "cannot share" message) -> one JPEG (long side 1280, quality 0.7/0.55/0.4 until under 780000 base64 chars) -> POST /api/screen/read {context:"trade"} now and every 20 s (never faster than the server gap + 1 s), or Read now -> the card answers. The picture is a local variable only: not in storage, not in the page, dropped after the reply.
- Talking panel (cartoon + speech bubble + plain-word lines): idle/scanning = IL2.eye; bot agrees = IL2.ok "I see a possible trade."; blocked = IL2.shield (IL2.sleep when the reason is weekend/Friday night/Bitcoin rests); disagree, no setup, bot-only, no candles = IL2.wait; chart not readable = IL2.off; 429 = wait, 402 = coin, 403 = off, other errors = IL2.cx. Text under the bubble: market, timeframe, trend, support/resistance, patterns, AI lean, and the BOT'S OWN entry / stop / target (never the AI's).
- Levels: Explain works; Suggest and Auto are shown as "soon" and disabled (SC4, SC5). Not yet in this section: the "Ask the AI about this chart" step in the learning path (context "learn"), nothing yet places a trade.
- The card shows when the server switch screen_on is on, or for an admin; an admin sees "Switch it on / off" (POST /api/admin/settings {screen_on:"1"|"0"}). With it off, Watch is disabled and the chip says Off. No plan = chip "Plan needed".
- Motion (magnifier sweeps, Watching chip pulses) only inside @media (prefers-reduced-motion:no-preference). CSS uses the site's variables only.
- NOT tested: a real browser share, a real model reply (needs ANTHROPIC_API_KEY today; the model choice is the owner's, see SC1b).
- Next: SC1b (model switch: Grok / Gemini / Anthropic / other), then SC3.
'''
s = open(H, encoding='utf-8').read()
if 'Section SC2 (Screen assistant card' in s: print(H, ': already ok')
else: open(H, 'a', encoding='utf-8').write(NOTE); print(H, ': edited')
