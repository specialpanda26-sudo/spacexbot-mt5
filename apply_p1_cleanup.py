"""Section 1 apply script (clean-up).
1) Removes the little letters (H, M, B, T, C) drawn next to each tab name on wide screens.
2) Removes every "Replay setup" button (Settings page, Upgrades panel, command search) and the code behind them.
Checks every old text appears exactly once. If anything does not fit, NOTHING is changed. Safe to run twice."""
import os, sys

F = 'static/index.html'
EDITS = [
    ('@media(min-width:900px){.nav button::after{content:attr(data-k);font:800 10px/1 var(--font);color:var(--muted);'
     'border:1.5px solid var(--line);border-radius:5px;padding:2px 5px;background:var(--surface)}}\n', ''),
    ('\n      <button class="btn block" id="obReplay">Replay setup</button>', ''),
    ('  if(t.id==="obReplay"){S.onboarded=false;save();show("home");return}\n', ''),
    ('{t:"Replay setup",h:"",f:function(){$("#obReplay").click()}},', ''),
    ('<button class="btn block" data-up="replay">Replay setup</button>', ''),
    (' if(b.dataset.up==="replay"){closeSet();var r=$("#obReplay");if(r)r.click();return}\n', ''),
]


def rd(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def main():
    if not os.path.exists(F):
        sys.exit('Run this from the project folder (the one that has static/index.html).')
    s = rd(F)
    todo = []
    for old, new in EDITS:
        n = s.count(old)
        if n == 1:
            todo.append((old, new))
        elif n == 0 and new == '' and 'Replay setup' not in s:
            continue
        else:
            sys.exit('STOPPED. Expected one match, found %d for: %r\nNothing was changed.' % (n, old[:80]))
    if not todo:
        print('Already applied. Nothing to do.')
    else:
        for old, new in todo:
            s = s.replace(old, new)
        if 'Replay setup' in s or 'obReplay' in s:
            sys.exit('STOPPED. A Replay setup leftover is still there. Nothing was changed.')
        with open(F, 'w', encoding='utf-8', newline='') as f:
            f.write(s)
        print('Done: %d edits applied to %s' % (len(todo), F))


if __name__ == '__main__':
    main()
