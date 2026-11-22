"""Rk2: static/index.html. The other site cartoons (mail, wait, coin, paid, phone, ok, push, yay, lock, off, cx, doc, shield, cookie, sleep, plug) get the same look as the rocket: bright flat fills, darker shade peeking out, fills shifted off a thick violet outline, same new character. Their animations (check draw, lock lift, banner, pins, waves, confetti, shield, zzz, plug) keep their class names and still run."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
OLD = '''var ILM={plug:"plug",doc:"doc",cookie:"cookie",guard:"shield",lock:"lock",sleep:"sleep",rocket:"rocket"};'''
NEW = r'''/* rk2: the other cartoons, repainted like the rocket */
(function(){var G=['#5BE38E','#2FB864'],S=['#56B6FF','#2F86E0'],U=['#FFD43B','#F0A800'],B=['#FF6B72','#E0444F'],W=['#FFFFFF','#DCD6FF'],K='#7F61F5';
function sh(s,m){var c=s[1],f=m==='l'?'none':c[m==='h'?1:0],a=m==='l'?' stroke="'+K+'" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"':' stroke="none"';return '<'+s[0]+' fill="'+f+'"'+a+'/>'}
function seq(a){var o='';a.forEach(function(s){o+=sh(s,'h')+'<g transform="translate(3.5 -3.5)">'+sh(s,'f')+'</g>'+sh(s,'l')});return o}
function ln(d,w,c,cl,x){return '<path'+(cl?' class="'+cl+'"':'')+' d="'+d+'" fill="none" stroke="'+(c||K)+'" stroke-width="'+(w||3.5)+'" stroke-linecap="round" stroke-linejoin="round"'+(x||'')+'/>'}
function sp(d){return '<path class="sp" d="'+d+'" stroke-width="3"/>'}
var TK='<g stroke="#FFD43B" stroke-width="3" stroke-linecap="round"><path d="M96 14l5-6M102 24l7-3"/></g>';
var CH=[['path d="M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18"',S],['path d="M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z"',W],['path d="M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z"',U]];
function il(p){return '<svg class="ill2" viewBox="0 0 240 170" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+ln('M114 146c-14 4-26 2-38-4',4)+p+'<g transform="translate(112 40)">'+seq(CH)+ln('M60 47q6 5 12 0')+'</g></svg>'}
function bd(x,y,c,i){return '<g transform="translate('+x+' '+y+')">'+seq([['circle r="14"',c]])+i+'</g>'}
var CK=ln('M-6 .5l4.2 4.2 8.2-9.6',3.5,'#fff'),CX=ln('M-5-5l10 10M5-5l-10 10',3.5,'#fff');
var COIN='<g transform="translate(18 44)">'+seq([['ellipse cx="30" cy="48" rx="28" ry="9"',U],['ellipse cx="30" cy="36" rx="28" ry="9"',U],['ellipse cx="30" cy="24" rx="28" ry="9"',U]])+ln('M30 20v8')+'</g>';
var PH='<g transform="translate(14 22)">'+seq([['rect width="58" height="96" rx="11"',W]]);
IL2.mail=il('<g transform="translate(14 28)">'+seq([['rect width="76" height="52" rx="8"',S],['path d="M4 10L38 34L72 10z"',W]])+ln('M4 10L38 34L72 10')+'</g>'+TK);
IL2.wait=il('<g transform="translate(22 22)">'+seq([['circle cx="34" cy="34" r="30"',S],['circle cx="34" cy="34" r="21"',W]])+ln('M34 20v14l10 7')+'</g>'+TK);
IL2.coin=il(COIN+TK);
IL2.paid=il(COIN+bd(80,46,G,CK)+TK);
IL2.cx=il(COIN+bd(80,46,B,CX)+TK);
IL2.phone=il(PH+seq([['rect x="9" y="24" width="40" height="28" rx="7"',S]])+ln('M22 10h14')+ln('M12 31l17 11 17-11',3.5,'#fff')+'</g>'+TK);
IL2.ok=il('<g transform="translate(22 26)">'+seq([['circle cx="40" cy="40" r="36"',G]])+ln('M26 41l10 10.5 19-23',6,'#fff','ckd')+'</g>'+sp('M14 24v10M9 29h10')+sp('M96 18v8M92 22h8')+sp('M100 96v8M96 100h8'));
IL2.push=il(PH+seq([['rect x="9" y="22" width="40" height="30" rx="7"',S]])+ln('M22 10h14')+'<rect class="bn" x="13" y="26" width="32" height="10" rx="4" style="fill:#FFD43B"/>'+[15,25,35,45].map(function(x,i){return '<circle class="pin" cx="'+x+'" cy="72" r="3.6" style="fill:#5BE38E;stroke:none;animation-delay:'+(0.5+i*0.5)+'s"/>'}).join('')+'<path class="wv" d="M20 14q9-8 18 0" style="animation-delay:0s"/><path class="wv" d="M14 8q15-14 30 0" style="animation-delay:.25s"/><path class="wv" d="M8 2q21-20 42 0" style="animation-delay:.5s"/></g>'+TK);
IL2.yay=il(COIN+bd(80,46,G,CK)+[[20,6,7,'#5BE38E',0],[58,0,6,'#56B6FF',.5],[128,2,7,'#FF6B72',.3],[196,4,6,'#FFD43B',.7]].map(function(c){return '<rect class="cf" x="'+c[0]+'" y="'+c[1]+'" width="'+c[2]+'" height="'+c[2]+'" rx="2" style="fill:'+c[3]+';animation-delay:'+c[4]+'s"/>'}).join('')+'<circle class="cf" cx="96" cy="8" r="3.5" style="fill:#FFD43B;animation-delay:.9s"/><circle class="cf" cx="166" cy="10" r="3.5" style="fill:#5BE38E;animation-delay:1.2s"/>'+sp('M184 40v10M179 45h10'));
IL2.lock=il('<g transform="translate(26 24)">'+ln('M14 30v-9a16 16 0 0 1 32 0v9',5,K,'lk')+seq([['rect y="30" width="60" height="46" rx="9"',U],['circle cx="30" cy="52" r="5"',B]])+ln('M30 56v9')+'</g>'+sp('M100 28v10M95 33h10')+sp('M14 104v8M10 108h8'));
IL2.off=il('<g class="wf">'+ln('M16 70q36-34 72 0',5,S[1])+ln('M30 84q22-20 44 0',5,S[1])+ln('M44 98q8-8 16 0',5,S[1])+'</g>'+seq([['circle cx="52" cy="110" r="4.5"',S]])+ln('M22 28L84 124',5,'#FF6B72','sl')+TK);
IL2.doc=il('<g transform="translate(20 24)">'+seq([['rect width="66" height="88" rx="9"',W],['circle cx="48" cy="72" r="10"',G]])+ln('M14 24h38M14 40h38M14 56h24')+ln('M43 72l3.5 3.5 6.5-7.5',3.5,'#fff')+'</g>'+TK);
IL2.shield=il('<g transform="translate(22 24)"><g class="sh">'+seq([['path d="M32 0l32 11v27c0 23-15 38-32 46C15 76 0 61 0 38V11z"',S]])+'</g>'+seq([['circle cx="32" cy="36" r="8"',W]])+ln('M32 44v13')+'</g>'+sp('M100 30v10M95 35h10')+sp('M14 104v8M10 108h8'));
IL2.cookie=il('<g transform="translate(16 28)">'+seq([['path d="M44 0a44 44 0 1 0 44 46 15 15 0 0 1-17-17A15 15 0 0 1 44 0z"',U]])+'<g fill="'+B[1]+'" stroke="none"><circle cx="28" cy="32" r="4"/><circle cx="48" cy="58" r="4"/><circle cx="26" cy="62" r="3.5"/><circle cx="58" cy="40" r="3.5"/></g></g>'+TK);
IL2.sleep=il('<g transform="translate(22 30)">'+seq([['path d="M46 2a38 38 0 1 0 24 54A32 32 0 0 1 46 2z"',U]])+ln('M64 4h16L64 22h16',3.5,K,'zz')+ln('M80 28h12L80 42h12',3.5,K,'zz z2')+'</g>'+sp('M14 28v8M10 32h8')+sp('M104 108v8M100 112h8'));
IL2.plug=il('<g transform="translate(8 44)">'+seq([['rect x="58" y="10" width="36" height="56" rx="10"',W]])+ln('M70 30v12M82 30v12')+'<g class="pg">'+ln('M14 38c-9 0-12 22-6 42',5)+seq([['rect x="14" y="16" width="36" height="44" rx="10"',S]])+ln('M50 28h8M50 48h8')+'</g></g>'+bd(118,38,G,CK)+sp('M78 30v10M73 35h10')+sp('M30 24v8M26 28h8'));
})();
''' + OLD
edit(P, OLD, NEW, 'rk2: the other cartoons, repainted')
