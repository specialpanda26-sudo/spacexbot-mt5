/* C2: the learning path. A card on Home and a pop-up with short lessons and quizzes (GET /api/course, POST /api/course/quiz). The server grades. */
(function () {
  "use strict";
  if (!window.SXA) return;
  var vh = document.getElementById("view-home"); if (!vh) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function art(k) { var I = window.IL2 || {}; return I[k] || ""; }
  var C = document.createElement("div"); C.className = "card"; C.id = "coursec"; C.hidden = true;
  vh.insertBefore(C, vh.firstChild ? vh.firstChild.nextSibling : null);
  var D = null, LH = "", OV = null, S = { v: "list", id: null, pick: [], res: null, busy: false, err: "" };
  function lesson(id) { return D && D.lessons.filter(function (l) { return l.id === id; })[0]; }
  function drawCard() {
    var u = me(), on = !!(u && u.verified && D); C.hidden = !on; C.style.display = on ? "" : "none";
    var h = "";
    if (on) {
      var all = D.complete, pc = Math.round(100 * D.done / D.total);
      h = '<div class="card-head"><h2>Your learning path</h2><span class="chip ' + (all ? "ok" : "info") + '">' + D.done + " of " + D.total + "</span></div>" +
        '<div style="height:8px;border-radius:8px;background:var(--surface2);overflow:hidden"><div style="height:100%;width:' + pc + '%;background:var(--green)"></div></div>' +
        '<p class="note">' + (all ? "All lessons done. Real trading is unlocked for you." : "Short lessons, about two minutes each. Demo trading is open now. Finishing the lessons unlocks Real.") + "</p>" +
        '<button class="btn primary block" type="button" data-c="open">' + (all ? "Review lessons" : D.done ? "Continue learning" : "Start learning") + "</button>";
    }
    if (h !== LH) C.innerHTML = LH = h;
  }
  function load() { var u = me(); if (!(u && u.verified)) { D = null; drawCard(); return; } SXA.api("/api/course").then(function (j) { D = j; drawCard(); if (OV) draw(); }).catch(function () {}); }
  function close() { if (OV && OV.remove) OV.remove(); OV = null; }
  function open(v, id) {
    S.v = v; S.id = id || null; S.pick = []; S.res = null; S.err = "";
    if (!OV) {
      OV = document.createElement("div"); OV.className = "ov"; OV.id = "coursov";
      OV.innerHTML = '<div class="bd" data-c="close"></div><div class="panel" role="dialog" aria-modal="true" id="coursep" style="max-height:88vh;overflow:auto"></div>';
      document.body.appendChild(OV); try { void OV.offsetWidth; } catch (e) {} OV.className = "ov open";
    }
    draw();
  }
  function draw() {
    var p = document.getElementById("coursep"); if (!p || !D) return; var h = "", l = lesson(S.id);
    if (S.v === "list") {
      h = art("rocket") + '<h2 style="text-align:center">Your learning path</h2><p class="muted" style="text-align:center">Finish the lessons one by one to unlock Real trading. Demo is open any time.</p>' +
        D.lessons.map(function (x, i) {
          var lk = x.status === "locked";
          return '<button class="btn block" type="button" style="text-align:left;margin:6px 0" data-c="lesson" data-id="' + esc(x.id) + '"' + (lk ? " disabled" : "") + "><b>" + (i + 1) + ". " + esc(x.title) + "</b> " +
            '<span class="chip ' + (x.status === "done" ? "ok" : lk ? "" : "info") + '">' + (x.status === "done" ? "Done" : lk ? "Locked" : "Start") + "</span><br><small>" + esc(x.intro) + "</small></button>";
        }).join("") + '<button class="btn block" type="button" data-c="close">Close</button>';
    } else if (S.v === "lesson" && l) {
      h = art(l.art) + "<h2 style=\"text-align:center\">" + esc(l.title) + "</h2><ul>" + l.points.map(function (t) { return "<li style=\"margin:8px 0\">" + esc(t) + "</li>"; }).join("") + "</ul>" +
        '<button class="btn primary big block" type="button" data-c="quiz">Take the quiz</button><button class="btn block" type="button" data-c="list">Back</button>';
    } else if (S.v === "quiz" && l) {
      h = "<h2>" + esc(l.title) + ": quick quiz</h2>" + l.quiz.map(function (q, qi) {
        return "<p><b>" + (qi + 1) + ". " + esc(q.q) + "</b></p>" + q.o.map(function (o, oi) {
          return '<button class="btn block" type="button" style="text-align:left;margin:4px 0" data-c="pick" data-q="' + qi + '" data-o="' + oi + '" aria-pressed="' + (S.pick[qi] === oi) + '">' + esc(o) + "</button>"; }).join("");
      }).join("") + (S.err ? '<p class="err">' + esc(S.err) + "</p>" : "") +
        '<button class="btn primary big block" type="button" data-c="check"' + (S.pick.length === l.quiz.length && S.pick.indexOf(undefined) < 0 && !S.busy ? "" : " disabled") + '>Check answers</button><button class="btn block" type="button" data-c="lesson" data-id="' + esc(l.id) + '">Back to the lesson</button>';
    } else if (S.v === "result" && S.res && l) {
      var r = S.res, nx = D.next;
      h = art(r.passed ? "yay" : "wait") + '<h2 style="text-align:center">' + (r.passed ? "Lesson done!" : "Almost there") + '</h2><p class="muted" style="text-align:center">You got ' + r.score + " of " + r.total + " right." + (r.passed ? "" : " You need 2. Read the lesson again and retry.") + "</p>" +
        r.results.map(function (x, i) { return '<p class="note">' + (x.ok ? "✓ " : "✗ ") + esc(l.quiz[i].q) + (x.ok ? "" : "<br>" + esc(x.why)) + "</p>"; }).join("") +
        (r.passed ? (nx ? '<button class="btn primary big block" type="button" data-c="lesson" data-id="' + esc(nx) + '">Next lesson</button>' : '<p class="note"><b>All lessons done. Real trading is unlocked.</b></p>') : '<button class="btn primary big block" type="button" data-c="lesson" data-id="' + esc(l.id) + '">Read it again</button>') +
        '<button class="btn block" type="button" data-c="list">All lessons</button>';
    } else h = '<button class="btn block" type="button" data-c="close">Close</button>';
    p.innerHTML = h;
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-c]"); if (!b || (!C.contains(b) && !(OV && OV.contains(b)))) return; var c = b.getAttribute("data-c");
    if (c === "open") open("list"); else if (c === "close") close(); else if (c === "list") open("list");
    else if (c === "lesson") open("lesson", b.getAttribute("data-id")); else if (c === "quiz") open("quiz", S.id);
    else if (c === "pick") { S.pick[+b.getAttribute("data-q")] = +b.getAttribute("data-o"); draw(); }
    else if (c === "check" && !S.busy) {
      S.busy = true; var a = []; for (var i = 0; i < lesson(S.id).quiz.length; i++) a.push(S.pick[i]); draw();
      SXA.api("/api/course/quiz", { method: "POST", body: { lesson: S.id, answers: a } })
        .then(function (j) { S.busy = false; D = j.view; S.res = j; S.v = "result"; drawCard(); draw(); })
        .catch(function (x) { S.busy = false; S.err = (x && x.message) || "Could not check the answers."; draw(); });
    }
  });
  window.sxCourse = { open: function () { if (D) open("list"); }, state: function () { return D; } };
  load(); setInterval(load, 60000); setTimeout(load, 2500);
})();
