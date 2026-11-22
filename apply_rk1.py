"""Rk1: static/index.html. The welcome rocket cartoon (IL2.rocket, also IL2.rs) is repainted: bright flat fills with a darker shade peeking out, fills shifted off a thick violet outline, yellow ticks. Flame and sparkles keep their animation. Other cartoons are not touched."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
OLD = '''IL2.rs=IL2.rocket.replace('class="ill2"','class="ill2 sm"');'''
NEW = r'''/* rk1: repainted welcome rocket + character (offset fills, darker shade underneath, violet outline) */
IL2.rocket=(function(){var G=['#5BE38E','#2FB864'],S=['#56B6FF','#2F86E0'],U=['#FFD43B','#F0A800'],B=['#FF6B72','#E0444F'],W=['#FFFFFF','#DCD6FF'],K='#7F61F5';
function sh(s,m){var c=s[s.length-1],f=m==='l'?'none':c[m==='h'?1:0],a=m==='l'?' stroke="'+K+'" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"':' stroke="none"';
 return s[0]==='o'?'<circle cx="'+s[1]+'" cy="'+s[2]+'" r="'+s[3]+'" fill="'+f+'"'+a+'/>':'<path d="'+s[0]+'" fill="'+f+'"'+a+'/>'}
function lay(a){var h='',f='',l='';a.forEach(function(s){h+=sh(s,'h');f+=sh(s,'f');l+=sh(s,'l')});return h+'<g transform="translate(3.5 -3.5)">'+f+'</g>'+l}
var R=[['M30 0c14 10 18 30 12 52H18C12 30 16 10 30 0z',W],['M30 0C38 5 42 10 42 16H18C18 10 22 5 30 0z',B],['M18 40L8 54l12-4z',G],['M42 40l10 14-12-4z',G],['o',30,24,8,S]];
var C=[['M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18',S],['M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z',W],['M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z',U]];
return '<svg class="ill2" viewBox="0 0 240 170" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
 +'<path d="M114 146c-14 4-26 2-38-4" stroke="'+K+'" stroke-width="4"/>'
 +'<g transform="translate(24 16)"><g class="fl">'+lay([['M24 56q6 16 12 0z',U]])+'</g>'+lay(R)+'</g>'
 +'<g transform="translate(112 40)">'+lay(C)+'<path d="M60 47q6 5 12 0" stroke="'+K+'" stroke-width="3.5"/></g>'
 +'<path class="sp" d="M92 24v10M87 29h10" stroke-width="3"/><path class="sp" d="M12 100v8M8 104h8" stroke-width="3"/>'
 +'<g stroke="'+U[0]+'" stroke-width="3"><path d="M96 30l5-6M102 40l7-3M8 84l-4-6"/></g></svg>'})();
''' + OLD
edit(P, OLD, NEW, 'rk1: repainted welcome rocket')
