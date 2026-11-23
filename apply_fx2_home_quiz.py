"""FX2 + FX3: Home guide wording, and the learning path quiz answers.
Run from the repo folder: python3 apply_fx2_home_quiz.py"""
import sys

def rep(path, old, new, count=1):
    s = open(path, encoding='utf-8').read()
    if s.count(old) != count:
        sys.exit('STOP: %s: expected %d match(es), found %d for: %s' % (path, count, s.count(old), old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new))
    print('ok', path)

rep('static/guide.js', "Short cartoon steps: sign up, connect, demo or real, start, signals and safety.", "Quick guide: sign up, connect, demo or real, start, signals and safety.")

C = 'static/course.js'
rep(C, '''    p.innerHTML = h;
  }
  document.addEventListener("click"''', '''    var top = p.scrollTop; p.innerHTML = h; p.scrollTop = keep ? top : 0;          /* FX3: a tap on an answer must not throw the screen back to the top */
  }
  document.addEventListener("click"''')
rep(C, '''  function draw() {
    var p = document.getElementById("coursep");''', '''  function draw(keep) {
    var p = document.getElementById("coursep");''')
rep(C, '''          return '<button class="btn block" type="button" style="text-align:left;margin:4px 0" data-c="pick" data-q="' + qi + '" data-o="' + oi + '" aria-pressed="' + (S.pick[qi] === oi) + '">' + esc(o) + "</button>"; }).join("");''',
      '''          var on = S.pick[qi] === oi;          /* FX3: the chosen answer is clearly marked (green border, soft green fill, tick) */
          return '<button class="btn block" type="button" style="text-align:left;margin:4px 0;' + (on ? "border-color:var(--green);background:var(--green-soft);box-shadow:0 3px 0 var(--green);font-weight:700" : "") + '" data-c="pick" data-q="' + qi + '" data-o="' + oi + '" aria-pressed="' + on + '">' + (on ? "\\u2713 " : "") + esc(o) + "</button>"; }).join("");''')
rep(C, '''      }).join("") + (S.err ? '<p class="err">' + esc(S.err) + "</p>" : "") +
        '<button class="btn primary big block" type="button" data-c="check"''', '''      }).join("") + (S.err ? '<p class="err">' + esc(S.err) + "</p>" : "") +
        (l.quiz.every(function (q, i) { return typeof S.pick[i] === "number"; }) ? "" : '<p class="note" style="text-align:center">Pick one answer for each question. ' + l.quiz.filter(function (q, i) { return typeof S.pick[i] !== "number"; }).length + " still to answer.</p>") +
        '<button class="btn primary big block" type="button" data-c="check"''')
rep(C, '''else if (c === "pick") { S.pick[+b.getAttribute("data-q")] = +b.getAttribute("data-o"); draw(); }''', '''else if (c === "pick") { S.pick[+b.getAttribute("data-q")] = +b.getAttribute("data-o"); draw(true); }''')
rep(C, '''lesson(S.id).quiz.length; i++) a.push(S.pick[i]); draw();''', '''lesson(S.id).quiz.length; i++) a.push(S.pick[i]); draw(true);''')
print('FX2 + FX3 done')
