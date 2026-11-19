"""P9b: screens for strategy picks / entries / auto-scale and open trades. Run once from the repo root."""
import sys
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if s.count(old) != 1: sys.exit('NOT FOUND exactly once in %s: %r' % (path, old[:70]))
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
edit('static/index.html', [
    ('function paint() { try { renderTrades(); jr(); sr(); } catch (e) {} try { if (window.sxBotCards) window.sxBotCards(); } catch (e) {} }',
     'function paint() { try { renderTrades(); jr(); sr(); } catch (e) {} try { if (window.sxBotCards) window.sxBotCards(); } catch (e) {} try { if (window.sxOpenTrades) window.sxOpenTrades(); } catch (e) {} }'),
    ('SXJ.broker = j.broker || ""; SXJ.state = "ok";', 'SXJ.broker = j.broker || ""; SXJ.open = j.open || []; SXJ.state = "ok";'),
    ('\n</body></html>', '\n<script src="/static/prefs_ui.js"></script>\n</body></html>'),
])
print('P9b applied')
