import sys, os
P, T, H = 'backend/binance_trade.py', 'tests/test_bt1.py', 'docs/HANDOFF.md'
if not (os.path.isfile(P) and os.path.isfile(T)): print('STOP: run this from the repo folder'); sys.exit(1)
t = open(P, encoding='utf-8', newline='').read()
if "'/api/v3/klines'" in t: print('already applied'); sys.exit(0)
a = "('POST', '/api/v3/order'), ('GET', '/api/v3/order'))"
b = """def _result(j, base):
    ex = _d(j.get('executedQty')); cq = _d(j.get('cummulativeQuoteQty'))
    fee = sum((_d(x.get('commission')) for x in (j.get('fills') or []) if x.get('commissionAsset') == base), Decimal(0))
    return {'ok': True, 'order_id': j.get('orderId'), 'status': j.get('status'), 'qty': ex, 'net_qty': ex - fee, 'quote': cq,
            'avg': (cq / ex) if ex > 0 else Decimal(0), 'fee_base': fee}"""
if t.count(a) != 1 or t.count(b) != 1: print('STOP: cannot find the anchors exactly once'); sys.exit(1)
t = t.replace(a, "('POST', '/api/v3/order'), ('GET', '/api/v3/order'), ('GET', '/api/v3/klines'))").replace('Only the 6 (method, path) pairs', 'Only the 7 (method, path) pairs')
t = t.replace(b, """def _result(j, base):
    ex = _d(j.get('executedQty')); cq = _d(j.get('cummulativeQuoteQty'))
    fee = sum((_d(x.get('commission')) for x in (j.get('fills') or []) if x.get('commissionAsset') == base), Decimal(0))
    feeq = sum((_d(x.get('commission')) for x in (j.get('fills') or []) if x.get('commissionAsset') == 'USDT'), Decimal(0))
    return {'ok': True, 'order_id': j.get('orderId'), 'status': j.get('status'), 'qty': ex, 'net_qty': ex - fee, 'quote': cq,
            'avg': (cq / ex) if ex > 0 else Decimal(0), 'fee_base': fee, 'fee_quote': feeq}""")
open(P, 'w', encoding='utf-8', newline='').write(t)
u = open(T, encoding='utf-8', newline='').read()
c = "T('only 6 method+path pairs are allowed', len(bt.ALLOWED) == 6"
if u.count(c) == 1: open(T, 'w', encoding='utf-8', newline='').write(u.replace(c, "T('only 7 method+path pairs are allowed', len(bt.ALLOWED) == 7"))
if os.path.isfile(H):
    h = open(H, encoding='utf-8', newline='').read()
    h += ('\n\n## Section 5B-2a (Binance SPOT bot engine, TESTNET ONLY, not started yet) DONE (Nov 22)\n'
          '- New: backend/binance_bot.py, tests/test_bb2.py (37 checks; 11 deliberate breaks each went red: platform choice ignored, bot switch ignored, Real allowed, SELL traded, non-crypto traded, close not claimed, stop loss ignored, half-balance cap removed, unconfirmed buy retried, open trades not followed, held coins not counted). apply_bb2.py: binance_trade.py now also allows GET /api/v3/klines (7 pairs) and reports fee_quote.\n'
          '- Flow like Deriv: read Binance candles (BTC ETH BNB SOL XRP ADA DOGE LTC, BTCUSD maps to BTCUSDT) -> scan -> open pending BUY signals (claimed first, one order id per signal) -> follow open trades. Spot is long-only: SELL signals are skipped; gold/forex are skipped.\n'
          '- Rules: trades only when the person CHOSE Binance (trade_on), bot switch on, key verified, plan active, mode demo (= testnet); Real gives "real not ready". Stake: strong setup = its share of the balance (stake.py, 40% very strong), else the stop loses about risk_pct; never over half the balance. Balance = free USDT + cost of open trades.\n'
          '- The stop loss / take profit are checked by the bot about once a minute (no stop inside a market order), so a fast move can pass them. Open trades are followed even with the bot off or the plan ended. An order or sell that could not be confirmed is never repeated (stays sent / closing with a note).\n'
          '- NOT wired: the app does not start this loop (test asserts it). Next 5B-2b: start the loop in app.py, check TESTNET keys on the Binance card (binance_trade.check_key) with a demo/testnet switch, allow Start bot / Trade on Binance, REASONS text for the new codes (real not ready, no key, no crypto symbols, cannot trade), tile text, a note about the 1-minute stop check. Then 5B-3 (Real).\n')
    open(H, 'w', encoding='utf-8', newline='').write(h)
print('5B-2a applied: klines allowed + fee_quote in binance_trade.py')
