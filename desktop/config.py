"""Desktop app settings: one JSON file in the user's home folder (never inside the app folder, never in git)."""
import os, json

DEFAULTS = {'server_url': '', 'key': '', 'symbols': '', 'suffix': '', 'poll_seconds': 5, 'bars_push_seconds': 60, 'allow_live': False,
            'max_spread_points': 60, 'max_lots': 1.0, 'deviation': 20, 'magic': 5150150, 'utc_offset_min': None}

def home(): return os.getenv('SXB_HOME') or os.path.join(os.path.expanduser('~'), '.spacexbot')
def path(): return os.path.join(home(), 'config.json')
def state_path(): return os.path.join(home(), 'state.json')

def _num(v, lo, hi, d, cast=float):
    try: v = cast(v)
    except (TypeError, ValueError): return d
    return max(lo, min(hi, v))

def clean(raw):
    """Any dict in, a complete, type-safe, clamped config out."""
    c = dict(DEFAULTS); c.update({k: v for k, v in (raw or {}).items() if k in DEFAULTS})
    c['server_url'] = str(c['server_url']).strip().rstrip('/'); c['key'] = str(c['key']).strip(); c['suffix'] = str(c['suffix']).strip()
    c['symbols'] = ','.join(s.strip() for s in str(c['symbols']).split(',') if s.strip())
    c['poll_seconds'] = _num(c['poll_seconds'], 2, 60, 5, int); c['bars_push_seconds'] = _num(c['bars_push_seconds'], 30, 600, 60, int)
    c['max_spread_points'] = _num(c['max_spread_points'], 1, 100000, 60, int); c['max_lots'] = _num(c['max_lots'], 0.01, 1000, 1.0)
    c['deviation'] = _num(c['deviation'], 0, 500, 20, int); c['magic'] = _num(c['magic'], 1, 2 ** 31 - 1, 5150150, int)
    c['allow_live'] = c['allow_live'] is True
    u = c['utc_offset_min']; c['utc_offset_min'] = None if u in (None, '') else _num(u, -840, 840, None, int)
    return c

def problems(c):
    """Plain-words list of what must be fixed before the bot can start (empty = fine)."""
    p = []
    if not (c['server_url'].startswith('https://') or c['server_url'].startswith('http://127.0.0.1') or c['server_url'].startswith('http://localhost')):
        p.append('Server address must start with https:// (copy it from your browser).')
    if not c['key']: p.append('Paste your personal key (Connect tab > Make my key).')
    return p

def load_json(p):
    try:
        with open(p, encoding='utf-8') as f: j = json.load(f)
        return j if isinstance(j, dict) else {}
    except (OSError, ValueError): return {}

def save_json(p, d):
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    t = p + '.part'
    with open(t, 'w', encoding='utf-8') as f: json.dump(d, f)
    try: os.chmod(t, 0o600)
    except OSError: pass
    os.replace(t, p)            # never leaves a half-written file if the PC loses power

def load(p=None): return clean(load_json(p or path()))
def save(c, p=None): save_json(p or path(), clean(c))
