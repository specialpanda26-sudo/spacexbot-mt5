"""Run from a terminal:   python -m desktop.main        (first run asks for your server address and key; --setup asks again)."""
import sys, threading
from . import config
from .broker import MT5Broker
from .client import Client
from .engine import Engine

def setup(cfg):
    print('spaceXBot desktop setup. Press Enter to keep the value in [brackets].')
    for k, label in (('server_url', 'Server address (https://....onrender.com)'), ('key', 'Your personal key (sxb_...)'), ('suffix', 'Symbol suffix at your broker (usually empty)')):
        v = input('%s [%s]: ' % (label, cfg[k] if k != 'key' else ('set' if cfg[k] else ''))).strip()
        if v: cfg[k] = v
    cfg['allow_live'] = input('Allow REAL-money accounts? Type YES to allow, Enter to stay demo-only: ').strip() == 'YES'
    cfg = config.clean(cfg); config.save(cfg); return cfg

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv; cfg = config.load()
    if '--setup' in argv or config.problems(cfg): cfg = setup(cfg)
    for p in config.problems(cfg): print(p); return 1
    eng = Engine(cfg, MT5Broker(), Client(cfg['server_url'], cfg['key']), state_file=config.state_path()); stop = threading.Event(); last = [None]
    def show(s):
        if (s['state'], s['msg']) != last[0]: last[0] = (s['state'], s['msg']); print('[%s] %s' % (s['state'], s['msg']))
    print('Running. Press Ctrl+C to stop. MetaTrader 5 must stay open.')
    try: eng.run(stop, show)
    except KeyboardInterrupt: stop.set(); print('Stopped.')
    return 0

if __name__ == '__main__': sys.exit(main())
