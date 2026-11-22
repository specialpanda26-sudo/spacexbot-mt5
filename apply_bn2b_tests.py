"""5B-2b: update 5 old tests to the new truth (Binance trades on the testnet). Idempotent. Run: python apply_bn2b_tests.py"""
import os
R = os.path.dirname(os.path.abspath(__file__))
def sub(path, pairs):
    p = os.path.join(R, path); s = open(p, encoding='utf-8').read()
    for a, b in pairs:
        if b in s: continue
        assert s.count(a) == 1, (path, a[:60], s.count(a)); s = s.replace(a, b)
    open(p, 'w', encoding='utf-8').write(s)
sub('tests/test_binance.py', [
 ("T('the tile data says it does not trade', v['trades'] is False and 'never places a Binance order' in v['note'])", "T('the real-key read-only check still says it never orders (5B-2b: the demo check is binance_bot.verify)', v['trades'] is True and 'never places a Binance order' in v['note'])"),
 ("state['acct'] = (200, {'balances': [{'asset': 'USDT', 'free': '7', 'locked': '0'}]})\nr = c.post('/api/brokers/Binance/verify'", "state['acct'] = (200, {'balances': [{'asset': 'USDT', 'free': '7', 'locked': '0'}]})\nbk.set_mode(U, 'Binance', 'real')          # 5B-2b: demo = testnet key (test_bn2b.py); real keeps this read-only check\nr = c.post('/api/brokers/Binance/verify'"),
 ("T('route: Binance still has no bot and no demo/real switch',", "T('route: Binance bot is refused until it is chosen and checked, and it has no demo/real switch',"),
 ("'no trading' in cat['Binance']['tile'].lower()", "'testnet' in cat['Binance']['tile'].lower()"),
 ("'Withdrawals OFF' in idx and 'never places a Binance order' in idx and 'Create an API key with trading only' not in idx", "'Withdrawals OFF' in idx and 'testnet.binance.vision' in idx and 'never places a Binance order' not in idx and 'Create an API key with trading only' not in idx"),
 ("'Read-only, no trading' in idx", "'Testnet demo' in idx"),
])
sub('tests/test_bb2.py', [("T('the app does not start this bot yet (5B-2b)', 'binance_bot' not in src)", "T('the app starts this bot (5B-2b)', 'binance_bot.start(_scan, _paid)' in src)")])
sub('tests/test_tp5a.py', [
 ("T('Binance chosen: Start says Binance does not trade yet', r.status_code == 400 and 'Binance' in r.get_json()['error'] and not links.bot_on(A))", "T('Binance chosen, no Binance key saved: Start asks for the key and MT5 stays off (5B-2b)', r.status_code == 400 and 'Binance' in r.get_json()['error'] and not links.bot_on(A))"),
 ("'nothing will trade' in j['note']", "'Only Binance trades' in j['note']"),
])
sub('tests/test_c4.py', [("'does not place trades yet' in txt", "'testnet only for now' in txt")])
sub('tests/test_deriv_e2e.py', [("and 'does not trade yet' in e('/api/brokers/Binance/bot', {'on': True}))", "and 'Binance key' in e('/api/brokers/Binance/bot', {'on': True}))")])
print('old tests updated')
