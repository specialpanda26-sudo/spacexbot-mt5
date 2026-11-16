"""Check Resend from your own machine or Render shell. Run:  python3 tools/check_resend.py you@example.com
Needs RESEND_API_KEY and MAIL_FROM in the environment. Sends one test email; ignores the daily cap."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend import mailer

if len(sys.argv) != 2 or '@' not in sys.argv[1]: print('Usage: python3 tools/check_resend.py you@example.com'); sys.exit(2)
print('RESEND_API_KEY:', 'set' if os.getenv('RESEND_API_KEY') else 'MISSING')
print('MAIL_FROM     :', os.getenv('MAIL_FROM') or 'MISSING')
h, t = mailer._page('spaceXBot email check', [('Status', 'Resend is working')], 'This is a test from tools/check_resend.py.')
ok, info = mailer.send(sys.argv[1], 'spaceXBot email check', h, t, kind='test')
print('SENT. Email id:' if ok else 'FAILED:', info); sys.exit(0 if ok else 1)
