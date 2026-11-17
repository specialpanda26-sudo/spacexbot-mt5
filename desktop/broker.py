"""The MT5 side. Engine only calls these methods, so tests swap in a fake. MT5Broker uses the official `MetaTrader5` Python package
(Windows only; MetaTrader 5 must be open and logged in). Times from MT5 are broker-server time; the engine converts to UTC."""

class BrokerError(Exception): pass     # MT5 closed, logged out, or not answering

class MT5Broker:
    def __init__(self, path=None): self.path, self.m = path, None

    def connect(self):
        try: import MetaTrader5 as m
        except ImportError: raise BrokerError('The MetaTrader5 package is missing (it only exists for Windows).')
        if not (m.initialize(path=self.path) if self.path else m.initialize()):
            raise BrokerError('Cannot reach MetaTrader 5 (%s). Open it and log in first.' % (m.last_error(),))
        self.m = m

    def _mt(self):
        if self.m is None: self.connect()
        return self.m

    def account(self):
        m = self._mt(); t, a = m.terminal_info(), m.account_info()
        if t is None or a is None: self.m = None; raise BrokerError('MetaTrader 5 is not answering. Is it open and logged in?')
        if not t.connected: raise BrokerError('MetaTrader 5 has no connection to the broker.')
        return {'balance': float(a.balance), 'equity': float(a.equity), 'login': int(a.login), 'demo': a.trade_mode == m.ACCOUNT_TRADE_MODE_DEMO,
                'trade_allowed': bool(t.trade_allowed and a.trade_allowed)}      # trade_allowed = the "Algo Trading" button is on

    def resolve(self, canon, suffix=''):
        """Broker's name for XAUUSD: your suffix if it exists, else the shortest symbol that starts with the name (XAUUSDm, XAUUSD.r ...)."""
        m = self._mt(); want = canon + suffix
        if m.symbol_info(want) is None:
            names = sorted((s.name for s in (m.symbols_get(group='*' + canon + '*') or ()) if s.name.upper().startswith(canon.upper())), key=len)
            if not names: return None
            want = names[0]
        return want if m.symbol_select(want, True) else None

    def symbol(self, name):
        m = self._mt(); i, k = m.symbol_info(name), m.symbol_info_tick(name)
        if i is None or k is None: return None
        fill = m.ORDER_FILLING_IOC if i.filling_mode & 2 else m.ORDER_FILLING_FOK if i.filling_mode & 1 else m.ORDER_FILLING_RETURN
        return {'point': i.point, 'digits': i.digits, 'ask': k.ask, 'bid': k.bid, 'stops_level': i.trade_stops_level, 'tick_value': i.trade_tick_value,
                'tick_size': i.trade_tick_size, 'vol_min': i.volume_min, 'vol_max': i.volume_max, 'vol_step': i.volume_step, 'fill': fill,
                'tradable': i.trade_mode == m.SYMBOL_TRADE_MODE_FULL}

    def rates(self, sym, tf, count):
        """CLOSED candles only (start 1 skips the forming one), oldest first: [time, o, h, l, c, tick_volume]. Time is broker-server time."""
        m = self._mt(); r = m.copy_rates_from_pos(sym, {'M15': m.TIMEFRAME_M15, 'H1': m.TIMEFRAME_H1}[tf], 1, count)
        return [] if r is None else [[int(x['time']), float(x['open']), float(x['high']), float(x['low']), float(x['close']), int(x['tick_volume'])] for x in r]

    def freshest_tick(self, syms):
        m = self._mt(); best = None
        for s in syms:
            k = m.symbol_info_tick(s)
            if k is not None and k.time and (best is None or k.time > best): best = int(k.time)
        return best

    def positions(self, magic):
        m = self._mt(); r = m.positions_get()
        if r is None: raise BrokerError('could not read open positions (%s)' % (m.last_error(),))     # None = error; () = genuinely none
        return [{'pid': p.identifier, 'ticket': p.ticket, 'comment': p.comment, 'symbol': p.symbol} for p in r if p.magic == magic]

    def close_info(self, pid):
        """P/L (profit + swap + commission + fee, same as the EA) and why it closed, or None while MT5's history has not caught up."""
        m = self._mt(); d = m.history_deals_get(position=pid)
        outs = [x for x in (d or ()) if x.entry in (m.DEAL_ENTRY_OUT, m.DEAL_ENTRY_OUT_BY, m.DEAL_ENTRY_INOUT)]
        if not outs: return None
        r = outs[-1].reason
        return {'pnl': round(sum(x.profit + x.swap + x.commission + getattr(x, 'fee', 0.0) for x in d), 2),
                'reason': 'tp' if r == m.DEAL_REASON_TP else 'sl' if r == m.DEAL_REASON_SL else 'other'}

    def send_market(self, sym, side, lots, sl, tp, comment, deviation, magic, fill):
        m = self._mt(); k = m.symbol_info_tick(sym); buy = side == 'buy'
        r = m.order_send({'action': m.TRADE_ACTION_DEAL, 'symbol': sym, 'volume': lots, 'type': m.ORDER_TYPE_BUY if buy else m.ORDER_TYPE_SELL,
                          'price': k.ask if buy else k.bid, 'sl': sl, 'tp': tp, 'deviation': deviation, 'magic': magic, 'comment': comment,
                          'type_time': m.ORDER_TIME_GTC, 'type_filling': fill})
        if r is None: return {'ok': False, 'retcode': -1, 'ticket': 0, 'price': 0, 'comment': str(m.last_error())}
        return {'ok': r.retcode in (m.TRADE_RETCODE_DONE, m.TRADE_RETCODE_PLACED), 'retcode': r.retcode, 'ticket': r.order, 'price': r.price, 'comment': r.comment}
