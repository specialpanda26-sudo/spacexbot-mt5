"""Checks Section 8d: lock, moon, shield and plug cartoons have moving parts, the plug cartoon replaces the still symbol,
the closing-band picture is back in its corner, and all motion is allowed only for people who did not ask for less.
The picture code is run in node (no temp files) and every picture is parsed as XML. Run: python tests/test_pic8d.py"""
import os, re, sys, json, shutil, subprocess
import xml.etree.ElementTree as ET
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def cut(a, b):
    i = S.find(a); j = S.find(b, i + 1) if i > -1 else -1
    return S[i:j + len(b)] if i > -1 and j > -1 else ''
css = cut('/*P8-start*/', '/*P8-end*/')
m = re.search(r'@media \(prefers-reduced-motion:no-preference\)\{', css)
before = css[:m.start()] if m else css
inside = css[m.start():] if m else ''
T('the P8 style is in the page once, before the calm block', S.count('/*P8-start*/') == 1 and S.count('/*P8-end*/') == 1 and S.find('/*P8-end*/') < S.find('/* calm: no decorative motion'))
T('every animation lives inside @media (prefers-reduced-motion:no-preference)', bool(m) and 'animation' not in before and inside.count('animation-name') == 4)
T('the four keyframes exist (lock wiggle, Z float, shield breathe, plug slide)', all(('@keyframes ' + k + '{') in inside for k in ('sxlk', 'sxzz', 'sxsd', 'sxpg')))
T('no hard-coded colour and no Arial in the P8 style', css != '' and not re.search(r'#[0-9a-fA-F]{3,8}\b|Arial|rgb\(', css))
T('the closing-band picture has its corner rule again (absolute, bottom right) and a smaller phone size', '.ctaband .ill2.sec2{position:absolute;right:10px;bottom:-6px;' in before and '@media(max-width:600px){.ctaband .ill2.sec2{width:96px}}' in before)
T('the class names the CSS animates are on the pictures', all(x in S for x in ('<path class="lk" ', 'class="zz" ', 'class="zz z2" ', '<path class="sh" ', '<g class="pg">')))
T('the plug cartoon is mapped, so the page swaps the old still symbol for it', 'var ILM={plug:"plug",' in S and S.count('IL2.plug=il2(') == 1)
T('the page still asks for the plug symbol first (fixArt swaps it); nothing else was removed', '<use href="#ill-plug">' in S or 'add("#how","plug","sec-ill",1)' in S)
T('no Claude credit anywhere in the new code', not re.search(r'(?i)claude', css))
if not shutil.which('node'): print('SKIP node not installed'); print('%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
a = S.find('var CH2='); b = S.find('IL2.rs=', a); c = S.find('/* ---- topic cartoons'); d = S.find('var ILM=', c); d2 = S.find(';', S.find('}', d)) + 1
code = S[a:b] + 'IL2.rs=0;' + S[c:d2] + ';return {IL2:IL2,ILM:ILM};'
r = subprocess.run(['node', '-e', 'const o=new Function("window",process.argv[1])({});console.log(JSON.stringify({IL2:o.IL2,ILM:o.ILM}))', code], capture_output=True, text=True)
if r.returncode:
    T('node ran the picture code', False); print(r.stderr[-500:]); print('%d/%d passed' % (sum(R), len(R))); sys.exit(1)
O = json.loads(r.stdout.strip().splitlines()[-1]); I = O['IL2']
T('node ran the picture code and ILM maps plug', O['ILM'].get('plug') == 'plug' and 'plug' in I)
CH = I['mail'][I['mail'].find('<g transform="translate(112 40)">'):]
for k in ('lock', 'sleep', 'shield', 'plug'):
    p = I.get(k, '')
    try: ET.fromstring(p); good = True
    except Exception: good = False
    T(k + ': a valid picture with the same dark-haired character as the rest', good and CH in p and p.startswith('<svg class="ill2"'))
T('lock: shackle wiggles and there are sparkles', 'class="lk"' in I['lock'] and I['lock'].count('class="sp"') == 2)
T('sleep: two floating Z parts and sparkles', I['sleep'].count('class="zz') == 2 and I['sleep'].count('class="sp"') == 2)
T('shield: breathing part and sparkles', 'class="sh"' in I['shield'] and I['shield'].count('class="sp"') == 2)
T('plug: slides (pg), socket slots, check badge, sparkles', 'class="pg"' in I['plug'] and I['plug'].count('class="sp"') == 2 and 'M70 30v12M82 30v12' in I['plug'] and 'M-6 .5l4.2 4.2 8.2-9.6' in I['plug'])
T('the picture code stays outside the old still-picture colours rule: plug uses only the same fills as other props', set(re.findall(r'fill="(#[0-9a-f]+)"', I['plug'])) <= {'#26262a', '#000', '#1d1d20', '#34343a'})
print('%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
