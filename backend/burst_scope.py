"""Section BT9: which burst settings the burst card shows and saves.
Found: for the OWNER the app files burst settings under scope '' (the owner's PC EA calls the server with no uid), but the owner's Deriv (and Binance)
bot scans under the owner's own uid. So 'Burst switch: on' was saved where the Deriv scan never looks, and the card judged the bot by the EA switch
('The bot is stopped') while Deriv was running.
Now: owner with the Deriv or Binance bot switched on -> the card uses the owner's own uid. Anyone else, and the owner on MT5 only, is unchanged.
The first time, the settings already saved under '' are copied once to the uid (never over settings that are already there)."""
from . import store as st, brokers as bk

OWN_UID = ('Deriv', 'Binance')


def adopt(src, dst):
    """Copy the burst settings saved under scope `src` to scope `dst`, only when `dst` has none yet."""
    if not dst or dst == src: return False
    if st.get('burst:' + dst): return False
    v = st.get('burst:' + (src or ''))
    if not v: return False
    st.put('burst:' + dst, v); return True


def scope(u):
    """u = the signed-in person {'uid', 'admin'}. -> the scope the burst card reads and writes."""
    uid = u['uid']
    if not u.get('admin'): return uid
    if any(bk.bot_flag(uid, p) for p in OWN_UID):          # the owner's Deriv or Binance bot is switched on, so it scans under the owner's own uid
        adopt('', uid); return uid
    return ''
