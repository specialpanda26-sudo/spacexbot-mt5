"""BT3 patch: Big burst numbers on the Burst card (static/index.html). The server already saves big_n and big_usd (backend/burst.py), only the fields were missing.
Shows them in plain view with the reason: a big burst happens only when enough strategies agree, and it needs MORE entries than the normal burst.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_bt3_bigburst.py"""
import sys
F, H = 'static/index.html', 'docs/HANDOFF.md'
Q = '"'
R = [
 ('<button class="btn primary block" id="bswSave">Save numbers</button>',
  '<h3 style="margin:12px 0 0">Big burst (rare, strong setups)</h3><p class="note" id="bswBigWhy"></p><div class="inp-row"><div class="field"><label for="bswBigN">Big burst entries</label><input class="inp" id="bswBigN" type="number" min="1" max="15" step="1" inputmode="numeric"></div><div class="field"><label for="bswBigUsd">Big target per entry ($)</label><input class="inp" id="bswBigUsd" type="number" min="0.05" step="0.05" inputmode="decimal"></div></div><p class="note" id="bswBigPrev"></p>'
  '<button class="btn primary block" id="bswSave">Save numbers</button>'),
 ('$("#bswStake").value=s.stake_usd==null?"":s.stake_usd;bswPrev();',
  '$("#bswStake").value=s.stake_usd==null?"":s.stake_usd;bswQ=s.quick_n||0;$("#bswBigN").value=s.big_n||"";$("#bswBigUsd").value=s.big_usd||"";if(j.ceiling){$("#bswN").max=j.ceiling;$("#bswBigN").max=j.ceiling}bswBigShow(j);bswPrev();'),
 ('$("#bswN").oninput=bswPrev;$("#bswUsd").oninput=bswPrev;',
  '$("#bswN").oninput=function(){bswPrev();bswBigPrev()};$("#bswUsd").oninput=bswPrev;$("#bswBigN").oninput=bswBigPrev;$("#bswBigUsd").oninput=bswBigPrev;\n'
  ' /*BT3*/var bswQ=0,bswScore=0;\n'
  ' function bswBigShow(j){bswScore=j.big_score||0;$("#bswBigWhy").textContent="A big burst happens only when "+(bswScore||"several")+" strategies agree on the same idea at the same time. Then the bot uses these numbers instead of the normal ones. How many must agree is set by the owner; you cannot change it here.";bswBigPrev()}\n'
  ' function bswBigPrev(){var n=Math.round(parseFloat($("#bswBigN").value)||0),u=parseFloat($("#bswBigUsd").value)||0,q=Math.round(parseFloat($("#bswN").value)||0)||bswQ,t="";\n'
  '  if(n&&q&&n<q)t="Big burst entries must be at least the Entries above. Saving will be refused.";else if(n&&q&&n===q)t="Same as Entries, so a big burst never happens. Use more entries than the normal burst to switch it on.";else if(n&&u)t=n+" entries x "+u+" USD each: a big burst closes at "+(Math.round(n*u*100)/100)+" USD in total.";$("#bswBigPrev").textContent=t}'),
 ('if(i)body.idle_min=i;if(n)body.quick_n=n;if(u)body.quick_usd=u;',
  'var bn=Math.round(parseFloat($("#bswBigN").value)||0),bu=parseFloat($("#bswBigUsd").value)||0;if(i)body.idle_min=i;if(n)body.quick_n=n;if(u)body.quick_usd=u;if(bn)body.big_n=bn;if(bu)body.big_usd=bu;\n'
  '  var qn=n||bswQ;if(bn&&qn&&bn<qn){$("#bswMsg").textContent="Big burst entries must be at least "+qn+" (the normal Entries).";return}'),
]
s = open(F, encoding='utf-8').read()
if '/*BT3*/' in s: print(F, 'already patched')
else:
    for old, new in R:
        if s.count(old) != 1: sys.exit('STOP: anchor found %d times in %s: %s' % (s.count(old), F, old[:70]))
    for old, new in R: s = s.replace(old, new)
    open(F, 'w', encoding='utf-8').write(s); print('patched', F)
MARK = '## Section BT3 (Big burst numbers on the card)'; h = open(H, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has BT3')
else:
    open(H, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 24)
- static/index.html, Burst card: new part "Big burst (rare, strong setups)" with Big burst entries and Big target per entry ($), saved with Save numbers (big_n, big_usd, already supported by backend/burst.py). Block marker /*BT3*/.
- The card says in plain words that a big burst needs N strategies to agree (N = owner setting burst_big_score, read from GET /api/burst big_score, not editable by users) and that Big entries must be MORE than the normal Entries, otherwise a big burst never happens (burst.plan needs big_n > quick_n). Fewer entries than normal is refused on the card; the same number shows a warning.
- Entries inputs now use the owner ceiling as their max. Not checked on a real phone. Test: tests/test_bt3.py.
''')
    print('HANDOFF updated')
