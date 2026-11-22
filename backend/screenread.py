"""SC1 (AI screen assistant, server side only). One picture of a chart comes in; a vision model READS it; then the bot is ASKED what it thinks.
The AI never trades and never invents an entry, stop or target. It only reads. The bot's own strategies and safety rules answer (a dry run of the
same scan the bot uses, nothing is saved as a signal, nothing is placed). Two contexts: 'trade' (paid plan) and 'learn' (the learning path: any
verified person, small daily cap, teaching words, the bot's trading gates are described but never block the lesson). The picture is never stored or logged:
only the short JSON read, the time and the verdict go into screen_reads. Switch: setting screen_on (default 0). Provider: call_model (Anthropic vision by
default, key only in the ANTHROPIC_API_KEY env var; tests replace call_model)."""
import os, re, json, time, math, base64
import requests
from . import store as st, bars, brain, risk, prefs, automode, stats, regime as rgm, strategy_info as si

MAX_B64 = 800_000            # about 600 KB of picture
MAX_BODY = MAX_B64 + 2_000
GAP = 10                     # seconds between two reads of one person
NOTE = 'A read of your screen, not advice.'
ALIAS = {'GOLD': 'XAUUSD', 'XAUUSD': 'XAUUSD', 'BTCUSD': 'BTCUSD', 'BTCUSDT': 'BTCUSD', 'BITCOIN': 'BTCUSD'}

class ModelError(Exception): pass

def init():
    st.x('CREATE TABLE IF NOT EXISTS screen_reads(uid TEXT,ts BIGINT,ctx TEXT,symbol TEXT,bias TEXT,verdict TEXT,data TEXT)')

def cap(ctx):
    k, d = ('SCREEN_LEARN_CAP', 10) if ctx == 'learn' else ('SCREEN_DAILY_CAP', 60)
    try: n = int(os.getenv(k, d))
    except ValueError: n = d
    return max(0, n)

def used(uid, ctx):
    return st.q('SELECT COUNT(*) n FROM screen_reads WHERE uid=? AND ctx=? AND ts>=?', (uid, ctx, st.day_start()), True)['n']

def on(): return st.get('screen_on') == '1'

def status(uid, paid):
    return {'on': on(), 'trade': {'allowed': bool(paid), 'used': used(uid, 'trade'), 'cap': cap('trade')},
            'learn': {'allowed': True, 'used': used(uid, 'learn'), 'cap': cap('learn')}, 'gap': GAP, 'note': NOTE}

PROMPT = ('You are reading ONE screenshot of a trading chart. Answer with ONE JSON object and nothing else. Never guess: if you cannot clearly read the market name, '
          'the chart or the price, answer {"readable": false, "note": "why"}. Otherwise: {"readable": true, "symbol": "market name as shown", "timeframe": "e.g. M15 or unknown", '
          '"trend": "up|down|range|unclear", "bias": "buy|sell|none", "patterns": ["up to 5 short names"], "support": [up to 4 prices], "resistance": [up to 4 prices], '
          '"last_price": number or null, "strategies": [ids from this list that the chart looks like: %s], "note": "one plain sentence"}. '
          'No advice, no promises, no entry or stop prices.')

def _anthropic(jpeg_b64):
    key = os.getenv('ANTHROPIC_API_KEY', '')
    if not key: raise ModelError('The AI reader is not set up yet. The owner must add its key on the server.')
    body = {'model': os.getenv('VISION_MODEL', 'claude-sonnet-5-5'), 'max_tokens': 600, 'messages': [{'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': jpeg_b64}},
        {'type': 'text', 'text': PROMPT % ', '.join(sorted(si.INFO))}]}]}
    try: r = requests.post('https://api.anthropic.com/v1/messages', json=body, timeout=25, headers={'x-api-key': key, 'anthropic-version': '2023-06-01'})
    except requests.RequestException: raise ModelError('The AI reader did not answer. Try again in a moment.')
    if r.status_code != 200: raise ModelError('The AI reader did not answer (%d). Try again in a moment.' % r.status_code)
    try: return ''.join(b.get('text', '') for b in r.json().get('content', []) if b.get('type') == 'text')
    except ValueError: raise ModelError('The AI reader sent something unreadable.')

call_model = _anthropic      # call_model(jpeg_b64) -> text. Tests replace it.

def _nums(v, n=4):
    if not isinstance(v, list): return None
    out = []
    for x in v[:n]:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0: return None
        out.append(float(x))
    return out

def parse(text):
    """The model's text -> a checked read, or None when it is not what was asked for. Unreadable charts come back as {'readable': False}."""
    t = str(text or ''); a, b = t.find('{'), t.rfind('}')
    try: d = json.loads(t[a:b + 1]) if 0 <= a < b else None
    except ValueError: d = None
    if not isinstance(d, dict) or not isinstance(d.get('readable'), bool): return None
    note = str(d.get('note') or '')[:240]
    if not d['readable']: return {'readable': False, 'note': note or 'I could not read this chart.'}
    sym, tf = d.get('symbol'), d.get('timeframe')
    if not isinstance(sym, str) or not sym.strip() or len(sym) > 40 or not isinstance(tf, str) or len(tf) > 12: return None
    if d.get('trend') not in ('up', 'down', 'range', 'unclear') or d.get('bias') not in ('buy', 'sell', 'none'): return None
    pats = d.get('patterns', [])
    if not isinstance(pats, list) or not all(isinstance(p, str) for p in pats): return None
    sup, res = _nums(d.get('support', [])), _nums(d.get('resistance', []))
    if sup is None or res is None: return None
    lp = d.get('last_price')
    if lp is not None and (isinstance(lp, bool) or not isinstance(lp, (int, float)) or not math.isfinite(lp) or lp <= 0): return None
    ids = [x for x in (d.get('strategies') or []) if isinstance(x, str) and x in si.INFO][:6] if isinstance(d.get('strategies', []), list) else []
    return {'readable': True, 'symbol': sym.strip(), 'timeframe': tf.strip(), 'trend': d['trend'], 'bias': d['bias'], 'patterns': [p[:40] for p in pats[:5]],
            'support': sup, 'resistance': res, 'last_price': float(lp) if lp is not None else None, 'strategies': ids, 'note': note}

def canon(name):
    k = re.sub(r'[^A-Z0-9]', '', str(name or '').upper())
    return ALIAS.get(k, k) if k else ''

def _v(code, text, sig=None): return {'code': code, 'text': text, 'signal': sig}

def ask_bot(uid, read, ctx):
    """Talk to the bot: a DRY RUN of its scan on the market in the picture. Nothing is saved or placed."""
    sym = canon(read.get('symbol'))
    m = bars.get(sym, 'M15', uid) or bars.get(sym, 'M15', ''); h = bars.get(sym, 'H1', uid) or bars.get(sym, 'H1', '')
    if not sym or not m or not h: return _v('no_data', 'The bot has no candles for this market, so it cannot check the chart. Only the AI read is shown.')
    off = {x for x in (st.get('strategies_off') or '').split(',') if x}
    if st.get('auto_disable') == '1': off |= stats.losers(int(st.fget('auto_disable_min_trades')), uid)
    solo = {x for x in (st.get('strategies_solo') or '').split(',') if x}
    orf = stats.regime_off(uid) if st.get('regime_switch') == '1' else None
    off, solo, mc = prefs.apply(uid, off, solo, int(st.fget('min_confluence'))); off, solo, mc = automode.lock(off, solo, mc)
    if automode.on(): orf = None
    info = {}; s = brain.evaluate(m, h, mc, automode.rr(), off, solo=solo, info=info, off_reg=orf, max_stop=automode.max_stop())
    bias = read.get('bias')
    if not s:
        idea = ('The AI leans %s, but ' % bias) if bias in ('buy', 'sell') else ''
        return _v('no_setup', idea + 'none of the bot\'s strategies see a setup right now, so the bot would not trade. ' + rgm.note_text(info))
    sig = {'side': s['side'], 'strategy': s['strategy'], 'strategy_name': si.label(s['strategy']), 'entry': s['entry'], 'sl': s['sl'], 'tp': s['tp']}
    ok, why = (True, 'ok') if ctx == 'learn' else risk.global_gate(uid=uid)          # learning: no bot is running, so only the market rules are described
    if ok and ctx != 'learn' and risk.crypto_open() and risk.weekend_skip(sym): ok, why = False, 'weekend/Friday-night risk'
    if ok and ctx != 'learn' and risk.weekday_skip(sym): ok, why = False, 'Bitcoin rests on weekdays'
    if ok: ok, why = risk.symbol_gate(sym, s['side'], uid=uid, cool=(ctx != 'learn'))
    if not ok: return _v('blocked', 'The bot sees a %s setup (%s) but this cannot work right now: %s. It does not trade.' % (s['side'], sig['strategy_name'], why), sig)
    if bias == s['side']: return _v('agree', 'The bot agrees: its strategies (%s) also see a %s. Its own stop loss and target are shown.' % (sig['strategy_name'], s['side']), sig)
    if bias in ('buy', 'sell'): return _v('disagree', 'The AI leans %s but the bot\'s strategies see a %s. When they disagree the bot stays out.' % (bias, s['side']), sig)
    return _v('bot_only', 'The AI saw no clear direction, but the bot sees a %s setup (%s).' % (s['side'], sig['strategy_name']), sig)

def handle(uid, ctx, paid, image, now=None):
    """-> (http status, dict). The picture (base64 JPEG) lives only in this function."""
    now = int(now or time.time())
    if not on(): return 403, {'error': 'The screen assistant is switched off for now.'}
    if ctx not in ('trade', 'learn'): return 400, {'error': 'context must be trade or learn.'}
    if ctx == 'trade' and not paid: return 402, {'error': 'The screen assistant needs an active plan. In the learning path it is free in a small amount.'}
    if not isinstance(image, str) or not image: return 400, {'error': 'Send the picture as a base64 JPEG.'}
    if len(image) > MAX_B64: return 413, {'error': 'That picture is too big. Send one under about 600 KB.'}
    try: raw = base64.b64decode(image, validate=True)
    except ValueError: raw = b''
    if raw[:3] != b'\xff\xd8\xff': return 400, {'error': 'The picture must be a JPEG.'}
    gk = 'screen:last:' + uid
    if now - int(st.get(gk) or 0) < GAP: return 429, {'error': 'One read every %d seconds, please wait a moment.' % GAP}
    n = used(uid, ctx)
    if n >= cap(ctx): return 429, {'error': 'You used all %d reads for today. They come back tomorrow.' % cap(ctx)}
    st.put(gk, now)
    read, err = None, ''
    try: read = parse(call_model(image))
    except ModelError as e: err = str(e)
    if err: code, out = 502, {'error': err}
    elif read is None: code, out = 200, {'ok': True, 'read': {'readable': False, 'note': 'I could not read this chart.'}, 'bot': None}
    else: code, out = 200, {'ok': True, 'read': read, 'bot': ask_bot(uid, read, ctx) if read['readable'] else None}
    bot = out.get('bot') or {}
    st.x('INSERT INTO screen_reads(uid,ts,ctx,symbol,bias,verdict,data) VALUES(?,?,?,?,?,?,?)',
         (uid, now, ctx, canon((read or {}).get('symbol')), (read or {}).get('bias') or '', bot.get('code') or ('error' if err else 'unreadable'), json.dumps(read) if read else ''))
    if code == 200:
        out.update(context=ctx, used=n + 1, cap=cap(ctx), note=NOTE)
        if ctx == 'learn' and read and read.get('readable'): out['teach'] = [{'id': i, 'name': si.name(i), 'desc': si.desc(i)} for i in read['strategies']]
    return code, out
