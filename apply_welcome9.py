"""Section 9a: welcome email on a person's first sign-in. Edits backend/mailer.py, backend/app.py, tests/test_mail.py, docs/HANDOFF.md. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding="utf-8").read()
    if marker in s: print("skip (already there):", path); return
    if s.count(old) != 1: print("STOP:", path, "anchor found", s.count(old), "times"); sys.exit(1)
    open(path, "w", encoding="utf-8").write(s.replace(old, new)); print("edited:", path)

edit("backend/mailer.py",
"""def receipt(ref):
    if configured(): threading.Thread(target=_receipt_now, args=(ref,), daemon=True).start()""",
"""def receipt(ref):
    if configured(): threading.Thread(target=_receipt_now, args=(ref,), daemon=True).start()

# ---------- welcome (Section 9a) ----------
def _welcome_now(uid):
    u = st.q('SELECT email,name FROM users WHERE uid=?', (uid,), True)
    if not u or not (u['email'] or '').strip(): return False
    first = (u['name'] or '').strip().split(' ')[0]
    rows = [('Step 1', 'Choose a plan'), ('Step 2', 'Connect Deriv or MT5 on the Connect tab'), ('Step 3', 'Start the bot on the Bot tab')]
    h, t = _page('Welcome to spaceXBot' + (', ' + first if first else '') + '!', rows, 'The bot does not trade until you start it. Not financial advice; trading can lose money. Questions? Reply to this email.', img='alert')
    ok, info = send(u['email'], 'Welcome to spaceXBot', h, t, idem='welcome/' + uid, kind='receipt')
    if not ok: print('[mail] welcome not sent:', uid, info)
    return ok

def welcome(uid):
    \"\"\"Once, when a verified person signs in for the first time. MAIL_WELCOME=0 turns it off.\"\"\"
    if configured() and os.getenv('MAIL_WELCOME', '1').strip() != '0': threading.Thread(target=_welcome_now, args=(uid,), daemon=True).start()""",
"# ---------- welcome (Section 9a)")

edit("backend/app.py",
"""        st.x('INSERT INTO users(uid,email,name,created,onboarded) VALUES(?,?,?,?,0) ON CONFLICT(uid) DO NOTHING', (u['uid'], u['email'], u['name'], int(time.time())))""",
"""        new = st.x('INSERT INTO users(uid,email,name,created,onboarded) VALUES(?,?,?,?,0) ON CONFLICT(uid) DO NOTHING', (u['uid'], u['email'], u['name'], int(time.time())), count=True)
        if new == 1 and u.get('verified'):      # welcome email: first sign-in only, verified email only (Section 9a)
            try:
                from . import mailer; mailer.welcome(u['uid'])
            except Exception as e: print('welcome failed', e)""",
"Section 9a)")

edit("tests/test_mail.py", "MAIL_ALERT_CAP='3', MAIL_HARD_CAP='5')", "MAIL_ALERT_CAP='3', MAIL_HARD_CAP='5', MAIL_WELCOME='0')", "MAIL_WELCOME")

edit("docs/HANDOFF.md", "\n## STATUS BOARD (Nov 21, newest; read this first)",
"""
## Section 9a (welcome email) DONE (Nov 21)
- apply_welcome9.py edits backend/mailer.py (welcome(uid), _welcome_now), backend/app.py (user()) and tests/test_mail.py (+ tests/test_welcome9.py). Trigger: user() inserts the users row for the first time (INSERT ... count=True == 1) AND the email is verified. Existing people get nothing; an unverified first sign-in gets no welcome and never will (no second trigger, on purpose: no email to unverified addresses).
- Email: heading 'Welcome to spaceXBot, <first name>!', three steps (Choose a plan / Connect Deriv or MT5 on the Connect tab / Start the bot on the Bot tab), picture = the existing alert rocket (img='alert', so still 5 email pictures). Sent as kind 'receipt' (hard cap, never blocked by the alert cap), idempotency key welcome/<uid>. Does nothing when Resend is not set up. MAIL_WELCOME=0 turns it off (tests/test_mail.py sets it so its counts stay exact).
- NOT built (no server trigger exists): plan-ending email (needs the parked N3 loop), update-available email, bot started/stopped email. NOT tested: a real Resend send.
- Next: 9b only if a trigger is chosen; otherwise Section 10 (final check).

## STATUS BOARD (Nov 21, newest; read this first)""", "Section 9a (welcome email)")
