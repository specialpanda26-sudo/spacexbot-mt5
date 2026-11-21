"""Update card picture, simple: only the phone, the download arrow and a line under it that loads. Edits static/update.js and tests/test_update5.py. Safe to run twice."""
import re
J = "static/update.js"; T = "tests/test_update5.py"
s = open(J, encoding="utf-8").read()
if "/*U5c*/" in s:
    print("already applied")
else:
    a = s.find('  /* The cartoon "update"'); b = s.find("  function el(tag")
    if a < 0 or b < a or s.count("  function el(tag") != 1:
        print("STOP: cannot find the cartoon block exactly once"); raise SystemExit(1)
    new = r'''  /*U5c*/ /* The cartoon "update": only a phone, a download arrow dropping in and a line under the arrow that loads. */
  function art() {
    return '<svg class="ill2 upd" viewBox="0 0 120 140" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
      + '<g transform="translate(31 14)"><g class="up">'
      + '<rect width="58" height="96" rx="11" fill="#26262a"/><path d="M22 10h14"/><rect x="9" y="22" width="40" height="62" rx="8"/>'
      + '<g class="ua"><path d="M29 33v24"/><path d="M20 48l9 9 9-9"/></g>'
      + '<rect class="pt" x="14" y="69" width="30" height="4" rx="2"/><rect class="pf" x="14" y="69" width="30" height="4" rx="2"/>'
      + '</g></g></svg>';
  }
  var CSS = [
    "#sxbUpd{z-index:100000}",
    "#sxbUpd .ucart{display:grid;place-items:center}",
    "#sxbUpd .ill2{width:130px;max-width:50%;margin:0 auto}",
    "#sxbUpd h2,#sxbUpd p{text-align:center}",
    "#sxbUpd .unote{background:var(--surface2);border:1px solid var(--line);border-radius:14px;padding:10px 14px;color:var(--fg);font-size:14px}",
    "#sxbUpd .btn.q{background:transparent;border-color:transparent;box-shadow:none;color:var(--muted)}",
    "#sxbUpd .btn.q:active{transform:none}",
    ".ill2.upd .ua{stroke:var(--green);stroke-width:3.2}",
    ".ill2.upd .pt{fill:none}",
    ".ill2.upd .pf{fill:var(--green);stroke:none}",
    "@media (prefers-reduced-motion:no-preference){",
    ".ill2.upd .up,.ill2.upd .ua,.ill2.upd .pf{transform-box:fill-box;animation-iteration-count:infinite!important}",
    ".ill2.upd .up{animation:sxuP 2.6s ease-in-out infinite}",
    ".ill2.upd .ua{animation:sxuA 3s ease-in-out infinite}",
    ".ill2.upd .pf{transform-origin:0 50%;animation:sxuR 3s ease-in-out infinite}",
    "@keyframes sxuP{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}",
    "@keyframes sxuA{0%{transform:translateY(-28px);opacity:0}20%{opacity:1}42%{transform:translateY(0)}50%{transform:translateY(4px)}58%,88%{transform:translateY(0);opacity:1}100%{transform:translateY(0);opacity:0}}",
    "@keyframes sxuR{0%{transform:scaleX(.05)}60%,100%{transform:scaleX(1)}}",
    "}"
  ].join("\n");
'''
    s = s[:a] + new + s[b:]
    s = re.sub(r"\n  var CH = '[^\n]*\n", "\n", s, count=1)
    open(J, "w", encoding="utf-8").write(s)
    print("update.js done")
t = open(T, encoding="utf-8").read().split("\n"); out = []; ch = 0
for L in t:
    if L.startswith("  out.art = {"):
        L = """  out.art = { svg: cart.innerHTML.indexOf('class="ill2 upd"') > -1, arrow: /class="ua"/.test(cart.innerHTML), track: /class="pt"/.test(cart.innerHTML), bar: /class="pf"/.test(cart.innerHTML), extra: /class="(uf|ug|us|ux|uc|uk|pl|st)[ "]/.test(cart.innerHTML), char: cart.innerHTML.indexOf('#1d1d20') > -1 };"""; ch += 1
    elif L.startswith("T('the \"update\" cartoon is there"):
        L = """T('the "update" cartoon is only a phone, a download arrow and a loading line (no flame, sparkles, character or extras)', o['art']['svg'] and o['art']['arrow'] and o['art']['track'] and o['art']['bar'] and not o['art']['extra'] and not o['art']['char'])"""; ch += 1
    elif L.startswith("T('the dark-haired site character") or L.startswith("T('the new scene parts"):
        ch += 1; continue
    out.append(L)
open(T, "w", encoding="utf-8").write("\n".join(out)); print("test_update5.py edited lines:", ch)
