"""LC3 checks: the Burst card has clear boxes, a hint under every input, a plain explanation, and the Biggest lot box is wired. No network.
Run: python tests/test_lc3.py   (exit 1 on any FAIL)"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
m = re.search(r'/\*BT1-start\*/(.*?)/\*BT1-end\*/', s, re.S); src = m.group(1) if m else ''
a = src.find('vb.insertBefore(card(["Burst mode"'); b = src.find('),vb.firstChild);', a); card = src[a:b]
ok = []
def chk(name, c): ok.append((name, bool(c)))
ids = ['bswIdle', 'bswN', 'bswUsd', 'bswStake', 'bswLot', 'bswMaxLot', 'bswLoss', 'bswMinN', 'bswBigN', 'bswBigUsd']
chk('card found', len(card) > 500)
chk('plain explanation is at the top', 'What burst does, in plain words' in card and card.find('plain words') < card.find('id="bswOn"'))
for i in ids:
    fm = re.search(r'<div class="field"><label for="%s">([^<]+)</label><input class="inp" id="%s"[^>]*><small class="hint">([^<]{20,})</small></div>' % (i, i), card)
    chk('%s: a label and a plain hint under the box' % i, fm)
boxes = re.findall(r'<div class="bbox"><h3>(.*?)</h3>(.*?)</div>(?=<div class="bbox">|<button class="btn primary)', card, re.S)
chk('6 boxes with a title', len(boxes) == 6)
chk('every input sits inside a box', all(any('id="%s"' % i in body for _, body in boxes) for i in ids))
chk('the old ids the other tests use are all still there', all(('id="%s"' % i) in card for i in ['bswOn', 'bswNow', 'bswChip', 'bswMin', 'bswPrev', 'bswLotWarn', 'bswBigWhy', 'bswBigPrev', 'bswSave', 'bswMsg']))
chk('Biggest lot is filled from the server', '$("#bswMaxLot").value=s.max_lot>0?s.max_lot:""' in src)
chk('Biggest lot is saved as max_lot (empty = 0)', 'body.max_lot=mxl===""?0:parseFloat(mxl)' in src)
chk('the box css exists', '.bbox{' in s and '.bbox .hint{' in s)
chk('no stray apostrophe broke the page script', "'" not in card.split("'<span class=\"chip info\" id=\"bswChip\"></span>'],'", 1)[-1].rsplit("'", 1)[0])
badn = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if badn else 0)
