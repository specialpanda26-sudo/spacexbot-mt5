"""Stochastic oscillator (helper for video 3 section 3B; kept out of indicators.py on purpose)."""
def stoch(b, k=14, d=3):
    """(%K list, %D list), both 0..100. %K = where the close sits inside the last k candles' high-low range; %D = average of the last d %K. A flat range gives 50."""
    K = []
    for i in range(len(b)):
        w = b[max(0, i - k + 1): i + 1]; hi = max(x['h'] for x in w); lo = min(x['l'] for x in w)
        K.append(50.0 if hi == lo else 100.0 * (b[i]['c'] - lo) / (hi - lo))
    D = [sum(K[max(0, i - d + 1): i + 1]) / len(K[max(0, i - d + 1): i + 1]) for i in range(len(K))]
    return K, D
