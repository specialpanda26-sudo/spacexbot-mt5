"""Update card picture, with the site character: phone + download arrow + loading line, a green "new" badge, sparkles and the same dark-haired character as every other IL2 cartoon.
Edits static/update.js and tests/test_update5.py. Safe to run twice."""
import re
J = "static/update.js"; T = "tests/test_update5.py"
s = open(J, encoding="utf-8").read()
if "/*U6*/" in s:
    print("already applied")
else:
    a = s.find('  /*U5c*/'); b = s.find("  var CSS = [")
    if a < 0 or b < a or s.count("  var CSS = [") != 1:
        print("STOP: cannot find the cartoon block exactly once"); raise SystemExit(1)
    ch = ("M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18|#1d1d20;M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z|#26262a;"
          "M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z|#34343a")
    chs = "".join('<path d="%s" fill="%s"/>' % tuple(p.split("|")) for p in ch.split(";")) + '<path d="M60 47q6 5 12 0"/>'
    new = r'''  /*U6*/ /* The cartoon "update": the site's dark-haired character next to a phone that downloads (arrow drops in, line loads), a green "new" badge and sparkles. Same look as the IL2 pictures. */
  var CH = '__CH__';
  function art() {
    return '<svg class="ill2 upd" viewBox="0 0 240 170" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
      + '<g transform="translate(14 22)"><g class="up">'
      + '<rect width="58" height="96" rx="11" fill="#26262a"/><path d="M22 10h14"/><rect x="9" y="22" width="40" height="62" rx="8"/>'
      + '<g class="ua"><path d="M29 33v24"/><path d="M20 48l9 9 9-9"/></g>'
      + '<rect class="pt" x="14" y="69" width="30" height="4" rx="2"/><rect class="pf" x="14" y="69" width="30" height="4" rx="2"/>'
      + '</g></g>'
      + '<g transform="translate(88 30)"><g class="nb"><circle r="14" fill="#000"/><path d="M0 6V-6M-5.500-1L0-6.500l5.500 5.500" stroke="#fff" stroke-width="3.200"/></g></g>'
      + '<path class="sp" d="M26 10v10M21 15h10"/><path class="sp" d="M104 92v8M100 96h8"/><path class="sp" d="M70 8v8M66 12h8"/>'
      + '<path d="M114 146c-14 4-26 2-38-4"/><g transform="translate(112 40)">' + CH + '</g></svg>';
  }
'''.replace("__CH__", chs)
    s = s[:a] + new + s[b:]
    s = s.replace('"#sxbUpd .ill2{width:130px;max-width:50%;margin:0 auto}"', '"#sxbUpd .ill2{width:190px;max-width:72%;margin:0 auto}"')
    s = s.replace('".ill2.upd .pf{fill:var(--green);stroke:none}",', '".ill2.upd .pf{fill:var(--green);stroke:none}",\n    ".ill2.upd .nb{transform-box:fill-box;transform-origin:center}",')
    s = s.replace('"@keyframes sxuR{', '".ill2.upd .nb{animation:sxuN 2.4s ease-in-out infinite}",\n    "@keyframes sxuN{0%,100%{transform:scale(1)}50%{transform:scale(1.14)}}",\n    "@keyframes sxuR{')
    open(J, "w", encoding="utf-8").write(s); print("update.js done")
t = open(T, encoding="utf-8").read().split("\n"); out = []
for L in t:
    if L.startswith("  out.art = {"):
        L = L.replace("char: cart.innerHTML.indexOf('#1d1d20') > -1", "char: cart.innerHTML.indexOf('#1d1d20') > -1, badge: /class=\"nb\"/.test(cart.innerHTML), spark: (cart.innerHTML.match(/class=\"sp\"/g) || []).length")
    elif L.startswith("T('the \"update\" cartoon is only"):
        L = "T('the \"update\" cartoon: phone, download arrow, loading line, new badge, sparkles and the dark-haired site character', o['art']['svg'] and o['art']['arrow'] and o['art']['track'] and o['art']['bar'] and o['art']['badge'] and o['art']['spark'] >= 3 and o['art']['char'])"
    elif L.startswith("code_nofill = "):
        L = """code_nofill = src.replace(CH2, '').replace('fill="#26262a"', '').replace('fill="#000"', '').replace('stroke="#fff"', '')"""
    out.append(L)
open(T, "w", encoding="utf-8").write("\n".join(out)); print("test_update5.py done")
