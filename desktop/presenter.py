"""The window's brain. No screen code lives here, so it is fully testable without a display.
The window (gui.py) only has to: read the form, show text, and call pump() a few times a second.
The engine runs in a background thread and only ever puts messages into a queue; this class (on the window's own thread) reads them.
So the window can never freeze waiting for the internet or for MetaTrader 5."""
import queue, threading, time
from . import config

FIELDS = ('server_url', 'key', 'suffix', 'allow_live')

LIVE_WARNING = ('You ticked "Allow real-money accounts".\n\nIf MetaTrader 5 is logged in to a REAL account, this app will place real '
                'trades and you can lose money. Nothing here is proven profitable.\n\nContinue?')

def default_engine(cfg, log):
    """Built only when Start is pressed, so merely opening the window never touches MetaTrader 5."""
    from .broker import MT5Broker
    from .client import Client
    from .engine import Engine
    return Engine(cfg, MT5Broker(), Client(cfg['server_url'], cfg['key']), state_file=config.state_path(), log=log)

# state from the engine -> (headline, colour, what to do about it).  Colours: ok / warn / bad / idle.
STATES = {
    'starting': ('Starting...', 'idle', ''),
    'ok': ('Running', 'ok', ''),
    'no_mt5': ('Cannot reach MetaTrader 5', 'bad', 'Open MetaTrader 5 on this PC and log in to your account. This app reconnects by itself.'),
    'bad_key': ('The server refused your key', 'bad', 'In the app, open the Connect tab, make a new key, paste it here and press Start again.'),
    'offline': ('Cannot reach the server', 'warn', 'Check this PC\'s internet. A sleeping free server needs about a minute to wake. This app keeps trying.'),
    'expired': ('Your plan has ended', 'warn', 'Renew your plan in the app. Nothing will be traded until then.'),
    'error': ('Unexpected problem', 'warn', 'The app is retrying. If it keeps happening, copy the log and send it to support.'),
}

def money(x):
    try: return '{:,.2f}'.format(float(x))
    except (TypeError, ValueError): return '-'

def describe(s, cfg=None):
    """Engine status dict -> (one status line, colour, advice). Pure function."""
    head, colour, advice = STATES.get(s.get('state'), ('Working...', 'idle', ''))
    parts = [head]
    if s.get('state') == 'ok' and s.get('msg', '').startswith('Waiting'): parts = ['Running (learning your broker\'s clock, a few seconds)']
    if 'balance' in s:
        parts.append('Balance %s' % money(s['balance']))
        parts.append('Equity %s' % money(s.get('equity')))
        parts.append('DEMO account' if s.get('demo') else 'LIVE account')
        if not s.get('demo') and not (cfg or {}).get('allow_live'):
            colour, advice = 'warn', 'This is a REAL account and "Allow real-money accounts" is off, so no trades will be placed. Stop, tick it (if you mean it) and Start again.'
    if s.get('state') == 'ok':
        parts.append('Bot is %s in the app' % ('ON' if s.get('bot') else 'OFF'))
        if s.get('bot') is not True and not advice: advice = 'The bot is switched off in the app (Connect tab). Nothing will be traded until you switch it on there.'
    if s.get('state') == 'ok' or 'balance' in s: parts.append('Open trades: %s' % s.get('open', 0))
    detail = s.get('msg') if s.get('state') in ('no_mt5', 'offline', 'error') and s.get('msg') else ''
    return ' | '.join(parts), colour, (advice + ('  [%s]' % detail if detail else '')).strip()


class Presenter:
    def __init__(self, ui, cfg_path=None, engine_factory=default_engine):
        self.ui, self.cfg_path, self.factory = ui, cfg_path, engine_factory
        self.q = queue.Queue(); self.stop_ev = None; self.thread = None; self.running = False; self.stopping = False; self.cfg = None

    # ---------- start-up ----------
    def load(self):
        c = config.load(self.cfg_path)
        self.ui.set_form({'server_url': c['server_url'], 'key': c['key'], 'suffix': c['suffix'], 'allow_live': c['allow_live']})
        self._idle('Stopped. Fill in the boxes and press Start.', 'idle')
        self.ui.set_button('Start', True); self.ui.set_fields_enabled(True)

    def _say(self, m): self.ui.append_log('%s  %s' % (time.strftime('%H:%M:%S'), m))
    def _idle(self, text, colour, advice=''): self.ui.set_status(text, colour); self.ui.set_advice(advice)

    def _read_cfg(self):
        f = self.ui.get_form()
        raw = dict(config.load_json(self.cfg_path or config.path()))          # keep settings the window does not show
        raw.update(server_url=f.get('server_url', ''), key=f.get('key', ''), suffix=f.get('suffix', ''), allow_live=f.get('allow_live') is True)
        return config.clean(raw)

    # ---------- buttons ----------
    def toggle(self):
        if self.running: self.stop()
        else: self.start()

    def start(self):
        if self.running: return
        try:
            cfg = self._read_cfg(); bad = config.problems(cfg)
            if bad: self._idle('Not started: fix this first', 'bad', '\n'.join(bad)); return
            if cfg['allow_live'] and not self.ui.confirm(LIVE_WARNING):
                self._idle('Not started.', 'idle', 'Untick "Allow real-money accounts" to stay demo-only.'); return
            try: config.save(cfg, self.cfg_path)
            except OSError as e: self._say('Could not save your settings (%s). Running anyway.' % e)
            self.cfg = cfg; self.stop_ev = threading.Event(); stop = self.stop_ev
            engine = self.factory(cfg, lambda line: self.q.put(('log', line)))
        except Exception as e:                                               # a bug here must never close the window
            self._idle('Could not start', 'bad', 'Unexpected problem: %s: %s' % (e.__class__.__name__, e)); return
        self.running, self.stopping = True, False
        self.ui.set_fields_enabled(False); self.ui.set_button('Stop', True)
        self._idle('Starting...', 'idle')
        self._say('Started. Real-money accounts: %s.' % ('ALLOWED' if cfg['allow_live'] else 'blocked (demo only)'))
        self.thread = threading.Thread(target=self._work, args=(engine, stop), daemon=True, name='sxb-engine'); self.thread.start()

    def stop(self):
        if not self.running or self.stopping: return
        self.stopping = True; self.stop_ev.set()
        self.ui.set_button('Stopping...', False); self._idle('Stopping...', 'idle', 'Finishing the current step. This can take a few seconds.')

    def _work(self, engine, stop):
        """Runs in the background thread. Touches NOTHING on screen: only the queue."""
        try: engine.run(stop, lambda s: self.q.put(('status', s)))
        except BaseException as e: self.q.put(('crash', '%s: %s' % (e.__class__.__name__, e)))
        finally: self.q.put(('stopped', None))

    # ---------- called by the window a few times a second ----------
    def pump(self):
        last_status, ended, crash = None, False, None
        try:
            while True:
                kind, v = self.q.get_nowait()
                if kind == 'log': self.ui.append_log(v)
                elif kind == 'status': last_status = v
                elif kind == 'crash': crash = v
                elif kind == 'stopped': ended = True
        except queue.Empty: pass
        if last_status is not None and self.running and not ended:
            line, colour, advice = describe(last_status, self.cfg); self.ui.set_status(line, colour); self.ui.set_advice(advice)
        if crash: self._say('The engine stopped by itself: %s' % crash)
        if self.running and not ended and self.thread is not None and not self.thread.is_alive() and self.q.empty(): ended = True   # thread vanished
        if ended:
            self.running = self.stopping = False
            self.ui.set_fields_enabled(True); self.ui.set_button('Start', True)
            self._say('Stopped.')
            if crash: self._idle('Stopped by an unexpected problem', 'bad', 'Press Start to try again. If it repeats, copy the log and send it to support.')
            else: self._idle('Stopped. Fill in the boxes and press Start.', 'idle')

    def close(self, wait=3.0):
        """Window is closing. Ask the engine to stop and give it a moment (the thread is a daemon, so we never hang)."""
        if self.running and self.stop_ev is not None:
            self.stop_ev.set()
            if self.thread is not None: self.thread.join(wait)
