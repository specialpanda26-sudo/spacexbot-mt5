p = 'backend/payments.py'
s = open(p).read()
if '_rl = threading.Lock()' in s:
    a = s.index('_rl = threading.Lock()')
    b = s.index('def note(ref, text):')
    s = s[:a] + s[b:]
    old = """    if not (bump('aid:' + uid, int(_env('STK_DAILY_PER_ACCOUNT', d='30'))) and bump('phone:' + ph, int(_env('STK_DAILY_PER_PHONE', d='10')))):
        raise PermissionError('Too many payment attempts today. Try again tomorrow.')
"""
    assert old in s, 'limiter call not found'
    s = s.replace(old, '')
    open(p, 'w').write(s)
p = '.env.example'
s = open(p).read()
s = s.replace('STK_DAILY_PER_ACCOUNT=30\n', '').replace('STK_DAILY_PER_PHONE=10\n', '')
open(p, 'w').write(s)
p = 'README.md'
s = open(p).read()
s = s.replace(', STK prompts are rate-limited per account and phone', '; STK prompts are not rate-limited')
open(p, 'w').write(s)
print('done')
