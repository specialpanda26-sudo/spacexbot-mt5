from . import risk


def base(sym):
    s = str(sym or "").strip().upper()
    for c in risk.CRYPTO:
        if s.startswith(c): return c
    return s


def name(sym):
    s = base(sym)
    return ("cry" if risk.is_crypto(s) else "frx") + s
