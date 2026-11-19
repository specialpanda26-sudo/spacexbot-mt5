"""Profit not showing, cause found in the MT5 bridge: Report() sent each open/close result ONCE. If that single WebRequest failed (internet blip, Render waking up
slower than the 15 s limit), the close was never recorded and the Profit and Loss card never saw the trade. Also an HTTP error answer (500, 502) was treated as success.
Now: an error answer counts as a failure, and a report is tried up to 4 times (1.5 s, 3 s, 6 s apart) before giving up with a clear line in the Experts tab.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
F = 'ea/SpaceXBridge.mq5'
s = open(F, encoding='utf-8').read()
if 'ReportTries' in s:
    print('already applied'); raise SystemExit
E = [
 ('   if(code < 0){ Print("WebRequest error ", GetLastError(), " - add ", ServerUrl, " in Tools>Options>Expert Advisors"); return ""; }\n',
  '   if(code < 0){ Print("WebRequest error ", GetLastError(), " - add ", ServerUrl, " in Tools>Options>Expert Advisors"); return ""; }\n'
  '   if(code >= 300){ Print("Server answered HTTP ", code, " for ", path); return ""; }          // an error answer is a failure, not a result\n'),
 ('void Report(long id, string status, string extra)\n{\n   Post("/api/ea/report", "{\\"id\\":" + (string)id + ",\\"status\\":\\"" + status + "\\"" + extra + "}");\n}\n',
  'input int ReportTries = 4;   // how many times a trade report (open/close) is sent before giving up\n'
  'void Report(long id, string status, string extra)\n{\n'
  '   string body = "{\\"id\\":" + (string)id + ",\\"status\\":\\"" + status + "\\"" + extra + "}";\n'
  '   int wait = 1500;\n'
  '   for(int t = 1; t <= ReportTries; t++)\n'
  '   {\n'
  '      if(Post("/api/ea/report", body) != "") return;\n'
  '      if(t < ReportTries){ Print("Report ", status, " for signal ", id, " not delivered (try ", t, " of ", ReportTries, "), trying again"); Sleep(wait); wait *= 2; }\n'
  '   }\n'
  '   Print("Report ", status, " for signal ", id, " could NOT be delivered. The server may miss this trade: ", body);\n'
  '}\n'),
]
for a, b in E:
    assert s.count(a) == 1, 'not found exactly once: ' + a[:60]
for a, b in E: s = s.replace(a, b)
open(F, 'w', encoding='utf-8').write(s)
print('done')
