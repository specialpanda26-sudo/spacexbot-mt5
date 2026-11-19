"""R3: the market regime, in one place. Pure (no database), so the backtest tool can use it too.
The limits are the ones the brain already uses to skip setups: ADX above rev_max = strong trend (reversal setups skipped),
ADX below trend_min = quiet (trend setups skipped), in between = moderate (both kinds allowed)."""
STRONG, QUIET, MODERATE = 'strong trend', 'quiet', 'moderate'
LABELS = (STRONG, QUIET, MODERATE)

def _ok(x):
    try: x = float(x)
    except (TypeError, ValueError): return None
    return x if x == x and abs(x) != float('inf') else None

def of(ax, trend_min=18.0, rev_max=28.0):
    """The regime for this ADX. A missing or broken ADX counts as moderate (nothing is skipped on a guess)."""
    x = _ok(ax)
    if x is None: return MODERATE
    return STRONG if x > rev_max else QUIET if x < trend_min else MODERATE

def sentence(rg, ax):
    """One plain sentence about the market, or '' when there is nothing true to say."""
    x = _ok(ax)
    t = {STRONG: 'Market: strong trend (ADX %.0f), so trend strategies lead and reversal setups are skipped.',
         QUIET: 'Market: quiet and ranging (ADX %.0f), so reversal strategies lead and trend setups are skipped.',
         MODERATE: 'Market: moderate (ADX %.0f), so both kinds of strategy are allowed.'}.get(rg)
    return (t % x) if t and x is not None else ''

def note_text(info):
    """The 'no setup' reason from brain.evaluate(info=...) plus one sentence about the market."""
    info = info or {}; t = str(info.get('text') or ''); ax = info.get('adx')
    s = sentence(of(ax), ax) if ax is not None else ''
    return (t + ' ' + s).strip()
