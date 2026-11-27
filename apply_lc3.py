"""LC3: the Burst card gets clear boxes, a plain explanation, and the Biggest lot box (LC1/LC2). Safe to run twice."""
import sys, re
P = 'static/index.html'
s = open(P, encoding='utf-8').read()
if 'LC3-start' in s: print('already done'); sys.exit(0)

def field(id_, label, extra, hint, note=''):
    return ('<div class="field"><label for="%s">%s</label><input class="inp" id="%s" %s><small class="hint">%s</small>%s</div>'
            % (id_, label, id_, extra, hint, note))
def box(title, body): return '<div class="bbox"><h3>%s</h3>%s</div>' % (title, body)

NUM = 'type="number" step="1" inputmode="numeric"'
DEC = 'type="number" inputmode="decimal"'
card = (
 '<p class="note"><b>What burst does, in plain words.</b> When the market is quiet and no strategy has a signal, the bot opens several small trades on the same idea at once. '
 'When their profit together reaches your target, it closes them all together. Your daily limits and loss stops still apply. Try it on a demo account first.</p>'
 '<button type="button" class="switch" role="switch" aria-checked="false" id="bswOn"><span><b>Burst switch</b><small>On = the bot may open a burst group when the market is quiet. Saves the moment you tap it.</small></span><span class="sw"></span></button>'
 '<p class="note" id="bswNow" role="status"></p>'
 + box('1. When it starts', field('bswIdle', 'Quiet minutes first', NUM + ' min="1" max="60"', 'Minutes with no strategy signal before a burst may start. Example: 5 means the bot waits 5 quiet minutes first.'))
 + box('2. How many trades, and when to close',
       field('bswN', 'Entries (trades in one group)', NUM + ' min="1" max="15"', 'How many small trades open together. Example: 5.')
       + field('bswUsd', 'Target per entry ($)', DEC + ' min="0.05" step="0.05"', 'Profit you want from each trade. The group closes when the total reaches Entries x Target.')
       + '<p class="note" id="bswPrev"></p>')
 + box('3. How big each trade is',
       '<p class="note">Fill only the box for your broker. Empty or 0 means the bot decides the size itself.</p>'
       + field('bswStake', 'Stake per entry ($) - Deriv only', DEC + ' min="0" step="0.05" placeholder="0.5"', 'Money each trade puts in on Deriv. 0 = normal sizing. Deriv has its own smallest stake and tells you if it refuses one.')
       + field('bswLot', 'Lot per entry - FBS / MT5 only', DEC + ' min="0" step="0.01" placeholder="0.01"', 'Size of each trade on MT5. Empty = automatic. Example: 0.02.')
       + field('bswMaxLot', 'Biggest lot - FBS / MT5 only', DEC + ' min="0" max="100" step="0.01" placeholder="no limit"', 'A hard ceiling for any one MT5 trade, burst or normal. If a lot is bigger, it is cut down to this. Empty or 0 = no ceiling. Example: 0.06.')
       + '<p class="note" id="bswLotWarn" role="status"></p>')
 + box('4. Safety', field('bswLoss', 'Most a burst group may lose ($)', DEC + ' min="0" step="0.5" placeholder="no limit"', 'If the group is down this much, all its trades close. Empty = no limit.'))
 + box('Every minute (off by default)',
       '<button type="button" class="switch" role="switch" aria-checked="false" id="bswMin"><span><b>Trade every minute</b><small>On = the bot opens a group every minute, even with no strategy signal, up to an hourly cap. Loss limits still apply.</small></span><span class="sw"></span></button>'
       + field('bswMinN', 'Entries each minute (2 or more)', NUM + ' min="2" max="15"', 'How many trades open each minute while this is on.'))
 + box('Big burst (rare, strong setups)',
       '<p class="note" id="bswBigWhy"></p>'
       + field('bswBigN', 'Big burst entries', NUM + ' min="1" max="15"', 'Must be more than Entries above, or a big burst never happens.')
       + field('bswBigUsd', 'Big target per entry ($)', DEC + ' min="0.05" step="0.05"', 'Profit you want from each trade in a big burst.')
       + '<p class="note" id="bswBigPrev"></p>')
 + '<button class="btn primary block" id="bswSave">Save numbers</button><p class="note" id="bswMsg" role="status"></p>'
 '<details><summary class="note">More about burst</summary><p class="note">After the quiet minutes with no signal, the bot opens this many entries on one idea and closes them at the target, or when the profit starts to go away. '
 'Auto settings turns burst off. The MT5 bridge does the closing; phone-only mode cannot close for you.</p></details>'
)
assert "'" not in card, 'an apostrophe would break the JS string'
new_head = 'vb.insertBefore(card(["Burst mode",\'<span class="chip info" id="bswChip"></span>\'],\'' + card + '\'),vb.firstChild);\n /*LC3-start*/ var bswOn=false,bswMinOn=false;'
m = re.search(r'vb\.insertBefore\(card\(\["Burst mode".*?\),vb\.firstChild\);\n var bswOn=false,bswMinOn=false;', s, re.S)
if not m: print('Burst card not found'); sys.exit(1)
s = s[:m.start()] + new_head + s[m.end():]

def rep(old, new):
    global s
    if s.count(old) != 1: print('NOT FOUND:', old[:60]); sys.exit(1)
    s = s.replace(old, new, 1)
rep('$("#bswLot").value=s.lot>0?s.lot:"";', '$("#bswLot").value=s.lot>0?s.lot:"";$("#bswMaxLot").value=s.max_lot>0?s.max_lot:"";')
rep('body.lot=lt===""?0:parseFloat(lt);', 'body.lot=lt===""?0:parseFloat(lt);var mxl=$("#bswMaxLot").value.trim();body.max_lot=mxl===""?0:parseFloat(mxl);')
rep('.note{font-size:13px;color:var(--muted);font-weight:600}',
    '.note{font-size:13px;color:var(--muted);font-weight:600}\n'
    '.bbox{border:2px solid var(--line);border-radius:16px;background:var(--surface2);padding:12px;display:grid;gap:12px}\n'
    '.bbox h3{font-size:14px;margin:0}\n.bbox .field{display:grid;gap:4px}\n.bbox .hint{font-size:12px;color:var(--muted);font-weight:600;line-height:1.35}')
open(P, 'w', encoding='utf-8').write(s)
print('LC3 applied to', P)
