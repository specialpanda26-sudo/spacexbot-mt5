"""Section FD1: the sample-data backtest no longer feeds the go-live verdict or the Journal (static/index.html).
Run from the project folder: python apply_fd1.py  (safe to run twice)."""
def edit(path, pairs):
    s = open(path, encoding='utf-8').read(); o = s
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, path + ': need exactly one: ' + old[:60]
        s = s.replace(old, new, 1)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)

edit('static/index.html', [
 ('c4=b?b.pf>1:null,c5=', 'c4=null,c5='),
 ('rw(c4,\\"Backtest evidence\\",b?\\"Profit factor \\"+b.pf.toFixed(2)+\\", \\"+b.pos+\\" of \\"+b.tot+\\" pairs positive.\\":\\"Run the backtest below.\\")'.replace('\\"', '"'),
  'rw(c4,"Backtest evidence","Not tested on real candles yet. The sample backtest below does not count; use tools/backtest.py on your own data.")'),
 ('else if(c4===null){v="Conditions are fine, but nothing is tested yet. Run the backtest.";k=""}',
  'else if(c5!==true){v="Conditions are fine, but nothing is proven yet. Real closed trades are the evidence (30 needed).";k=""}'),
 ('Replays your trend rule on sample candles of all 8 pairs. No trades, no cost.',
  'Replays your trend rule on random sample candles of all 8 pairs. Just a demo: it is not saved to your Journal and does not count in the go-live check.'),
 (';runBt();ja("note","Backtest ran: profit factor "+X.bt.pf.toFixed(2)+", "+X.bt.pos+" of "+X.bt.tot+" pairs positive")},450)', ';runBt()},450)'),
])

NOTE = """
## Section FD1 (fake data fix a: sample backtest out of the go-live verdict and the Journal) DONE (Nov 22)
- static/index.html only. In the Run check card the 'Backtest evidence' row is always 'Not tested' (the random sample result is no longer read), and the verdict can only say 'Conditions pass' when 30+ real closed trades beat break-even (otherwise 'nothing is proven yet'; a failed check or a losing real record still says 'Not now' / 'Not recommended'). The sample backtest card still runs as a demo, its note now says it is not saved and does not count, and it no longer writes 'Backtest ran: ...' into the Journal. tests/test_fd1.py. apply_fd1.py.
- Fake data scan items 2-5 are still open (b Focus pair, c News list, d Weekly brief / Home chart labels). Owner picks which next.
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Section FD1' not in h:
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h.rstrip('\n') + '\n' + NOTE)
print('ok docs/HANDOFF.md')
