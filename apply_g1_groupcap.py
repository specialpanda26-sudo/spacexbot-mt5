"""Section 3 apply script (group profit target + group loss limit, server side).
Edits backend/burst.py and backend/app.py. Checks every old text appears exactly once; if anything does not fit, NOTHING is changed. Safe to run twice."""
import os, sys

EDITS = {
    'backend/burst.py': [
        ('from . import store as st, links, risk, limits, multi\n', 'from . import store as st, links, risk, limits, multi, groupcap\n'),
        ("        if meta(r['grp']): return True\n", "        m = meta(r['grp'])\n        if m and m.get('k') != 'multi': return True          # a normal multi-entry group is not a burst: it must not hold the next burst back\n"),
        ("    st.put('bg:%d' % first, json.dumps({'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now}))\n",
         "    gm = {'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now}\n    gr = groupcap.rules(uid, n)          # the person's group target / loss limit, when they switched it on\n    if gr: gm.update(tgt=gr['tgt'], loss=gr['loss'])\n    st.put('bg:%d' % first, json.dumps(gm))\n"),
        ("            'each': m.get('each'), 'gb': m.get('gb', 0), 'ids': ','.join(str(i) for i in ids)}\n",
         "            'each': groupcap.each_for(m, len(ids)) if m.get('tgt') or m.get('k') == 'multi' else m.get('each'), 'gb': m.get('gb', 0),\n            'tgt': float(m.get('tgt') or 0), 'loss': float(m.get('loss') or 0), 'kind': m.get('k'), 'ids': ','.join(str(i) for i in ids)}\n"),
    ],
    'backend/app.py': [
        ('from . import lag, multi, automarkets, prefs, scale, burst\n', 'from . import lag, multi, automarkets, prefs, scale, burst, groupcap\n'),
        ("        print('multi-entry', sym, s['side'], n, 'entries sharing', base, 'percent')\n",
         "        print('multi-entry', sym, s['side'], n, 'entries sharing', base, 'percent')\n        groupcap.mark(sid, uid, n)          # group target / loss limit on: this setup goes to the EA as ONE basket\n"),
        ("            sbauth.notify(title, body, key=kk, only=only)\n",
         "            if bg and (burst.meta(bg) or {}).get('k') == 'multi': title = title.replace(' burst ', ' group '); body = body.replace('Burst ', 'Group ', 1)          # a normal group is not a burst\n            sbauth.notify(title, body, key=kk, only=only)\n"),
        ("@app.post('/api/admin/testprice')\n",
         "@app.get('/api/groupcap')\n@need(verified=True)\ndef gcap_get(u): return jsonify(groupcap.view(_mine(u)))\n\n@app.post('/api/groupcap')\n@need(verified=True)\ndef gcap_set(u):\n    j = _j()\n    try: groupcap.save(_mine(u), j)\n    except ValueError as e: return jsonify(error=str(e)), 400\n    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in groupcap.KEYS}})\n    return jsonify(groupcap.view(_mine(u)))\n\n@app.post('/api/admin/testprice')\n"),
    ],
}


def rd(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def main():
    for f in EDITS:
        if not os.path.exists(f): sys.exit('Run this from the project folder (the one that has backend/ and static/).')
    if not os.path.exists('backend/groupcap.py'): sys.exit('backend/groupcap.py is missing. Paste the first block (the new file) before running this script.')
    plan = {}
    for f, edits in EDITS.items():
        s = rd(f); todo = []
        for old, new in edits:
            n = s.count(old)
            if s.count(new) >= 1: continue          # already applied (checked first: some new texts still contain the old text)
            elif n == 1: todo.append((old, new))
            else: sys.exit('STOPPED. Expected one match in %s, found %d for: %r\nNothing was changed.' % (f, n, old[:90]))
        plan[f] = (s, todo)
    done = 0
    for f, (s, todo) in plan.items():
        for old, new in todo: s = s.replace(old, new, 1); done += 1
        if todo:
            with open(f, 'w', encoding='utf-8', newline='') as fh: fh.write(s)
    print('Already applied. Nothing to do.' if not done else 'Done: %d edits applied.' % done)


if __name__ == '__main__':
    main()
