"""The SpaceXBridge MT5 Expert Advisor, served to subscribers from inside the app.
ea/SpaceXBridge.mq5 is the one source of truth: its '#property version' is the version everybody sees.
An MT5 program cannot rewrite and compile itself, so 'update' = the EA reports its version, the app compares it to this file,
and the person re-pastes the new code (about one minute). The EA also warns on its own chart when it is behind."""
import os, re, json, hashlib

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ea')
VER_RE = re.compile(r'^\s*#property\s+version\s+"(\d{1,2}\.\d{1,3})"', re.M)
URL_RE = re.compile(r'(input\s+string\s+ServerUrl\s*=\s*")[^"]*(")')


def source():
    with open(os.path.join(_DIR, 'SpaceXBridge.mq5'), encoding='utf-8') as f: return f.read()


def version(src=None):
    m = VER_RE.search(src if src is not None else source()); return m.group(1) if m else ''


def vkey(v):
    try: return tuple(int(x) for x in str(v).split('.'))
    except ValueError: return ()


def newer(latest, installed):
    """True when `installed` is a real older version than `latest`. Unknown installed version -> False (never guess)."""
    a, b = vkey(latest), vkey(installed)
    return bool(a) and bool(b) and a > b


def changelog(limit=4):
    try:
        with open(os.path.join(_DIR, 'CHANGELOG.json'), encoding='utf-8') as f: rows = json.load(f)
    except (OSError, ValueError): return []
    return [{'v': str(r.get('v')), 'date': str(r.get('date') or ''), 'notes': [str(n) for n in r.get('notes', [])][:8]} for r in rows[:limit] if isinstance(r, dict)]


def code(site=''):
    """The code to paste. Only the ServerUrl default is filled with this server's address; the key is never put in the file."""
    src = source(); site = (site or '').strip().rstrip('/')
    if site.startswith('http') and '"' not in site: src = URL_RE.sub(lambda m: m.group(1) + site + m.group(2), src, count=1)
    return src


def info(site='', installed=None):
    src = code(site); v = version(src)
    return {'version': v, 'sha': hashlib.sha256(src.encode()).hexdigest()[:12], 'lines': src.count('\n') + 1, 'bytes': len(src.encode()),
            'installed': installed or None, 'outdated': newer(v, installed), 'changelog': changelog()}


def steps(site, owner=False):
    """Plain, click-by-click help. Each step: t = what to do, d = how, ok = what you should see, bad = what to do when you do not."""
    key = 'the EA_KEY you set on Render' if owner else 'your personal key (made in the Connect your MT5 card above; it is shown only once)'
    first = [
        {'t': 'Open MetaEditor', 'd': 'MetaEditor is the small code window that comes with MetaTrader 5. In MT5 press F4 on the keyboard. Or click the yellow book icon in the top toolbar.',
         'ok': 'A new window opens with a folder list called Navigator on the left.', 'bad': 'Nothing opens? In MT5 click Tools in the top menu, then MetaQuotes Language Editor.'},
        {'t': 'Make an empty file for the bot', 'd': 'In MetaEditor click File, then New. Pick Expert Advisor (template) and click Next. In Name type SpaceXBridge (one word) and click Next, Next, then Finish.',
         'ok': 'A tab called SpaceXBridge.mq5 opens with some sample code.', 'bad': ''},
        {'t': 'Paste the SpaceX code', 'd': 'In this app tap Copy code. Go to MetaEditor and click inside the sample code. Press Ctrl+A to select everything and Delete to clear it. Then press Ctrl+V to paste. Delete the sample code first, or the file will not compile.',
         'ok': 'The first line starts with //+----- and the file mentions SpaceXBridge.', 'bad': 'Nothing pasted? On a phone or a remote desktop, tap Download file here, then open it in MetaEditor with File, Open.'},
        {'t': 'Compile it', 'd': 'Press F7 (or click the Compile button). Compiling turns the code into the program MT5 can run.',
         'ok': 'At the bottom, the Errors tab says 0 errors. Warnings are fine.', 'bad': 'Errors? Almost always the old sample code is still there. Select everything, delete, paste again, press F7 again.'},
        {'t': 'Allow MT5 to talk to the bot', 'd': 'Back in MT5 click Tools, then Options, then the Expert Advisors tab. Tick Allow WebRequest for listed URL. Double-click the empty row under it and type ' + site + ' (no slash at the end). Click OK.',
         'ok': 'The address is listed under the tick box.', 'bad': 'Skipping this gives error 4014 or 4060 in the Experts tab.'},
        {'t': 'Put the bot on the XAUUSD chart', 'd': 'Open an XAUUSD chart. Press Ctrl+N to open the Navigator, open Expert Advisors, and drag SpaceXBridge onto the chart. On the Common tab tick Allow Algo Trading. On the Inputs tab set ServerUrl to ' + site + ' and EAKey to ' + key + '. Leave AllowLive as false while you practise on a demo account. Click OK.',
         'ok': 'A small name tag SpaceXBridge shows in the top-right corner of the chart.', 'bad': 'Chart says Wrong key? Copy the key again with no spaces before or after it.'},
        {'t': 'Turn Algo Trading on', 'd': 'Click the Algo Trading button in the top toolbar of MT5 so it turns green.',
         'ok': 'The name tag on the chart shows a smiling face.', 'bad': 'A sad face means Algo Trading is still off.'},
        {'t': 'Check that it connects', 'd': 'Press Ctrl+T and open the Experts tab at the bottom of MT5. Then come back to this app.',
         'ok': 'Experts says SpaceXBridge started. Within 2 minutes the Connect card here shows MT5 online and the version you installed.', 'bad': 'Error 4014 or 4060: redo the Allow WebRequest step. HTTP 401 or bad key: the EAKey is wrong. Nothing at all: MT5 must stay open with internet.'},
    ]
    update = [
        {'t': 'Know when to update', 'd': 'This app shows Update available when your EA is older than the newest one. Your EA also writes a message on the chart and one line in the Experts tab. Until you update, the old version keeps working as before.',
         'ok': 'The card above shows your version and the newest version.', 'bad': ''},
        {'t': 'Copy the newest code', 'd': 'Tap Copy code in this app. It always gives the newest version with your server address already filled in.', 'ok': 'The app says the code was copied.', 'bad': ''},
        {'t': 'Open your file in MetaEditor', 'd': 'In MT5 press F4. In the Navigator on the left open Experts and double-click SpaceXBridge.mq5. Click inside the code, press Ctrl+A, then Ctrl+V to replace the old code with the new one.',
         'ok': 'The #property version line near the top shows the new number.', 'bad': ''},
        {'t': 'Compile again', 'd': 'Press F7. MT5 restarts the bot on your chart by itself and keeps the settings you had.',
         'ok': 'Errors tab says 0 errors, and the Experts tab says SpaceXBridge started.', 'bad': 'If the name tag disappears from the chart, drag SpaceXBridge on again and re-enter ServerUrl and EAKey.'},
        {'t': 'Confirm in the app', 'd': 'Wait up to 2 minutes and open the Connect tab.',
         'ok': 'The chip says Up to date and your version matches the newest one.', 'bad': 'Still Update available? The compile did not finish. Press F7 again and read the Errors tab.'},
    ]
    return {'first': first, 'update': update}
