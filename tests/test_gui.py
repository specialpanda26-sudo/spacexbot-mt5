"""Desktop window logic (desktop/presenter.py) with a fake screen, fake engines, and the real Engine against a broken MT5.
Also a smoke run of desktop/gui.py against a stand-in for tkinter (the real tkinter is not needed, and is not tested here).
Run:  python tests/test_gui.py   (exit code 1 on any failure)"""
import os, sys, json, time, types, tempfile, threading
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, ROOT)
HOME = tempfile.mkdtemp(prefix='sxbgui_'); os.environ['SXB_HOME'] = HOME
from desktop import config
from desktop.presenter import Presenter, describe, money, STATES
from desktop.client import ServerError
from desktop.broker import BrokerError
from desktop.engine import Engine

R = []
def T(name):
    def deco(f):
        try: f(); R.append((name, True, ''))
        except Exception as e: R.append((name, False, repr(e)[:200]))
        return f
    return deco

class FakeUI:
    def __init__(self, **form):
        self.form = dict(server_url='', key='', suffix='', allow_live=False); self.form.update(form)
        self.status = ('', ''); self.advice = ''; self.button = ('', True); self.enabled = True; self.logs = []; self.asked = []; self.answer = True
    def get_form(self): return dict(self.form)
    def set_form(self, d): self.form.update(d)
    def set_status(self, t, c): self.status = (t, c)
    def set_advice(self, t): self.advice = t
    def set_button(self, t, e): self.button = (t, e)
    def set_fields_enabled(self, on): self.enabled = on
    def confirm(self, t): self.asked.append(t); return self.answer
    def append_log(self, l): self.logs.append(l)
    def everything(self): return ' '.join([self.status[0], self.advice] + self.logs)

class FakeEngine:
    """Looks like Engine to the presenter: run(stop, on_status). mode: 'ok' | 'crash' | 'quick'."""
    def __init__(self, cfg, log, mode='ok'): self.cfg, self.log, self.mode = cfg, log, mode
    def run(self, stop, on_status):
        self.log('12:00:00  engine hello')
        if self.mode == 'crash': raise RuntimeError('boom')
        on_status({'state': 'starting', 'msg': 'x'})
        on_status({'state': 'ok', 'msg': 'Running. Bot is ON in the app.', 'bot': True, 'open': 2, 'balance': 1234.5, 'equity': 1240.0, 'demo': True})
        if self.mode != 'quick': stop.wait(10)

def make(mode='ok', **form):
    ui = FakeUI(**form); built = []
    def factory(cfg, log): e = FakeEngine(cfg, log, mode); built.append(e); return e
    p = Presenter(ui, engine_factory=factory); p.load(); ui.set_form(dict(dict(server_url='', key='', suffix='', allow_live=False), **form)); return ui, p, built       # load() fills the form from the saved file; then the 'person' types

def settle(p, secs=3):
    """Wait for the engine thread to finish, then let the presenter read its messages."""
    if p.thread: p.thread.join(secs)
    p.pump()

def wait_for(fn, secs=3):
    end = time.time() + secs
    while time.time() < end:
        if fn(): return True
        time.sleep(0.02)
    return False

GOOD = dict(server_url='https://x.onrender.com', key='sxb_secretkey123')

@T('describe: every engine state has a headline, colour and advice rules')
def _():
    for st_ in ('starting', 'ok', 'no_mt5', 'bad_key', 'offline', 'expired', 'error'):
        line, colour, adv = describe({'state': st_, 'msg': 'm'}); assert line and colour in ('ok', 'warn', 'bad', 'idle'), st_
    assert describe({'state': 'bad_key', 'msg': ''})[1] == 'bad' and 'new key' in describe({'state': 'bad_key', 'msg': ''})[2]
    assert describe({'state': 'nonsense'})[1] == 'idle'

@T('describe: ok line shows balance, equity, demo, bot on, open trades')
def _():
    line, colour, adv = describe({'state': 'ok', 'msg': 'Running.', 'bot': True, 'open': 3, 'balance': 1234.5, 'equity': 1240, 'demo': True})
    assert colour == 'ok' and 'Balance 1,234.50' in line and 'Equity 1,240.00' in line and 'DEMO' in line and 'Bot is ON' in line and 'Open trades: 3' in line and not adv

@T('describe: bot OFF in the app is explained')
def _():
    line, colour, adv = describe({'state': 'ok', 'msg': 'Running.', 'bot': False, 'open': 0, 'balance': 1, 'equity': 1, 'demo': True})
    assert 'Bot is OFF' in line and 'switched off in the app' in adv

@T('describe: LIVE account with allow-live off turns amber and says no trades')
def _():
    s = {'state': 'ok', 'msg': 'Running.', 'bot': True, 'open': 0, 'balance': 500, 'equity': 500, 'demo': False}
    line, colour, adv = describe(s, {'allow_live': False}); assert 'LIVE' in line and colour == 'warn' and 'no trades' in adv
    assert describe(s, {'allow_live': True})[1] == 'ok'

@T('describe: odd numbers never crash')
def _():
    assert money(None) == '-' and money('x') == '-' and money(5) == '5.00'
    describe({'state': 'ok', 'balance': None, 'equity': 'abc', 'open': None}); describe({})

@T('describe: clock-learning message is explained; error detail is kept')
def _():
    assert 'clock' in describe({'state': 'ok', 'msg': 'Waiting for the clock (a few seconds)...'})[0]
    assert 'ConnectionError' in describe({'state': 'offline', 'msg': 'cannot reach the server (ConnectionError)'})[2]

@T('load: form is filled from the saved settings; button says Start; nothing running')
def _():
    config.save({'server_url': 'https://a.onrender.com', 'key': 'sxb_k', 'suffix': 'm', 'allow_live': False})
    ui = FakeUI(); p = Presenter(ui, engine_factory=lambda c, l: None); built = []; p.load(); assert ui.form['server_url'] == 'https://a.onrender.com' and ui.form['key'] == 'sxb_k' and ui.form['suffix'] == 'm'
    assert ui.button == ('Start', True) and ui.enabled and not p.running and not built
    os.remove(config.path())

@T('start with empty boxes: refused in plain words, no thread, window fine')
def _():
    ui, p, built = make(); p.start()
    assert not p.running and not built and p.thread is None and ui.status[1] == 'bad' and 'https://' in ui.advice and 'key' in ui.advice and ui.button == ('Start', True) and ui.enabled

@T('start with a bad address (http://, no key) is refused')
def _():
    ui, p, built = make(server_url='http://evil.example', key=''); p.start(); assert not p.running and 'https://' in ui.advice

@T('start: settings saved, fields locked, button Stop, engine got the settings')
def _():
    ui, p, built = make(suffix=' m ', **GOOD); p.start()
    assert p.running and ui.button == ('Stop', True) and not ui.enabled and len(built) == 1
    c = built[0].cfg; assert c['key'] == 'sxb_secretkey123' and c['suffix'] == 'm' and c['allow_live'] is False
    assert config.load()['server_url'] == 'https://x.onrender.com'
    p.stop(); settle(p); assert not p.running

@T('engine messages reach the screen; only the newest status is shown')
def _():
    ui, p, built = make(**GOOD); p.start(); assert wait_for(lambda: not p.q.empty())
    time.sleep(0.1); p.pump()
    assert any('engine hello' in l for l in ui.logs); assert ui.status[1] == 'ok' and 'Balance 1,234.50' in ui.status[0] and 'Open trades: 2' in ui.status[0]
    p.stop(); settle(p)

@T('stop: button shows Stopping and is disabled, then returns to Start and unlocks the boxes')
def _():
    ui, p, built = make(**GOOD); p.start(); time.sleep(0.1); p.pump(); p.stop()
    assert ui.button == ('Stopping...', False) and ui.status[0] == 'Stopping...'
    settle(p); assert ui.button == ('Start', True) and ui.enabled and not p.running and ui.status[1] == 'idle'

@T('stop pressed twice, start pressed twice: only one thread, no error')
def _():
    ui, p, built = make(**GOOD); p.start(); t = p.thread; p.start(); assert p.thread is t and len(built) == 1
    p.stop(); p.stop(); settle(p); assert not p.running
    p.start(); assert p.running and len(built) == 2; p.stop(); settle(p)

@T('toggle button starts then stops')
def _():
    ui, p, built = make(**GOOD); p.toggle(); assert p.running; p.toggle(); assert ui.button[0] == 'Stopping...'; settle(p); assert not p.running

@T('engine that crashes: told in plain words, window alive, can press Start again')
def _():
    ui, p, built = make(mode='crash', **GOOD); p.start(); settle(p)
    assert not p.running and ui.button == ('Start', True) and ui.enabled and ui.status[1] == 'bad' and any('boom' in l for l in ui.logs)

@T('engine that ends quickly by itself returns the window to Start')
def _():
    ui, p, built = make(mode='quick', **GOOD); p.start(); settle(p); assert not p.running and ui.button == ('Start', True)

@T('engine factory that blows up: "Could not start", nothing running, boxes stay editable')
def _():
    ui = FakeUI(**GOOD)
    def bad(cfg, log): raise ImportError('no MetaTrader5')
    p = Presenter(ui, engine_factory=bad); p.load(); p.start()
    assert not p.running and ui.status[0] == 'Could not start' and 'ImportError' in ui.advice and ui.button == ('Start', True) and ui.enabled

@T('allow-live: warning shown; refusing it means nothing starts')
def _():
    ui, p, built = make(allow_live=True, **GOOD); ui.answer = False; p.start()
    assert len(ui.asked) == 1 and 'REAL' in ui.asked[0] and not p.running and not built

@T('allow-live: accepting it starts with allow_live on; ticking nothing never asks')
def _():
    ui, p, built = make(allow_live=True, **GOOD); p.start(); assert p.running and built[0].cfg['allow_live'] is True and len(ui.asked) == 1; p.stop(); settle(p)
    ui, p, built = make(**GOOD); p.start(); assert not ui.asked and built[0].cfg['allow_live'] is False; p.stop(); settle(p)

@T('allow_live must be exactly True (a string "yes" from a form does not count)')
def _():
    ui, p, built = make(allow_live='yes', **GOOD); p.start(); assert built[0].cfg['allow_live'] is False; p.stop(); settle(p)

@T('settings the window does not show are kept when it saves')
def _():
    config.save({'server_url': 'https://a.onrender.com', 'key': 'sxb_k', 'poll_seconds': 9, 'max_lots': 0.5})
    ui, p, built = make(**GOOD); p.start(); p.stop(); settle(p); c = config.load(); assert c['poll_seconds'] == 9 and c['max_lots'] == 0.5 and c['key'] == 'sxb_secretkey123'

@T('the personal key never appears in the status, advice or log text')
def _():
    ui, p, built = make(**GOOD); p.start(); time.sleep(0.1); p.pump(); p.stop(); settle(p)
    assert 'sxb_secretkey123' not in ui.everything()

@T('settings file cannot be written: window says so and still runs')
def _():
    ui, p, built = make(**GOOD); orig = config.save
    def broken(c, path=None): raise OSError('disk full')
    config.save = broken
    try: p.start()
    finally: config.save = orig
    assert p.running and any('disk full' in l for l in ui.logs); p.stop(); settle(p)

@T('closing the window while running stops the engine and does not hang')
def _():
    ui, p, built = make(**GOOD); p.start(); t = p.thread; t0 = time.time(); p.close(3); assert not t.is_alive() and time.time() - t0 < 2.5
    p2 = Presenter(FakeUI(), engine_factory=lambda c, l: None); p2.close()          # never started: fine

@T('thread that disappears without a message is noticed')
def _():
    ui, p, built = make(**GOOD); p.start(); p.stop_ev.set(); p.thread.join(3)
    while not p.q.empty(): p.q.get_nowait()                    # lose its goodbye message
    p.pump(); assert not p.running and ui.button == ('Start', True)

@T('REAL Engine with MT5 closed: plain "cannot reach MetaTrader 5" shows, Stop is quick')
def _():
    class NoMT5:
        def account(self): raise BrokerError('Cannot reach MetaTrader 5 (no IPC). Open it and log in first.')
    class NoNet:
        def sync(self, *a, **k): raise ServerError('x')
        def report(self, *a, **k): raise ServerError('x')
    def factory(cfg, log): return Engine(cfg, NoMT5(), NoNet(), state_file=os.path.join(HOME, 'st.json'), log=log)
    ui = FakeUI(**GOOD); p = Presenter(ui, engine_factory=factory); p.load(); p.start()
    assert wait_for(lambda: (p.pump() or True) and ui.status[0].startswith('Cannot reach MetaTrader 5'))
    assert ui.status[1] == 'bad' and 'log in' in ui.advice
    t0 = time.time(); p.stop(); assert wait_for(lambda: (p.pump() or True) and not p.running) and time.time() - t0 < 2

@T('gui.py against a stand-in for tkinter: builds, shows status, locks fields, runs the loop, closes')
def _():
    from unittest import mock
    try: os.remove(config.path())                                   # earlier tests saved settings
    except OSError: pass
    class Var:
        def __init__(self, value=None): self.v = value
        def get(self): return self.v
        def set(self, x): self.v = x
    tk = types.ModuleType('tkinter'); W = lambda *a, **k: mock.MagicMock(); tk.Tk = W; tk.StringVar = lambda value='': Var(value); tk.BooleanVar = lambda value=False: Var(value)
    tk.Label = tk.Text = tk.Checkbutton = W; ttk = mock.MagicMock(); mb = mock.MagicMock(); mb.askyesno.return_value = True
    tk.ttk, tk.messagebox = ttk, mb
    with mock.patch.dict(sys.modules, {'tkinter': tk, 'tkinter.ttk': ttk, 'tkinter.messagebox': mb}):
        from desktop import gui
        w = gui.Window(); assert w.get_form() == {'server_url': '', 'key': '', 'suffix': '', 'allow_live': False}
        w.set_form({'server_url': 'https://q.onrender.com', 'key': 'sxb_z'}); assert w.get_form()['key'] == 'sxb_z'
        w.set_status('hello', 'ok'); w.set_status('hello', 'unknown-colour'); w.set_advice('a'); w.set_button('Stop', False); w.set_fields_enabled(False); w.append_log('line')
        assert w.confirm('?') is True
        w._loop(); w._toggle_key(); w._on_error(ValueError, ValueError('x'), None)
        w._close()
    assert os.path.exists(os.path.join(HOME, 'crash.log'))

@T('gui.py can be imported with no tkinter installed (nothing at import time needs a screen)')
def _():
    from desktop import gui; assert callable(gui.main)

w = max(len(n) for n, _, _ in R)
for n, ok, err in R: print(('PASS ' if ok else 'FAIL ') + n.ljust(w), '' if ok else ' <- ' + err)
bad = [n for n, ok, _ in R if not ok]; print(f'\n{len(R) - len(bad)}/{len(R)} passed'); sys.exit(1 if bad else 0)
