"""GS1: bring the moving candles back on the Getting Started page. Run from the repo folder: python apply_gs1_candles.py (safe to run twice).
Cause: static/screen.js adds a <style id="sc2"> to the page head. The Getting Started canvas was ALSO id="sc2", so $("#sc2") found the style tag first, stream() got a non-canvas and stopped before drawing. No candles.
Fix (static/index.html only): the canvas gets its own id "gsc", intro() looks that id up, and stream() ignores anything that is not a canvas instead of crashing."""
import sys

PATH = 'static/index.html'


def rd(p):
    return open(p, encoding='utf-8').read()


def wr(p, s):
    open(p, 'w', encoding='utf-8').write(s)


def edit(s, old, new, marker):
    if marker in s:
        print('skip (already there):', marker[:50])
        return s
    if s.count(old) != 1:
        print('STOP: cannot find exactly once ->', old[:70])
        sys.exit(1)
    print('edited:', marker[:50])
    return s.replace(old, new, 1)


s = rd(PATH)
s = edit(s, '<div class="gpage"><canvas id="sc2"></canvas>', '<div class="gpage"><canvas id="gsc"></canvas>', '<canvas id="gsc"></canvas>')
s = edit(s, 'stream($("#sc2"),"#10151E");', 'stream($("#gsc"),"#10151E");', 'stream($("#gsc"),"#10151E");')
s = edit(s, 'function stream(cv,bgh){if(!cv)return;', 'function stream(cv,bgh){if(!cv||!cv.getContext)return;', 'if(!cv||!cv.getContext)return;')
wr(PATH, s)
print('done: Getting Started candles restored')
