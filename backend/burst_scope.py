"""Section BT9: which burst settings the burst card shows and saves.
Found: for the OWNER the app files burst settings under scope '' (the owner's PC EA calls the server with no uid), but the owner's Deriv (and Binance)
bot scans under the owner's own uid. So 'Burst switch: on' was saved where the Deriv scan never looks, and the card judged the bot by the EA switch
('The bot is stopped') while Deriv was running.
Now: owner + Deriv or Binance chosen on 'Trade on' -> the card uses the owner's own uid. Anyone else, and the owner on MT5 or with nothing chosen, is unchanged.
The first time, the settings already saved under '' are copied once to the uid (never over settings that are already there)."""
from . import store as st, tradeon

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
    if tradeon.get(uid) in OWN_UID:
        adopt('', uid); return uid
    return ''
