"""Анимированный Reels Legal.Lab.Ai: текст появляется по словам под голос, сцены-«макеты» по шагам,
маскот-ведущая реагирует на каждый шаг, трекер шагов, фоновая музыка.

python3 tools/make_motion_reel.py <папка_рилс>

В папке: spec.json, words_raw.json ([слово, start_ms(, end_ms)] по исходной озвучке), narration.wav
(уже ускоренная в spec.tempo раз). Время в spec (start, cues) — в мс исходной озвучки, движок сам делит на tempo.
Выход: reel.mp4 (1080x1920, 30 fps), cover.jpg.
"""
import asyncio, json, os, subprocess, sys, base64, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
from music_ambient import compose

FPS = 30
LEAD = 0.35  # пауза перед голосом, с


def uri(p):
    full = p if os.path.isabs(p) else os.path.join(ROOT, p)
    ext = "png" if full.lower().endswith(".png") else "jpeg"
    return f"data:image/{ext};base64," + base64.b64encode(open(full, "rb").read()).decode()


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#f4ecdc;--ink:#0f2a22;--g:#1f4a3b;--gold:#b8862e;--gold2:#d9b56a;--paper:#fffaf0;--red:#c2412d;--water:#4f87ad}
body{width:1080px;height:1920px;overflow:hidden;background:var(--bg);font-family:Inter,sans-serif;color:var(--ink)}
#grain{position:absolute;inset:0;opacity:.10;pointer-events:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.06 0 0 0 0 0.16 0 0 0 0 0.13 0 0 0 .9 0'/></filter><rect width='300' height='300' filter='url(%23n)'/></svg>");z-index:50}
#vign{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 40%,rgba(0,0,0,0) 55%,rgba(60,40,10,.13) 100%);z-index:49}
.lbl{position:absolute;left:76px;top:150px;font:500 26px 'DejaVu Sans Mono',monospace;color:rgba(15,42,34,.55);letter-spacing:.02em}
.brand{position:absolute;right:76px;top:146px;font:700 24px Inter;letter-spacing:.22em;color:rgba(15,42,34,.5)}
#cap{position:absolute;left:76px;top:206px;width:928px;font:700 68px/1.13 Inter;letter-spacing:-.01em}
#cap span{display:inline-block;margin-right:.24em;transform-origin:50% 80%}
#cap .k{font-family:Caladea,'DejaVu Serif',serif;font-style:italic;font-weight:700;color:var(--gold);font-size:1.08em}
#stage{position:absolute;left:0;top:560px;width:1080px;height:720px}
.sc{position:absolute;inset:0}
#masc{position:absolute;right:-10px;bottom:0;height:740px;transform-origin:70% 100%;z-index:20;filter:drop-shadow(-14px 10px 24px rgba(40,30,10,.22))}
#masc2{position:absolute;right:-10px;bottom:0;height:740px;transform-origin:70% 100%;z-index:19;filter:drop-shadow(-14px 10px 24px rgba(40,30,10,.22))}
#trk{position:absolute;left:60px;top:1318px;width:470px;z-index:15}
.ch{display:flex;align-items:center;gap:18px;height:84px;margin-bottom:14px;padding:0 22px;background:var(--paper);border-radius:18px;box-shadow:0 6px 0 rgba(15,42,34,.10),0 10px 26px rgba(15,42,34,.08);font:600 34px Inter;color:rgba(15,42,34,.42);border:2px solid rgba(15,42,34,.08);transform-origin:0 50%}
.ch b{display:flex;align-items:center;justify-content:center;width:52px;height:52px;border-radius:12px;background:rgba(15,42,34,.12);color:#fff;font:800 30px Inter}
.ch.on{color:var(--ink);border-color:var(--gold);}
.ch.on b{background:var(--gold)}
.ch.done{color:rgba(15,42,34,.72)}
.ch.done b{background:var(--g)}
.ch i{margin-left:auto;font-style:normal;font-weight:800;color:var(--g);font-size:34px}
.card{position:absolute;background:var(--paper);border-radius:28px;box-shadow:0 10px 0 rgba(15,42,34,.08),0 24px 60px rgba(15,42,34,.16);border:2px solid rgba(15,42,34,.08)}
.big{font:900 200px/1 Inter;color:var(--ink)}
.tag{position:absolute;padding:14px 26px;border-radius:999px;font:700 36px Inter;background:var(--ink);color:var(--gold2);white-space:nowrap}
.stamp{position:absolute;border:8px solid var(--red);color:var(--red);font:900 92px/1 Inter;padding:18px 34px;border-radius:16px;letter-spacing:.02em;background:rgba(255,250,240,.9)}
.line{height:18px;border-radius:9px;background:rgba(15,42,34,.13);margin:22px 0}
.mono{font-family:'DejaVu Sans Mono',monospace}
.numtile{position:absolute;left:50%;top:50%;width:300px;height:300px;margin:-150px 0 0 -150px;background:var(--ink);border-radius:56px;color:#fff;display:flex;align-items:center;justify-content:center;font:900 210px Inter;box-shadow:0 14px 0 rgba(0,0,0,.18)}
.numring{position:absolute;left:50%;top:50%;width:460px;height:460px;margin:-230px 0 0 -230px;border:4px solid var(--gold);border-radius:50%}
.dots{position:absolute;bottom:34px;left:0;right:0;display:flex;justify-content:center;gap:12px}
.dots u{width:18px;height:18px;border-radius:50%;background:rgba(255,255,255,.3)}
.dots u.a{background:var(--gold2)}
</style></head><body>
<div class="lbl" id="lbl"></div><div class="brand">LEGAL.LAB.AI</div>
<div id="cap"></div>
<div id="stage"></div>
<div id="trk"></div>
<img id="masc2"><img id="masc">
<div id="vign"></div><div id="grain"></div>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const cl = (x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const P = (t,a,d=.35)=>cl((t-a)/d);
const eo = x=>1-Math.pow(1-x,3);
const back = x=>{const c=1.9;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const pop = (t,a,d=.4)=>back(P(t,a,d));
function sty(el,o){for(const k in o) el.style[k]=o[k]}

// ---------- сцены ----------
const SC = {};
function numIntro(t,s){ // крупная цифра шага в первые ~0.9 с
  const x=t-s.start; if(!s.step||x>1.0) return '';
  const a=pop(t,s.start,.35), out=P(t,s.start+.75,.25);
  let dots='';for(let i=1;i<=5;i++)dots+=`<u class="${i<=s.step?'a':''}"></u>`;
  return `<div class="numring" style="transform:scale(${.6+.5*eo(P(t,s.start,.6))});opacity:${(1-P(t,s.start+.2,.7))*(1-out)}"></div>
  <div class="numtile" style="transform:scale(${a*(1-out*.4)}) rotate(${(1-a)*-12}deg);opacity:${1-out}">${s.step}<div class="dots">${dots}</div></div>`;
}
const C=(s,k)=>s.cues[k];
const late=(t,s)=>P(t,s.start+.9,.35); // контент шага после цифры

SC.hook=(t,s)=>{
  let h='';
  // потолок с пятном
  const st=eo(P(t,.2,3.5));
  h+=`<div class="card" style="left:70px;top:20px;width:940px;height:300px;overflow:hidden;background:#efe4cc">
   <div style="position:absolute;left:0;right:0;top:0;height:40px;background:#e4d6b8"></div>
   <div style="position:absolute;left:${470-220*st}px;top:${-60}px;width:${440*st}px;height:${300*st}px;border-radius:50%;background:radial-gradient(ellipse at 50% 30%,rgba(110,95,60,.55),rgba(140,120,70,.25) 60%,rgba(140,120,70,0) 72%)"></div>
   <div class="mono" style="position:absolute;left:28px;bottom:22px;font-size:26px;color:rgba(15,42,34,.5)">потолок · ваша кухня</div></div>`;
  // капли
  for(let i=0;i<6;i++){const per=1.1,off=i*0.37,ph=((t+off)%per)/per,x=420+((i*97)%220);
    const y=300+ph*300; h+=`<div style="position:absolute;left:${x}px;top:${y}px;width:26px;height:36px;border-radius:50% 50% 50% 50%/60% 60% 40% 40%;background:var(--water);opacity:${(1-ph)*.9*cl(t/0.4)}"></div>`}
  // лужа
  const pw=200+60*Math.sin(t*2);
  h+=`<div style="position:absolute;left:${530-pw}px;top:640px;width:${pw*2}px;height:60px;border-radius:50%;background:rgba(79,135,173,.35)"></div>`;
  // штамп
  const a=pop(t,C(s,'stamp'),.3), ga=1-P(t,C(s,'steps')-.1,.3);
  h+=`<div class="stamp" style="left:240px;top:360px;transform:scale(${2-a}) rotate(-8deg);opacity:${P(t,C(s,'stamp'),.12)*ga}">ЗАЛИЛИ?!</div>`;
  // 5 шагов
  const b=pop(t,C(s,'steps'),.45);
  h+=`<div class="card" style="left:140px;top:340px;width:800px;height:300px;display:flex;align-items:center;gap:30px;padding:0 50px;transform:scale(${b}) rotate(${(1-b)*6}deg);opacity:${P(t,C(s,'steps'),.15)}">
   <div class="big" style="color:var(--gold)">5</div><div style="font:800 76px/1.05 Inter">шагов<br><span style="font:600 40px Inter;color:rgba(15,42,34,.6)">чтобы вам возместили</span></div></div>`;
  return h;
};
SC.phone=(t,s)=>{
  let h=numIntro(t,s); const L=late(t,s); if(!L) return h;
  const ph=eo(L);
  const rec=t>=C(s,'rec'), tc=Math.max(0,t-C(s,'rec'));
  h+=`<div style="position:absolute;left:${110}px;top:${10+60*(1-ph)}px;width:380px;height:700px;border-radius:56px;background:#111a17;padding:22px;opacity:${L};box-shadow:0 30px 60px rgba(0,0,0,.25)">
   <div style="position:relative;width:100%;height:100%;border-radius:38px;overflow:hidden;background:linear-gradient(#e9dcc0,#d8c6a2)">
    <div style="position:absolute;left:60px;top:90px;width:220px;height:150px;border-radius:50%;background:radial-gradient(rgba(110,95,60,.6),rgba(110,95,60,0) 70%);transform:scale(${1+.04*Math.sin(t*3)})"></div>
    <div style="position:absolute;left:20px;right:20px;top:300px;height:2px;background:rgba(255,255,255,.6)"></div>
    <div style="position:absolute;left:30px;bottom:120px;width:120px;height:160px;background:rgba(60,40,20,.35);border-radius:8px"></div>
    <div style="position:absolute;right:30px;bottom:120px;width:150px;height:100px;background:rgba(60,40,20,.28);border-radius:8px"></div>
    <div style="position:absolute;inset:16px;border:3px solid rgba(255,255,255,.75);border-radius:26px"></div>
    <div class="mono" style="position:absolute;top:34px;left:0;right:0;text-align:center;color:#fff;font-size:28px;font-weight:700;text-shadow:0 1px 4px rgba(0,0,0,.4)">${rec?`<span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#e33;opacity:${Math.sin(t*8)>0?1:.25};margin-right:10px"></span>REC 00:0${Math.floor(tc)}`:'ВИДЕО'}</div>
    <div style="position:absolute;bottom:30px;left:50%;margin-left:-46px;width:92px;height:92px;border-radius:50%;border:7px solid #fff;background:${rec?'#e33':'rgba(255,255,255,.3)'};transform:scale(${rec?1-.12*Math.max(0,1-tc*4):1})"></div>
   </div></div>`;
  const items=[['Кран перекрыт','tap'],['Потолок','c1'],['Стены','c2'],['Мебель','c3']];
  items.forEach(([n,c],i)=>{const a=P(t,C(s,c),.3), on=a>0;
    h+=`<div class="ch ${on?'on':''}" style="position:absolute;left:540px;top:${60+i*120}px;width:440px;transform:translateX(${(1-eo(P(t,s.start+1+i*.12,.4)))*80}px);opacity:${P(t,s.start+1+i*.12,.3)}">
     <b style="background:${on?'var(--g)':''}">${on?'✓':i+1}</b>${n}</div>`});
  return h;
};
SC.act=(t,s)=>{
  let h=numIntro(t,s); const L=late(t,s); if(!L) return h;
  const c=pop(t,C(s,'call'),.4);
  h+=`<div class="card" style="left:80px;top:0;width:560px;height:150px;display:flex;align-items:center;gap:22px;padding:0 30px;transform:scale(${c});opacity:${P(t,C(s,'call'),.15)*(1-P(t,C(s,'doc'),.3)*.55)}">
   <div style="width:90px;height:90px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;color:#fff;font:800 44px Inter;transform:rotate(${Math.sin(t*20)*8}deg)">☎</div>
   <div><div style="font:800 40px Inter">Аварийная служба</div><div class="mono" style="font-size:26px;color:rgba(15,42,34,.55)">вызов · ${Math.floor(Math.max(0,t-C(s,'call'))*1.7)} сек</div></div></div>`;
  const d=eo(P(t,C(s,'doc'),.5)), lw=P(t,C(s,'doc')+.3,1.6);
  h+=`<div class="card" style="left:150px;top:${120+80*(1-d)}px;width:520px;height:600px;padding:48px 46px;opacity:${P(t,C(s,'doc'),.2)};transform:rotate(${-3+3*d}deg)">
   <div style="font:900 50px Inter;letter-spacing:.06em">АКТ</div><div style="font:600 32px Inter;color:rgba(15,42,34,.6);margin-top:6px">о заливе квартиры</div>
   ${['Дата и время','Причина залива','Что повреждено','Подписи'].map((n,i)=>`<div style="margin-top:26px"><div class="mono" style="font-size:22px;color:rgba(15,42,34,.5)">${n}</div><div class="line" style="width:${cl(lw*4-i)*100}%;margin:10px 0 0;background:rgba(15,42,34,.22)"></div></div>`).join('')}
  </div>`;
  const r=pop(t,C(s,'riser'),.4);
  h+=`<div class="tag" style="left:700px;top:180px;transform:scale(${r});opacity:${P(t,C(s,'riser'),.15)}">общий стояк</div>`;
  const k=pop(t,C(s,'clock'),.45), ang=Math.max(0,t-C(s,'clock'))*240;
  h+=`<div style="position:absolute;left:740px;top:290px;width:220px;height:220px;border-radius:50%;background:var(--ink);transform:scale(${k});opacity:${P(t,C(s,'clock'),.15)};box-shadow:0 14px 0 rgba(0,0,0,.15)">
    ${[0,1,2,3,4,5,6,7,8,9,10,11].map(i=>`<div style="position:absolute;left:107px;top:14px;width:6px;height:16px;background:rgba(255,255,255,.5);transform-origin:3px 96px;transform:rotate(${i*30}deg)"></div>`).join('')}
    <div style="position:absolute;left:105px;top:36px;width:10px;height:74px;background:var(--gold2);border-radius:5px;transform-origin:50% 100%;transform:rotate(${ang}deg)"></div>
    <div style="position:absolute;left:98px;top:98px;width:24px;height:24px;border-radius:50%;background:var(--gold2)"></div></div>
   <div class="tag" style="left:712px;top:540px;font-size:44px;transform:scale(${pop(t,C(s,'clock')+.25,.4)});opacity:${P(t,C(s,'clock')+.25,.12)}">≤ 12 часов</div>`;
  return h;
};
SC.split=(t,s)=>{
  let h=numIntro(t,s); const L=late(t,s); if(!L) return h;
  const q=pop(t,C(s,'q'),.4);
  h+=`<div style="position:absolute;left:0;right:0;top:0;text-align:center;font:900 96px Inter;transform:scale(${q});opacity:${P(t,C(s,'q'),.15)}">Чья труба<span style="color:var(--gold)">?</span></div>`;
  const side=(x,cue,title,who,sub)=>{const a=pop(t,C(s,cue),.45),on=P(t,C(s,cue),.15);
    return `<div class="card" style="left:${x}px;top:170px;width:440px;height:520px;padding:40px 36px;transform:translateY(${(1-a)*80}px) scale(${.9+.1*a});opacity:${on}">
     <div style="height:150px;position:relative">
      <div style="position:absolute;left:40px;top:60px;width:300px;height:44px;background:#8aa0a8;border-radius:22px"></div>
      <div style="position:absolute;left:${cue=='left'?250:170}px;top:30px;width:44px;height:120px;background:#8aa0a8;border-radius:22px"></div>
      ${[0,1,2].map(i=>{const ph=((t*1.3+i*.33)%1);return `<div style="position:absolute;left:${cue=='left'?262:182}px;top:${100+ph*60}px;width:20px;height:28px;border-radius:50%;background:var(--water);opacity:${1-ph}"></div>`}).join('')}
     </div>
     <div style="font:700 40px Inter;margin-top:20px">${title}</div>
     <div style="font:600 30px Inter;color:rgba(15,42,34,.55);margin-top:28px">платит</div>
     <div style="font:900 ${who.length>12?50:76}px/1.05 Inter;color:var(--gold);margin-top:6px">${who}</div>
     <div class="mono" style="font-size:22px;color:rgba(15,42,34,.5);margin-top:16px">${sub}</div></div>`};
  h+=side(70,'left','Труба соседа','сосед','ст. 210, 1064 ГК РФ');
  h+=side(570,'right','Общий стояк','управляющая компания','ст. 1064 ГК РФ');
  return h;
};
SC.estimate=(t,s)=>{
  let h=numIntro(t,s); const L=late(t,s); if(!L) return h;
  const r=eo(P(t,C(s,'report'),.5)), lw=P(t,C(s,'report')+.2,1.4);
  h+=`<div class="card" style="left:80px;top:${30+70*(1-r)}px;width:520px;height:640px;padding:46px;opacity:${P(t,C(s,'report'),.2)};transform:rotate(${2-2*r}deg)">
    <div style="font:900 44px Inter">Отчёт об оценке</div><div style="font:600 30px Inter;color:rgba(15,42,34,.55);margin:6px 0 20px">ущерба от залива</div>
    ${['Потолок','Обои','Пол','Мебель'].map((n,i)=>{const a=cl(lw*4-i);return `<div style="display:flex;align-items:center;gap:16px;margin-top:22px;opacity:${.25+.75*a}"><b style="width:40px;height:40px;border-radius:10px;background:${a>=1?'var(--g)':'rgba(15,42,34,.14)'};color:#fff;display:flex;align-items:center;justify-content:center;font:800 26px Inter">${a>=1?'✓':''}</b><span style="font:600 36px Inter">${n}</span><span style="margin-left:auto;height:16px;width:${110*a}px;border-radius:8px;background:rgba(15,42,34,.18)"></span></div>`}).join('')}
    <div style="position:absolute;left:46px;right:46px;bottom:46px;border-top:3px dashed rgba(15,42,34,.2);padding-top:22px;font:800 40px Inter">Итого: <span style="color:var(--gold)">₽ ${'•'.repeat(1+Math.floor(lw*5)%6)}</span></div></div>`;
  const e=P(t,C(s,'letter'),.6), ee=eo(e);
  h+=`<div style="position:absolute;left:${620+300*(1-ee)}px;top:${200-120*(1-ee)}px;width:400px;height:280px;transform:rotate(${(1-ee)*25-6}deg);opacity:${P(t,C(s,'letter'),.15)}">
    <div class="card" style="inset:0;background:#f1dfb6"></div>
    <div style="position:absolute;left:0;top:0;width:0;height:0;border-left:200px solid transparent;border-right:200px solid transparent;border-top:150px solid #e6cf9b"></div>
    <div style="position:absolute;left:50%;top:118px;margin-left:-34px;width:68px;height:68px;border-radius:50%;background:var(--red)"></div>
    <div style="position:absolute;left:0;right:0;bottom:24px;text-align:center;font:800 30px Inter">Приглашение на осмотр</div></div>`;
  const w=pop(t,C(s,'letter')+.5,.4);
  h+=`<div class="tag" style="left:660px;top:520px;transform:scale(${w}) rotate(-4deg);opacity:${P(t,C(s,'letter')+.5,.12)}">письменно!</div>`;
  return h;
};
SC.court=(t,s)=>{
  let h=numIntro(t,s); const L=late(t,s); if(!L) return h;
  const a=pop(t,C(s,'claim'),.45);
  h+=`<div class="card" style="left:70px;top:40px;width:400px;height:480px;padding:40px;transform:scale(${a}) rotate(${(1-a)*-8}deg);opacity:${P(t,C(s,'claim'),.15)}">
    <div style="font:900 46px Inter">ПРЕТЕНЗИЯ</div><div class="line" style="width:90%"></div><div class="line" style="width:75%"></div><div class="line" style="width:85%"></div><div class="line" style="width:50%"></div>
    <div style="position:absolute;right:30px;bottom:30px;font:italic 700 40px Caladea,serif;color:var(--g)">подпись</div></div>`;
  const ar=P(t,C(s,'court')-.4,.4);
  h+=`<div style="position:absolute;left:480px;top:250px;width:${100*ar}px;height:12px;background:var(--ink);border-radius:6px"></div><div style="position:absolute;left:${560}px;top:232px;width:0;height:0;border-top:24px solid transparent;border-bottom:24px solid transparent;border-left:36px solid var(--ink);opacity:${ar>=1?1:0}"></div>`;
  const c=pop(t,C(s,'court'),.45);
  h+=`<div class="card" style="left:620px;top:60px;width:390px;height:440px;transform:scale(${c});opacity:${P(t,C(s,'court'),.15)};background:var(--ink)">
    <div style="position:absolute;left:55px;right:55px;top:60px;height:0;border-left:140px solid transparent;border-right:140px solid transparent;border-bottom:70px solid var(--gold2)"></div>
    ${[0,1,2,3].map(i=>`<div style="position:absolute;left:${80+i*62}px;top:150px;width:34px;height:170px;background:var(--gold2);border-radius:4px"></div>`).join('')}
    <div style="position:absolute;left:60px;right:60px;top:330px;height:24px;background:var(--gold2);border-radius:4px"></div>
    <div style="position:absolute;left:0;right:0;bottom:24px;text-align:center;color:#fff;font:900 52px Inter">СУД</div></div>`;
  const y=pop(t,C(s,'years'),.45);
  h+=`<div class="card" style="left:250px;top:540px;width:580px;height:170px;display:flex;align-items:center;justify-content:center;gap:24px;transform:scale(${y});opacity:${P(t,C(s,'years'),.15)};border:4px solid var(--gold)">
    <div style="font:900 110px/1 Inter;color:var(--gold)">3 года</div><div class="mono" style="font-size:24px;color:rgba(15,42,34,.55);line-height:1.3">срок<br>ст. 196 ГК</div></div>`;
  return h;
};
SC.outro=(t,s)=>{
  let h='';
  const a=pop(t,s.start+.05,.5);
  h+=`<div style="position:absolute;left:390px;top:20px;width:300px;height:380px;transform:scale(${a}) translateY(${Math.sin(t*3)*8}px);">
    <div style="position:absolute;inset:0;background:var(--ink);clip-path:polygon(0 0,100% 0,100% 100%,50% 76%,0 100%);border-radius:10px"></div>
    <div style="position:absolute;left:0;right:0;top:110px;text-align:center;color:var(--gold2);font:900 120px Inter">✓</div></div>`;
  const b=pop(t,s.start+.5,.45);
  h+=`<div style="position:absolute;left:0;right:0;top:440px;text-align:center;transform:scale(${b});opacity:${P(t,s.start+.5,.15)}">
    <div style="font:900 70px Inter">Сохраните</div>
    <div style="font:600 36px Inter;color:rgba(15,42,34,.6);margin-top:14px">помощник — бот в шапке профиля</div></div>`;
  return h;
};

// ---------- кадр ----------
let lastM='';
function render(t){
  // сцена
  let si=0; D.scenes.forEach((s,i)=>{if(t>=s.start-0.05) si=i});
  const s=D.scenes[si];
  const fadeIn=P(t,s.start-.05,.25);
  $('#stage').innerHTML=`<div class="sc" style="opacity:${fadeIn};transform:scale(${1+.025*cl((t-s.start)/6)})">${SC[s.type](t,s)}</div>`;
  $('#lbl').textContent=s.label;
  // подпись по словам
  let fi=0; D.sent.forEach((st,i)=>{if(t>=D.words[st[0]].s-0.08) fi=i});
  const [a,b]=D.sent[fi];
  let cap='';
  for(let i=a;i<=b;i++){const w=D.words[i],x=P(t,w.s-.04,.22),on=t>=w.s-.04;
    cap+=`<span class="${w.k?'k':''}" style="opacity:${on?Math.max(.0,x):0};transform:translateY(${(1-eo(x))*26}px) scale(${w.k?(.8+.2*back(x)):1})">${w.w}</span>`}
  $('#cap').innerHTML=cap;
  // трекер
  const trkOn=P(t,D.trkStart,.4);
  let tk='';
  D.steps.forEach((n,i)=>{const st=i+1; const act=s.step===st, done=(s.step&&st<s.step)||s.type==='outro';
    const ap=eo(P(t,D.trkStart+i*.08,.35));
    tk+=`<div class="ch ${act?'on':''} ${done?'done':''}" style="opacity:${ap*(act||done?1:.85)};transform:translateX(${(1-ap)*-60}px) scale(${act?1+.04*pop(t,s.start,.4):.94})"><b>${st}</b>${n}${done?'<i>✓</i>':''}</div>`});
  $('#trk').innerHTML=tk; $('#trk').style.opacity=trkOn;
  // маскот
  let src=s.mascot, mstart=s.start;
  if(s.mascot2&&t>=s.mascot2.at){src=s.mascot2.src;mstart=s.mascot2.at}
  const m=$('#masc');
  if(m.dataset.src!==src){m.src=D.img[src];m.dataset.src=src}
  const e=pop(t,mstart,.45);
  const bob=Math.sin(t*2.2)*6, tilt=Math.sin(t*1.3)*1.2;
  m.style.transform=`translateY(${(1-e)*140+bob}px) rotate(${tilt}deg) scale(${.96+.04*e})`;
  m.style.opacity=cl((t-mstart)/.12+0.0);
  // предыдущая поза уходит
  const prev=D.mprev(t), m2=$('#masc2');
  if(prev&&t-prev.at<.35){ if(m2.dataset.src!==prev.src){m2.src=D.img[prev.src];m2.dataset.src=prev.src}
    const q=P(t,prev.at,.3); m2.style.opacity=1-q; m2.style.transform=`translateY(${q*120}px)`; } else m2.style.opacity=0;
}
// смены маскота
const MC=[];D.scenes.forEach(s=>{MC.push({at:s.start,src:s.mascot});if(s.mascot2)MC.push({at:s.mascot2.at,src:s.mascot2.src})});
D.mprev=t=>{let r=null;for(let i=1;i<MC.length;i++){if(t>=MC[i].at) r={at:MC[i].at,src:MC[i-1].src}}return r};
window.render=render;
</script></body></html>"""


def build_data(d, spec):
    tempo = spec.get("tempo", 1.0)
    T = lambda ms: LEAD + ms / 1000 / tempo
    raw = json.load(open(f"{d}/words_raw.json"))
    kw = set(spec.get("keywords", []))
    words = [{"w": r[0], "s": T(r[1]), "k": r[0] in kw} for r in raw]
    # фразы: до . ? ! (двоеточие и запятая не режут); длинные режем по ~7 слов
    sent, st = [], 0
    for i, r in enumerate(raw):
        end = r[0].endswith((".", "?", "!"))
        if end or i == len(raw) - 1 or (i - st >= 7 and r[0].endswith((",", "—", ":"))):
            sent.append([st, i]); st = i + 1
    scenes = []
    for s in spec["scenes"]:
        s = dict(s); s["start"] = T(s["start"]) if s["start"] else 0
        s["cues"] = {k: T(v) for k, v in s.get("cues", {}).items()}
        if s.get("mascot2"): s["mascot2"] = {"at": T(s["mascot2"]["at"]), "src": s["mascot2"]["src"]}
        scenes.append(s)
    imgs = {}
    for s in scenes:
        for p in [s["mascot"]] + ([s["mascot2"]["src"]] if s.get("mascot2") else []):
            imgs[p] = uri(p)
    trk = scenes[0]["cues"].get("steps", scenes[1]["start"])
    return {"words": words, "sent": sent, "scenes": scenes, "steps": spec["steps"], "img": imgs, "trkStart": trk}


async def render_frames(html, n, fdir, cover_t):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        await pg.set_content(html)
        await pg.wait_for_timeout(300)
        for i in range(n):
            await pg.evaluate(f"render({i / FPS})")
            await pg.screenshot(path=f"{fdir}/f{i:05d}.jpg", type="jpeg", quality=90)
        await pg.evaluate(f"render({cover_t})")
        await pg.screenshot(path=f"{fdir}/../cover.jpg", type="jpeg", quality=92)
        await b.close()


def main(d):
    spec = json.load(open(f"{d}/spec.json"))
    data = build_data(d, spec)
    voice = f"{d}/narration.wav"
    vd = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice]).decode())
    total = LEAD + vd + 1.6
    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    open(f"{d}/_preview.html", "w").write(html)
    fdir = f"{d}/frames"
    shutil.rmtree(fdir, ignore_errors=True); os.makedirs(fdir)
    n = int(total * FPS)
    asyncio.run(render_frames(html, n, fdir, spec.get("cover_t", 4.6)))
    compose(f"{d}/music.wav", total + 1, seed=spec.get("seed", 1))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{fdir}/f%05d.jpg",
                    "-i", f"{d}/music.wav", "-i", voice, "-filter_complex",
                    f"[1:a]volume=0.13[mu];[2:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},aformat=channel_layouts=stereo,volume=1.05[vo];"
                    f"[mu][vo]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={total - 1.5:.2f}:d=1.5[a]",
                    "-map", "0:v", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", f"{d}/reel.mp4"], check=True)
    print(f"{d}/reel.mp4", f"{total:.1f}s", n, "frames")


if __name__ == "__main__":
    main(sys.argv[1])
