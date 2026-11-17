"""Talks to your Render server with exactly the two calls the MT5 EA makes: /api/ea/sync and /api/ea/report."""
import requests

class AuthError(Exception): pass        # the server refused the key
class ServerError(Exception): pass      # unreachable, asleep, or an error answer: try again later

class Client:
    def __init__(self, url, key, session=None, timeout=60):    # 60 s: a sleeping free Render service needs about a minute to wake
        self.url, self.key, self.s, self.timeout = url.rstrip('/'), key, session or requests.Session(), timeout

    def _post(self, path, body):
        try: r = self.s.post(self.url + path, json=body, headers={'X-EA-Key': self.key}, timeout=self.timeout)
        except Exception as e: raise ServerError('cannot reach the server (%s)' % e.__class__.__name__)
        if r.status_code == 401: raise AuthError('the server refused the key')
        if r.status_code >= 400: raise ServerError('server answered %s' % r.status_code)
        try: j = r.json()
        except ValueError: j = None
        if not isinstance(j, dict): raise ServerError('unreadable answer from the server')
        return j

    def sync(self, account, bars=None):
        body = {'account': account}
        if bars: body['bars'] = bars
        return self._post('/api/ea/sync', body)

    def report(self, sid, status, **extra): return self._post('/api/ea/report', dict(extra, id=sid, status=status))
