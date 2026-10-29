"""Анимированный Reels Legal.Lab.Ai (формат «по шагам», как у пилота 28.10 про залив).

python3 tools/make_motion_reel.py <папка_рилс>

В папке: spec.json, words_raw.json (tools/align_words.py), narration.wav (озвучка, уже ускоренная в spec.tempo раз).
Выход: reel.mp4 (1080x1920, 30 fps), cover.jpg (обложка в стиле канала, см. spec.cover), preview.jpg (контактный лист кадров каждые 2 с — посмотреть через Read).

Текст на экране = слова озвучки, появляются по одному в момент произнесения; слова из spec.keywords — золотым курсивом.
Сцены сменяются в момент, когда звучит якорь "at". Якорь — слово или короткая фраза из озвучки
(«Шаг второй», «акт», «три»): ищется по порядку, начиная с начала текущей сцены, без учёта регистра и знаков.
Можно дать число — время в мс по исходной озвучке. Не нашёлся якорь — элемент появится через ~1 с после начала сцены
(в консоль пишется WARN).

spec.json:
{
 "tempo": 1.1,                # во сколько раз ускорена narration.wav относительно исходной (для пересчёта таймингов)
 "seed": 28,                  # вариант фоновой музыки
 "cover": {                    # ОБЛОЖКА — в стиле всех обложек канала (тёмно-зелёная, антиква, золотой акцент, золотая плашка)
   "title": "Соседи залили квартиру?",   # крючок, 2–5 слов, белым
   "accent": "5 шагов, чтобы вам возместили",  # вторая строка золотом
   "badge": "Памятка · 5 шагов",          # золотая плашка: рубрика · формат
   "photo": "media/scenes/....jpg", "focus": "30%",   # сцена дня из Canva / фото героини; если нет —
   "pose": "headache"                     # вырезанная героиня (поза из списка ниже) на тёмно-зелёном фоне
 },
 "keywords": ["залили", "акт", "три", "года"],   # слова для выделения (без учёта регистра и знаков)
 "steps": ["Вода и видео", "Акт о заливе", ...],  # подписи трекера шагов (3–5, до 16 символов); без steps трекер скрыт
 "intro_video": "media/avatar/2026-10-30-intro.mp4",   # необязательно: говорящий маскот (Kling) в начале
 "scenes": [ { "type": ..., "at": ..., "label": "// шаг 1 · ...", "step": 1, "mascot": "think_pen",
               "mascot2": {"at": "...", "pose": "idea"}, ...поля типа... }, ... ]
}
"step": N — сцена начинается с крупной цифры шага (0,9 с), трекер подсвечивает шаг N. Без step — без цифры.

Позы маскота (media/mascot/<поза>.png), только эти: headache (проблема, «ну вот»), idea (важно, правило),
think_pen (разберёмся), call (звонки), scales (суд, кто прав), notes (документы, чек-лист),
point_you (это про вас, призыв), coffee_smile (итог, лёгкий тон), books (закон, норма), doubt (подозрительно),
glasses («а теперь внимательно»), handshake (договорились, мировое). Не повторяй одну позу в соседних сценах.

Типы сцен:
 hook      : prop ("drops"|"money"|"phone"|"alert"|"doc"|"none"), prop_label (подпись к картинке),
             stamp {text, at} — красный штамп-вопрос («ЗАЛИЛИ?!»), card {big, text, sub, at} — карточка «5 шагов».
 checklist : device ("phone_rec" — телефон снимает видео | null), title, items [{text, at}] (2–5 пунктов, отмечаются галочкой).
 document  : call {text, sub, at} — входящий/исходящий вызов; doc {title, sub, fields[], checks(bool), at} — документ,
             поля заполняются (checks: true — с галочками); tags [{text, at}] — плашки; timer {text, at} — часы + срок;
             letter {text, at} — конверт («Приглашение на осмотр»); note {text, at} — плашка-акцент («письменно!»).
 compare   : question {text, at}, left и right {title, label, value, foot, at, icon} — две карточки «кто/что»
             (icon: "pipe"|"doc"|"money"|"phone"|"bank"|"court"|"home"|"shield"|"check"|"cross").
 path      : nodes [{title, icon, at}] (2–3 узла со стрелками), badge {text, sub, at} — плашка со сроком/суммой.
 big       : value («3 года», «50 000 ₽»), caption (подпись под цифрой), foot, at_value, icon — одна крупная цифра.
 chat      : contact, messages [{from: "them"|"me", text, at}], stamp {text, at} — переписка в телефоне (мошенники).
 photo     : src (media/photos/…jpg), focus («40%»), caption, credit, at — фото в рамке с медленным наездом.
 outro     : title («Сохраните»), sub («помощник — бот в шапке профиля»), follow («Подпишитесь») + follow_at (якорь) — золотая кнопка-призыв.
spec.cold_open (по умолчанию 1.5 с, 0 — выключить): первые секунды ролика показывают обложку канала (cover.jpg),
затем она растворяется — крючок крупно виден с первого кадра (в ленте и при перелистывании).
keywords — значимые слова (не короче 3 букв; «не», «в» игнорируются). Все тексты в сценах — короткие (2–4 слова на плашку), длинное — в озвучку.
"""
import asyncio, json, os, re, subprocess, sys, base64, shutil, html as _h

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
from music_ambient import compose

FPS = 30
LEAD = 0.35  # пауза перед голосом, с
POSES = ["headache", "idea", "think_pen", "call", "scales", "notes", "point_you", "coffee_smile",
         "books", "doubt", "glasses", "handshake"]


def uri(p):
    full = p if os.path.isabs(p) else os.path.join(ROOT, p)
    ext = "png" if full.lower().endswith(".png") else "jpeg"
    return f"data:image/{ext};base64," + base64.b64encode(open(full, "rb").read()).decode()


def norm(w):
    return re.sub(r"[^0-9a-zа-я]", "", w.lower().replace("ё", "е"))


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
#masc,#masc2{position:absolute;right:-10px;bottom:0;height:740px;transform-origin:70% 100%;filter:drop-shadow(-14px 10px 24px rgba(40,30,10,.22))}
#masc{z-index:20}#masc2{z-index:19}
#trk{position:absolute;left:60px;top:1318px;width:470px;z-index:15}
.ch{display:flex;align-items:center;gap:18px;height:84px;margin-bottom:14px;padding:0 22px;background:var(--paper);border-radius:18px;box-shadow:0 6px 0 rgba(15,42,34,.10),0 10px 26px rgba(15,42,34,.08);font:600 34px Inter;color:rgba(15,42,34,.42);border:2px solid rgba(15,42,34,.08);transform-origin:0 50%;white-space:nowrap;overflow:hidden}
.ch b{flex:none;display:flex;align-items:center;justify-content:center;width:52px;height:52px;border-radius:12px;background:rgba(15,42,34,.12);color:#fff;font:800 30px Inter}
.ch.on{color:var(--ink);border-color:var(--gold)}.ch.on b{background:var(--gold)}
.ch.done{color:rgba(15,42,34,.72)}.ch.done b{background:var(--g)}
.ch i{margin-left:auto;font-style:normal;font-weight:800;color:var(--g);font-size:34px}
.card{position:absolute;background:var(--paper);border-radius:28px;box-shadow:0 10px 0 rgba(15,42,34,.08),0 24px 60px rgba(15,42,34,.16);border:2px solid rgba(15,42,34,.08)}
.tag{position:absolute;padding:14px 26px;border-radius:999px;font:700 36px Inter;background:var(--ink);color:var(--gold2);white-space:nowrap}
.stamp{position:absolute;border:8px solid var(--red);color:var(--red);font:900 88px/1 Inter;padding:18px 34px;border-radius:16px;letter-spacing:.02em;background:rgba(255,250,240,.92);white-space:nowrap}
.line{height:18px;border-radius:9px;background:rgba(15,42,34,.13);margin:22px 0}
.mono{font-family:'DejaVu Sans Mono',monospace}
.numtile{position:absolute;left:50%;top:50%;width:300px;height:300px;margin:-150px 0 0 -150px;background:var(--ink);border-radius:56px;color:#fff;display:flex;align-items:center;justify-content:center;font:900 210px Inter;box-shadow:0 14px 0 rgba(0,0,0,.18)}
.numring{position:absolute;left:50%;top:50%;width:460px;height:460px;margin:-230px 0 0 -230px;border:4px solid var(--gold);border-radius:50%}
.dots{position:absolute;bottom:34px;left:0;right:0;display:flex;justify-content:center;gap:12px}
.dots u{width:18px;height:18px;border-radius:50%;background:rgba(255,255,255,.3)}.dots u.a{background:var(--gold2)}
.ico{position:relative;display:inline-block}
.bub{position:absolute;max-width:300px;padding:18px 22px;border-radius:26px;font:600 28px/1.25 Inter}
</style></head><body>
<div class="lbl" id="lbl"></div><div class="brand">LEGAL.LAB.AI</div>
<div id="cap"></div><div id="stage"></div><div id="trk"></div>
<img id="masc2"><img id="masc"><div id="vign"></div><div id="grain"></div>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const cl=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const P=(t,a,d=.35)=>cl((t-a)/d);
const eo=x=>1-Math.pow(1-x,3);
const back=x=>{const c=1.9;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const pop=(t,a,d=.4)=>back(P(t,a,d));
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const nst=s=>s.step?s.start+.9:s.start; // контент шага после цифры

// ---------- иконки ----------
function icon(k,sz=150,col='var(--ink)',acc='var(--gold2)'){
  const S=sz;
  const box=(inner)=>`<div class="ico" style="width:${S}px;height:${S}px">${inner}</div>`;
  if(k==='court') return box(`<div style="position:absolute;left:${S*.1}px;right:${S*.1}px;top:${S*.06}px;height:0;border-left:${S*.4}px solid transparent;border-right:${S*.4}px solid transparent;border-bottom:${S*.2}px solid ${acc}"></div>${[0,1,2,3].map(i=>`<div style="position:absolute;left:${S*(.17+i*.18)}px;top:${S*.32}px;width:${S*.1}px;height:${S*.42}px;background:${acc};border-radius:3px"></div>`).join('')}<div style="position:absolute;left:${S*.08}px;right:${S*.08}px;top:${S*.78}px;height:${S*.08}px;background:${acc};border-radius:3px"></div>`);
  if(k==='bank') return icon('court',sz,col,acc);
  if(k==='doc') return box(`<div style="position:absolute;left:${S*.18}px;top:${S*.05}px;width:${S*.64}px;height:${S*.9}px;background:#fff;border-radius:${S*.06}px;border:${S*.03}px solid ${col}"></div>${[0,1,2,3].map(i=>`<div style="position:absolute;left:${S*.28}px;top:${S*(.22+i*.16)}px;width:${S*(i==3?.25:.44)}px;height:${S*.06}px;background:${col};opacity:.35;border-radius:3px"></div>`).join('')}`);
  if(k==='money') return box(`${[0,1,2].map(i=>`<div style="position:absolute;left:${S*.15}px;top:${S*(.55-i*.16)}px;width:${S*.7}px;height:${S*.22}px;border-radius:50%;background:${acc};border:${S*.025}px solid ${col}"></div>`).join('')}<div style="position:absolute;left:0;right:0;top:${S*.08}px;text-align:center;font:900 ${S*.32}px Inter;color:${col}">₽</div>`);
  if(k==='phone') return box(`<div style="position:absolute;left:${S*.27}px;top:${S*.04}px;width:${S*.46}px;height:${S*.92}px;border-radius:${S*.1}px;background:${col}"></div><div style="position:absolute;left:${S*.32}px;top:${S*.12}px;width:${S*.36}px;height:${S*.68}px;border-radius:${S*.05}px;background:${acc};opacity:.85"></div>`);
  if(k==='home') return box(`<div style="position:absolute;left:${S*.1}px;top:${S*.08}px;width:0;height:0;border-left:${S*.4}px solid transparent;border-right:${S*.4}px solid transparent;border-bottom:${S*.34}px solid ${col}"></div><div style="position:absolute;left:${S*.2}px;top:${S*.42}px;width:${S*.6}px;height:${S*.48}px;background:${acc}"></div><div style="position:absolute;left:${S*.42}px;top:${S*.6}px;width:${S*.16}px;height:${S*.3}px;background:${col}"></div>`);
  if(k==='shield') return box(`<div style="position:absolute;left:${S*.16}px;top:${S*.05}px;width:${S*.68}px;height:${S*.88}px;background:${col};clip-path:polygon(50% 0,100% 15%,100% 50%,50% 100%,0 50%,0 15%)"></div><div style="position:absolute;left:0;right:0;top:${S*.22}px;text-align:center;font:900 ${S*.4}px Inter;color:${acc}">✓</div>`);
  if(k==='check'||k==='cross') return box(`<div style="position:absolute;inset:${S*.08}px;border-radius:50%;background:${k==='check'?'var(--g)':'var(--red)'}"></div><div style="position:absolute;left:0;right:0;top:${S*.14}px;text-align:center;font:900 ${S*.52}px Inter;color:#fff">${k==='check'?'✓':'✕'}</div>`);
  if(k==='letter') return box(`<div style="position:absolute;left:${S*.05}px;top:${S*.2}px;width:${S*.9}px;height:${S*.6}px;background:#f1dfb6;border-radius:${S*.05}px"></div><div style="position:absolute;left:${S*.05}px;top:${S*.2}px;width:0;height:0;border-left:${S*.45}px solid transparent;border-right:${S*.45}px solid transparent;border-top:${S*.32}px solid #e2c88f"></div><div style="position:absolute;left:${S*.42}px;top:${S*.42}px;width:${S*.16}px;height:${S*.16}px;border-radius:50%;background:var(--red)"></div>`);
  // pipe
  return box(`<div style="position:absolute;left:${S*.05}px;top:${S*.3}px;width:${S*.9}px;height:${S*.18}px;background:#8aa0a8;border-radius:${S*.09}px"></div><div style="position:absolute;left:${S*.6}px;top:${S*.1}px;width:${S*.18}px;height:${S*.5}px;background:#8aa0a8;border-radius:${S*.09}px"></div>${[0,1,2].map(i=>{const ph=((D.t*1.3+i*.33)%1);return `<div style="position:absolute;left:${S*.64}px;top:${S*(.6+ph*.3)}px;width:${S*.1}px;height:${S*.13}px;border-radius:50%;background:var(--water);opacity:${1-ph}"></div>`}).join('')}`);
}

// ---------- сцены ----------
const SC={};
function numIntro(t,s){
  const x=t-s.start; if(!s.step||x>1.0) return '';
  const a=pop(t,s.start,.35), out=P(t,s.start+.75,.25);
  let dots='';for(let i=1;i<=(D.steps.length||5);i++)dots+=`<u class="${i<=s.step?'a':''}"></u>`;
  return `<div class="numring" style="transform:scale(${.6+.5*eo(P(t,s.start,.6))});opacity:${(1-P(t,s.start+.2,.7))*(1-out)}"></div>
  <div class="numtile" style="transform:scale(${a*(1-out*.4)}) rotate(${(1-a)*-12}deg);opacity:${1-out}">${s.step}<div class="dots">${dots}</div></div>`;
}
const vis=(t,a,d=.15)=>P(t,a,d);

SC.hook=(t,s)=>{
  let h='';const pr=s.prop||'drops';
  if(pr==='drops'){
    const st=eo(P(t,s.start+.2,3.5));
    h+=`<div class="card" style="left:70px;top:20px;width:940px;height:300px;overflow:hidden;background:#efe4cc">
     <div style="position:absolute;left:0;right:0;top:0;height:40px;background:#e4d6b8"></div>
     <div style="position:absolute;left:${470-220*st}px;top:-60px;width:${440*st}px;height:${300*st}px;border-radius:50%;background:radial-gradient(ellipse at 50% 30%,rgba(110,95,60,.55),rgba(140,120,70,.25) 60%,rgba(140,120,70,0) 72%)"></div>
     <div class="mono" style="position:absolute;left:28px;bottom:22px;font-size:26px;color:rgba(15,42,34,.5)">${esc(s.prop_label||'')}</div></div>`;
    for(let i=0;i<6;i++){const ph=((t+i*.37)%1.1)/1.1,x=420+((i*97)%220);
      h+=`<div style="position:absolute;left:${x}px;top:${300+ph*300}px;width:26px;height:36px;border-radius:50% 50% 50% 50%/60% 60% 40% 40%;background:var(--water);opacity:${(1-ph)*.9*cl((t-s.start)/.4)}"></div>`}
    const pw=200+60*Math.sin(t*2);
    h+=`<div style="position:absolute;left:${530-pw}px;top:640px;width:${pw*2}px;height:60px;border-radius:50%;background:rgba(79,135,173,.35)"></div>`;
  } else if(pr==='money'){
    for(let i=0;i<9;i++){const ph=((t*.8+i*.23)%1),x=120+((i*131)%820);
      h+=`<div style="position:absolute;left:${x}px;top:${ph*640}px;transform:rotate(${ph*360+i*40}deg);opacity:${(1-ph)}">${icon('money',90)}</div>`}
  } else if(pr==='phone'){
    const sh=Math.sin(t*40)*(Math.sin(t*3)>0?6:0);
    h+=`<div style="position:absolute;left:390px;top:40px;transform:rotate(${sh}deg)">${icon('phone',300)}</div>`;
    for(let i=0;i<3;i++){const ph=((t*.9+i*.33)%1);h+=`<div style="position:absolute;left:${540-150-ph*160}px;top:${190-150-ph*160}px;width:${300+ph*320}px;height:${300+ph*320}px;border-radius:50%;border:5px solid var(--gold);opacity:${(1-ph)*.7}"></div>`}
    h+=`<div class="mono" style="position:absolute;left:0;right:0;top:${560}px;text-align:center;font-size:30px;color:rgba(15,42,34,.6)">${esc(s.prop_label||'входящий вызов')}</div>`;
  } else if(pr==='alert'){
    const pu=.5+.5*Math.sin(t*6);
    h+=`<div style="position:absolute;left:390px;top:60px;width:300px;height:300px;border-radius:50%;background:var(--red);opacity:${.25+.25*pu};transform:scale(${1+.15*pu})"></div><div style="position:absolute;left:465px;top:135px;width:150px;height:150px;border-radius:50%;background:var(--red);color:#fff;font:900 110px/150px Inter;text-align:center">!</div>`;
  } else if(pr==='doc'){
    h+=`<div style="position:absolute;left:380px;top:${40+Math.sin(t*2)*10}px;transform:rotate(${Math.sin(t*1.5)*5}deg)">${icon('doc',320)}</div>`;
  }
  if(s.stamp){const a=pop(t,s.stamp.at,.3), ga=s.card?1-P(t,s.card.at-.1,.3):1;
    h+=`<div style="position:absolute;left:0;right:0;top:360px;display:flex;justify-content:center"><div class="stamp" style="position:relative;transform:scale(${2-a}) rotate(-8deg);opacity:${vis(t,s.stamp.at,.12)*ga}">${esc(s.stamp.text)}</div></div>`}
  if(s.card){const b=pop(t,s.card.at,.45);
    h+=`<div class="card" style="left:140px;top:340px;width:800px;height:300px;display:flex;align-items:center;gap:30px;padding:0 50px;transform:scale(${b}) rotate(${(1-b)*6}deg);opacity:${vis(t,s.card.at)}">
     <div style="font:900 ${String(s.card.big).length>3?120:200}px/1 Inter;color:var(--gold);white-space:nowrap">${esc(s.card.big)}</div><div style="font:800 76px/1.05 Inter">${esc(s.card.text)}<br><span style="font:600 40px Inter;color:rgba(15,42,34,.6)">${esc(s.card.sub||'')}</span></div></div>`}
  return h;
};
SC.checklist=(t,s)=>{
  let h=numIntro(t,s); const t0=nst(s); if(t<t0) return h;
  const L=P(t,t0,.35), ph=eo(L); const items=s.items||[];
  let x0=90,w=900;
  if(s.device==='phone_rec'){
    const rec=items.length>1&&t>=items[1].at, tc=rec?t-items[1].at:0;
    h+=`<div style="position:absolute;left:110px;top:${10+60*(1-ph)}px;width:380px;height:700px;border-radius:56px;background:#111a17;padding:22px;opacity:${L};box-shadow:0 30px 60px rgba(0,0,0,.25)">
     <div style="position:relative;width:100%;height:100%;border-radius:38px;overflow:hidden;background:linear-gradient(#e9dcc0,#d8c6a2)">
      <div style="position:absolute;left:60px;top:90px;width:220px;height:150px;border-radius:50%;background:radial-gradient(rgba(110,95,60,.6),rgba(110,95,60,0) 70%);transform:scale(${1+.04*Math.sin(t*3)})"></div>
      <div style="position:absolute;left:30px;bottom:120px;width:120px;height:160px;background:rgba(60,40,20,.35);border-radius:8px"></div>
      <div style="position:absolute;right:30px;bottom:120px;width:150px;height:100px;background:rgba(60,40,20,.28);border-radius:8px"></div>
      <div style="position:absolute;inset:16px;border:3px solid rgba(255,255,255,.75);border-radius:26px"></div>
      <div class="mono" style="position:absolute;top:34px;left:0;right:0;text-align:center;color:#fff;font-size:28px;font-weight:700;text-shadow:0 1px 4px rgba(0,0,0,.4)">${rec?`<span style="display:inline-block;width:20px;height:20px;border-radius:50%;background:#e33;opacity:${Math.sin(t*8)>0?1:.25};margin-right:10px"></span>REC 00:0${Math.floor(tc)%10}`:'ВИДЕО'}</div>
      <div style="position:absolute;bottom:30px;left:50%;margin-left:-46px;width:92px;height:92px;border-radius:50%;border:7px solid #fff;background:${rec?'#e33':'rgba(255,255,255,.3)'}"></div>
     </div></div>`;
    x0=540;w=440;
  } else if(s.title){
    h+=`<div style="position:absolute;left:90px;top:0;font:900 64px Inter;opacity:${L};transform:translateY(${(1-ph)*30}px)">${esc(s.title)}</div>`;
  }
  const top=s.device==='phone_rec'?60:(s.title?120:30), gap=items.length>4?112:128;
  items.forEach((it,i)=>{const on=t>=it.at, a=eo(P(t,t0+.1+i*.12,.4));
    h+=`<div class="ch ${on?'on':''}" style="position:absolute;left:${x0}px;top:${top+i*gap}px;width:${w}px;height:${s.device?84:100}px;font-size:${s.device?34:40}px;transform:translateX(${(1-a)*80}px) scale(${on?1+.05*(1-P(t,it.at,.3)):1});opacity:${a}">
     <b style="background:${on?'var(--g)':''}">${on?'✓':i+1}</b>${esc(it.text)}</div>`});
  return h;
};
SC.document=(t,s)=>{
  let h=numIntro(t,s); const t0=nst(s); if(t<t0) return h;
  if(s.call){const c=pop(t,s.call.at,.4);
    h+=`<div class="card" style="left:80px;top:0;width:580px;height:150px;display:flex;align-items:center;gap:22px;padding:0 30px;z-index:3;transform:scale(${c});opacity:${vis(t,s.call.at)*(s.doc?1-P(t,s.doc.at,.3)*.5:1)}">
     <div style="flex:none;width:90px;height:90px;border-radius:50%;background:var(--red);display:flex;align-items:center;justify-content:center;color:#fff;font:800 44px Inter;transform:rotate(${Math.sin(t*20)*8}deg)">☎</div>
     <div><div style="font:800 40px/1.1 Inter">${esc(s.call.text)}</div><div class="mono" style="font-size:26px;color:rgba(15,42,34,.55)">${esc(s.call.sub||'вызов')} · ${Math.floor(Math.max(0,t-s.call.at)*1.7)} сек</div></div></div>`}
  if(s.doc){const d=eo(P(t,s.doc.at,.5)), lw=P(t,s.doc.at+.3,1.6), f=s.doc.fields||[], top=s.call?120:20;
    h+=`<div class="card" style="left:${s.call?150:90}px;top:${top+80*(1-d)}px;width:520px;height:${700-top}px;padding:44px;z-index:4;opacity:${vis(t,s.doc.at,.2)};transform:rotate(${-3+3*d}deg)">
     <div style="font:900 46px/1.1 Inter;letter-spacing:.04em">${esc(s.doc.title)}</div><div style="font:600 30px Inter;color:rgba(15,42,34,.6);margin-top:6px">${esc(s.doc.sub||'')}</div>
     ${f.map((n,i)=>{const a=cl(lw*f.length-i); return s.doc.checks?
       `<div style="display:flex;align-items:center;gap:16px;margin-top:24px;opacity:${.25+.75*a}"><b style="flex:none;width:40px;height:40px;border-radius:10px;background:${a>=1?'var(--g)':'rgba(15,42,34,.14)'};color:#fff;display:flex;align-items:center;justify-content:center;font:800 26px Inter">${a>=1?'✓':''}</b><span style="font:600 34px Inter">${esc(n)}</span><span style="margin-left:auto;height:16px;width:${90*a}px;border-radius:8px;background:rgba(15,42,34,.18)"></span></div>`:
       `<div style="margin-top:24px"><div class="mono" style="font-size:22px;color:rgba(15,42,34,.5)">${esc(n)}</div><div class="line" style="width:${a*100}%;margin:10px 0 0;background:rgba(15,42,34,.22)"></div></div>`}).join('')}
    </div>`}
  let ty=s.call?180:40;
  (s.tags||[]).forEach((g,i)=>{const r=pop(t,g.at,.4);h+=`<div class="tag" style="left:700px;top:${ty}px;z-index:5;transform:scale(${r});opacity:${vis(t,g.at)}">${esc(g.text)}</div>`;ty+=100});
  if(s.timer){const k=pop(t,s.timer.at,.45), ang=Math.max(0,t-s.timer.at)*240;
    h+=`<div style="position:absolute;left:740px;top:${ty+10}px;width:220px;height:220px;border-radius:50%;background:var(--ink);z-index:5;transform:scale(${k});opacity:${vis(t,s.timer.at)};box-shadow:0 14px 0 rgba(0,0,0,.15)">
      ${[...Array(12).keys()].map(i=>`<div style="position:absolute;left:107px;top:14px;width:6px;height:16px;background:rgba(255,255,255,.5);transform-origin:3px 96px;transform:rotate(${i*30}deg)"></div>`).join('')}
      <div style="position:absolute;left:105px;top:36px;width:10px;height:74px;background:var(--gold2);border-radius:5px;transform-origin:50% 100%;transform:rotate(${ang}deg)"></div>
      <div style="position:absolute;left:98px;top:98px;width:24px;height:24px;border-radius:50%;background:var(--gold2)"></div></div>
     <div class="tag" style="left:712px;top:${ty+250}px;font-size:44px;z-index:5;transform:scale(${pop(t,s.timer.at+.25,.4)});opacity:${vis(t,s.timer.at+.25,.12)}">${esc(s.timer.text)}</div>`;ty+=340}
  if(s.letter){const e=eo(P(t,s.letter.at,.6));
    h+=`<div style="position:absolute;left:${620+300*(1-e)}px;top:${Math.max(ty,170)-120*(1-e)}px;width:400px;height:280px;z-index:5;transform:rotate(${(1-e)*25-6}deg);opacity:${vis(t,s.letter.at)}">
      <div class="card" style="inset:0;background:#f1dfb6"></div>
      <div style="position:absolute;left:0;top:0;width:0;height:0;border-left:200px solid transparent;border-right:200px solid transparent;border-top:150px solid #e6cf9b"></div>
      <div style="position:absolute;left:50%;top:118px;margin-left:-34px;width:68px;height:68px;border-radius:50%;background:var(--red)"></div>
      <div style="position:absolute;left:10px;right:10px;bottom:24px;text-align:center;font:800 30px Inter">${esc(s.letter.text)}</div></div>`;ty=Math.max(ty,170)+320}
  if(s.note){const w=pop(t,s.note.at,.4);
    h+=`<div class="tag" style="left:660px;top:${Math.min(ty,600)}px;z-index:6;transform:scale(${w}) rotate(-4deg);opacity:${vis(t,s.note.at,.12)}">${esc(s.note.text)}</div>`}
  return h;
};
SC.compare=(t,s)=>{
  let h=numIntro(t,s); const t0=nst(s); if(t<t0) return h;
  if(s.question){const q=pop(t,Math.max(t0,s.question.at),.4);
    h+=`<div style="position:absolute;left:0;right:0;top:0;text-align:center;font:900 ${s.question.text.length>16?76:96}px Inter;transform:scale(${q});opacity:${vis(t,Math.max(t0,s.question.at))}">${esc(s.question.text).replace(/\?$/,'<span style="color:var(--gold)">?</span>')}</div>`}
  const side=(x,o)=>{if(!o)return '';const a=pop(t,o.at,.45);
    return `<div class="card" style="left:${x}px;top:170px;width:440px;height:520px;padding:36px;transform:translateY(${(1-a)*80}px) scale(${.9+.1*a});opacity:${vis(t,o.at)}">
     <div style="height:150px">${icon(o.icon||'pipe',150)}</div>
     <div style="font:700 40px/1.1 Inter;margin-top:18px">${esc(o.title)}</div>
     <div style="font:600 30px Inter;color:rgba(15,42,34,.55);margin-top:22px">${esc(o.label||'')}</div>
     <div style="font:900 ${o.value.length>12?50:(o.value.length>8?62:76)}px/1.05 Inter;color:var(--gold);margin-top:6px">${esc(o.value)}</div>
     <div class="mono" style="font-size:22px;color:rgba(15,42,34,.5);margin-top:14px">${esc(o.foot||'')}</div></div>`};
  return h+side(70,s.left)+side(570,s.right);
};
SC.path=(t,s)=>{
  let h=numIntro(t,s); const t0=nst(s); if(t<t0) return h;
  const n=(s.nodes||[]).length, W=n>2?280:400, gap=n>2?60:140, x0=(1080-(n*W+(n-1)*gap))/2;
  s.nodes.forEach((o,i)=>{const a=pop(t,Math.max(t0,o.at),.45), x=x0+i*(W+gap), dark=i===n-1;
    h+=`<div class="card" style="left:${x}px;top:40px;width:${W}px;height:440px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:30px;transform:scale(${a}) rotate(${(1-a)*-8}deg);opacity:${vis(t,Math.max(t0,o.at))};${dark?'background:var(--ink);':''}">
     ${icon(o.icon||'doc',W>300?200:160,dark?'#fff':'var(--ink)')}<div style="font:900 ${o.title.length>10?36:46}px/1.1 Inter;text-align:center;padding:0 16px;color:${dark?'#fff':'var(--ink)'}">${esc(o.title)}</div></div>`;
    if(i<n-1){const nx=s.nodes[i+1], ar=P(t,Math.max(t0,nx.at)-.4,.4);
      h+=`<div style="position:absolute;left:${x+W+8}px;top:254px;width:${(gap-30)*ar}px;height:12px;background:var(--ink);border-radius:6px"></div><div style="position:absolute;left:${x+W+gap-30}px;top:236px;width:0;height:0;border-top:24px solid transparent;border-bottom:24px solid transparent;border-left:30px solid var(--ink);opacity:${ar>=1?1:0}"></div>`}
  });
  if(s.badge){const y=pop(t,s.badge.at,.45);
    h+=`<div class="card" style="left:200px;top:540px;width:680px;height:170px;display:flex;align-items:center;justify-content:center;gap:24px;transform:scale(${y});opacity:${vis(t,s.badge.at)};border:4px solid var(--gold)">
      <div style="font:900 ${s.badge.text.length>8?80:110}px/1 Inter;color:var(--gold);white-space:nowrap">${esc(s.badge.text)}</div><div class="mono" style="font-size:24px;color:rgba(15,42,34,.55);line-height:1.3;max-width:220px">${esc(s.badge.sub||'')}</div></div>`}
  return h;
};
SC.big=(t,s)=>{
  let h=numIntro(t,s); const t0=nst(s); if(t<t0) return h;
  const at=Math.max(t0,s.at_value||t0), a=pop(t,at,.5);
  if(s.icon) h+=`<div style="position:absolute;left:465px;top:${10+Math.sin(t*2)*6}px;opacity:${vis(t,at)}">${icon(s.icon,150)}</div>`;
  h+=`<div style="position:absolute;left:0;right:0;top:${s.icon?190:120}px;text-align:center;transform:scale(${a});opacity:${vis(t,at)}">
    <div style="font:900 ${s.value.length>7?150:200}px/1 Inter;color:var(--gold);white-space:nowrap">${esc(s.value)}</div>
    <div style="font:800 54px/1.15 Inter;margin-top:22px;padding:0 80px">${esc(s.caption||'')}</div>
    <div class="mono" style="font-size:26px;color:rgba(15,42,34,.55);margin-top:18px">${esc(s.foot||'')}</div></div>`;
  return h;
};
SC.chat=(t,s)=>{
  let h=numIntro(t,s); const t0=nst(s); if(t<t0) return h;
  const L=P(t,t0,.35), ph=eo(L);
  let msgs='', y=150;
  (s.messages||[]).forEach(m=>{if(t<m.at-.05) return; const a=pop(t,m.at,.35), me=m.from==='me';
    msgs+=`<div class="bub" style="top:${y}px;${me?'right:24px;background:#d9b56a;color:#0f2a22;border-bottom-right-radius:6px':'left:24px;background:#fff;color:#0f2a22;border-bottom-left-radius:6px'};transform:scale(${a});transform-origin:${me?'100%':'0'} 100%">${esc(m.text)}</div>`;
    y+=Math.ceil(m.text.length/18)*36+56});
  const typing=(s.messages||[]).find(m=>t<m.at-.05&&t>m.at-.9&&m.from!=='me');
  if(typing) msgs+=`<div class="bub" style="top:${y}px;left:24px;background:#fff">${[0,1,2].map(i=>`<span style="display:inline-block;width:14px;height:14px;margin:0 4px;border-radius:50%;background:#999;transform:translateY(${Math.sin(t*12+i)*4}px)"></span>`).join('')}</div>`;
  h+=`<div style="position:absolute;left:${90}px;top:${10+60*(1-ph)}px;width:420px;height:700px;border-radius:56px;background:#111a17;padding:20px;opacity:${L};box-shadow:0 30px 60px rgba(0,0,0,.25)">
   <div style="position:relative;width:100%;height:100%;border-radius:40px;overflow:hidden;background:#e8e2d4">
    <div style="position:absolute;left:0;right:0;top:0;height:110px;background:#fff;display:flex;align-items:center;gap:16px;padding:30px 24px 0">
     <div style="flex:none;width:56px;height:56px;border-radius:50%;background:var(--g)"></div><div style="font:700 26px/1.15 Inter">${esc(s.contact||'Неизвестный')}</div></div>
    ${msgs}</div></div>`;
  if(s.stamp){const a=pop(t,s.stamp.at,.3);
    h+=`<div class="stamp" style="left:${s.stamp.text.length>9?250:300}px;top:430px;z-index:6;font-size:${s.stamp.text.length>9?60:76}px;transform:scale(${2-a}) rotate(-8deg);opacity:${vis(t,s.stamp.at,.12)}">${esc(s.stamp.text)}</div>`}
  return h;
};
SC.photo=(t,s)=>{
  let h=numIntro(t,s); const t0=nst(s); if(t<t0) return h;
  const a=eo(P(t,t0,.5)), z=1.05+.08*cl((t-t0)/6);
  h+=`<div class="card" style="left:90px;top:${20+40*(1-a)}px;width:900px;height:600px;overflow:hidden;padding:0;opacity:${a};transform:rotate(${-1.5*(1-a)}deg)">
    <div style="position:absolute;inset:0;background:url(${D.img[s.src]}) center ${s.focus||'40%'}/cover;transform:scale(${z})"></div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:180px;background:linear-gradient(rgba(15,42,34,0),rgba(15,42,34,.85))"></div>
    <div style="position:absolute;left:36px;right:36px;bottom:30px;color:#fff;font:800 46px/1.1 Inter">${esc(s.caption||'')}</div>
    <div class="mono" style="position:absolute;right:20px;top:16px;color:rgba(255,255,255,.8);font-size:20px">${esc(s.credit||'')}</div></div>`;
  return h;
};
SC.outro=(t,s)=>{
  let h='';const a=pop(t,s.start+.05,.5);
  h+=`<div style="position:absolute;left:390px;top:20px;width:300px;height:380px;transform:scale(${a}) translateY(${Math.sin(t*3)*8}px)">
    <div style="position:absolute;inset:0;background:var(--ink);clip-path:polygon(0 0,100% 0,100% 100%,50% 76%,0 100%);border-radius:10px"></div>
    <div style="position:absolute;left:0;right:0;top:110px;text-align:center;color:var(--gold2);font:900 120px Inter">✓</div></div>`;
  const b=pop(t,s.start+.5,.45);
  h+=`<div style="position:absolute;left:0;right:0;top:440px;text-align:center;transform:scale(${b});opacity:${vis(t,s.start+.5)}">
    <div style="font:900 70px Inter">${esc(s.title||'Сохраните')}</div>
    ${s.follow?'':`<div style="font:600 36px Inter;color:rgba(15,42,34,.6);margin-top:14px">${esc(s.sub||'помощник — бот в шапке профиля')}</div>`}</div>`;
  if(s.follow){const f=pop(t,s.follow_at||s.start+1.0,.45), pu=1+.04*Math.sin(t*5);
    h+=`<div style="position:absolute;left:0;right:0;top:640px;display:flex;justify-content:center;opacity:${vis(t,s.follow_at||s.start+1.0)}"><div style="transform:scale(${f*pu});background:var(--gold);color:#fff;font:800 46px Inter;padding:22px 44px;border-radius:999px;box-shadow:0 10px 0 rgba(15,42,34,.18);white-space:nowrap">＋ ${esc(s.follow)}</div></div>`}
  return h;
};

// ---------- кадр ----------
const MC=[];D.scenes.forEach(s=>{MC.push({at:s.start,src:s.mascot});if(s.mascot2)MC.push({at:s.mascot2.at,src:s.mascot2.src})});
function render(t){
  D.t=t;
  let si=0;D.scenes.forEach((s,i)=>{if(t>=s.start-.05)si=i});
  const s=D.scenes[si];
  $('#stage').innerHTML=`<div class="sc" style="opacity:${P(t,s.start-.05,.25)};transform:scale(${1+.025*cl((t-s.start)/6)})">${SC[s.type](t,s)}</div>`;
  $('#lbl').textContent=s.label||'';
  let fi=0;D.sent.forEach((st,i)=>{if(t>=D.words[st[0]].s-.08)fi=i});
  const [a,b]=D.sent[fi];let cap='';
  for(let i=a;i<=b;i++){const w=D.words[i],x=P(t,w.s-.04,.22),on=t>=w.s-.04;
    cap+=`<span class="${w.k?'k':''}" style="opacity:${on?x:0};transform:translateY(${(1-eo(x))*26}px) scale(${w.k?(.8+.2*back(x)):1})">${esc(w.w)}</span>`}
  $('#cap').innerHTML=cap;
  if(D.steps.length){
    let tk='';const last=D.scenes[D.scenes.length-1];
    D.steps.forEach((n,i)=>{const st=i+1,act=s.step===st,done=(s.step&&st<s.step)||(!s.step&&si>D.lastStepIdx);
      const ap=eo(P(t,D.trkStart+i*.08,.35));
      tk+=`<div class="ch ${act?'on':''} ${done?'done':''}" style="opacity:${ap}; transform:translateX(${(1-ap)*-60}px) scale(${act?1+.04*pop(t,s.start,.4):.94})"><b>${st}</b>${esc(n)}${done?'<i>✓</i>':''}</div>`});
    $('#trk').innerHTML=tk;
  }
  let src=s.mascot,ms=s.start;
  if(s.mascot2&&t>=s.mascot2.at){src=s.mascot2.src;ms=s.mascot2.at}
  const m=$('#masc');
  if(m.dataset.src!==src){m.src=D.img[src];m.dataset.src=src}
  const e=pop(t,ms,.45);
  m.style.transform=`translateY(${(1-e)*140+Math.sin(t*2.2)*6}px) rotate(${Math.sin(t*1.3)*1.2}deg) scale(${.96+.04*e})`;
  m.style.opacity=cl((t-ms)/.12);
  let prev=null;for(let i=1;i<MC.length;i++){if(t>=MC[i].at)prev={at:MC[i].at,src:MC[i-1].src}}
  const m2=$('#masc2');
  if(prev&&t-prev.at<.35&&prev.src!==src){if(m2.dataset.src!==prev.src){m2.src=D.img[prev.src];m2.dataset.src=prev.src}
    const q=P(t,prev.at,.3);m2.style.opacity=1-q;m2.style.transform=`translateY(${q*120}px)`}else m2.style.opacity=0;
}
window.render=render;
</script></body></html>"""


COVER_MASCOT = """<html><head><meta charset='utf-8'><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;overflow:hidden;font-family:Inter,sans-serif;color:#f3ead7;
background:radial-gradient(ellipse 80%% 55%% at 55%% 38%%,#2a5a47 0%%,#173b2f 45%%,#0f2a22 75%%)}
.m{position:absolute;left:50%%;top:330px;height:1180px;transform:translateX(-46%%);filter:drop-shadow(0 30px 50px rgba(0,0,0,.35))}
.sh{position:absolute;inset:0;background:linear-gradient(180deg,rgba(15,42,34,.55) 0%%,rgba(15,42,34,0) 20%%,rgba(15,42,34,0) 52%%,rgba(15,42,34,.92) 70%%,rgba(15,42,34,.99) 100%%)}
.gl{position:absolute;inset:0;opacity:.08;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/></filter><rect width='300' height='300' filter='url(%%23n)'/></svg>")}
.b{position:absolute;left:96px;top:300px;font-size:30px;letter-spacing:.22em;font-weight:700;color:#d9b56a}
.w{position:absolute;left:96px;right:96px;bottom:200px}
h1{font-family:'Noto Serif','DejaVu Serif',serif;font-size:82px;line-height:1.06;font-weight:700}
.g{color:#d9b56a}
.s{display:inline-block;margin-top:50px;background:#d9b56a;color:#0f2a22;font-size:42px;font-weight:700;padding:20px 32px}
</style></head><body><img class='m' src='%s'><div class='sh'></div><div class='gl'></div>
<div class='b'>LEGAL.LAB.AI</div><div class='w'><h1>%s<br><span class='g'>%s</span></h1><span class='s'>%s</span></div></body></html>"""


async def render_cover(c, path):
    from playwright.async_api import async_playwright
    import make_reel
    e = _h.escape
    if c.get("photo"):
        page = make_reel.PHOTO_COVER % (c.get("focus", "30%"), uri(c["photo"]), e(c["title"]), e(c.get("accent", "")), e(c.get("badge", "")))
    else:
        pose = c.get("pose") if c.get("pose") in POSES else "doubt"
        page = COVER_MASCOT % (uri(f"media/mascot/{pose}.png"), e(c["title"]), e(c.get("accent", "")), e(c.get("badge", "")))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        await pg.set_content(page)
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=path, type="jpeg", quality=92)
        await b.close()


def build_data(d, spec):
    tempo = spec.get("tempo", 1.0)
    T = lambda ms: LEAD + ms / 1000 / tempo
    raw = json.load(open(f"{d}/words_raw.json"))
    kw = {norm(k) for k in spec.get("keywords", []) if len(norm(k)) > 2 or norm(k).isdigit()}
    words = [{"w": r[0], "s": T(r[1]), "k": norm(r[0]) in kw or any(norm(p) in kw for p in r[0].split())} for r in raw]
    nw = [norm(r[0].split()[0]) if r[0].split() else "" for r in raw]
    sent, st = [], 0
    for i, r in enumerate(raw):
        if r[0].endswith((".", "?", "!")) or i == len(raw) - 1 or (i - st >= 7 and r[0].endswith((",", "—", ":"))):
            sent.append([st, i]); st = i + 1
    warns = []

    def find(anchor, frm):
        if isinstance(anchor, (int, float)):
            ms = anchor
            idx = next((i for i, r in enumerate(raw) if r[1] >= ms), frm)
            return T(ms), idx
        toks = [norm(x) for x in str(anchor).split() if norm(x)]
        for i in range(frm, len(raw) - len(toks) + 1):
            if all(nw[i + k] == toks[k] or nw[i + k].startswith(toks[k]) for k in range(len(toks))):
                return T(raw[i][1]), i
        return None, frm

    scenes, ptr, imgs = [], 0, {}

    def pose(p):
        p = p or "coffee_smile"
        if p not in POSES:
            warns.append(f"поза {p} не из списка, заменена на idea"); p = "idea"
        path = f"media/mascot/{p}.png"; imgs[path] = uri(path); return path

    for n, s in enumerate(spec["scenes"]):
        s = json.loads(json.dumps(s))
        if n == 0 and not s.get("at"):
            s["start"], sidx = 0.0, 0
        else:
            st_, sidx = find(s.get("at"), ptr)
            if st_ is None:
                warns.append(f"сцена {n}: якорь «{s.get('at')}» не найден"); st_ = scenes[-1]["start"] + 3 if scenes else 0
            s["start"] = 0.0 if n == 0 else st_
        ptr = sidx
        s["mascot"] = pose(s.get("mascot"))
        base = s["start"] + (0.9 if s.get("step") else 0)

        def res(o, key="at", dflt=1.0):
            if isinstance(o, dict) and key in o:
                v, _ = find(o[key], sidx)
                if v is None:
                    warns.append(f"сцена {n}: якорь «{o[key]}» не найден"); v = base + dflt
                o[key] = max(v, s["start"] + (0.9 if s.get("step") else 0) if o is not s else v)
            elif isinstance(o, dict):
                o[key] = base + dflt
        for k in ("stamp", "card", "call", "doc", "timer", "letter", "note", "question", "left", "right", "badge"):
            if isinstance(s.get(k), dict):
                res(s[k])
        for i, k in enumerate(("items", "tags", "nodes", "messages")):
            for j, o in enumerate(s.get(k, []) or []):
                res(o, dflt=0.6 + 0.8 * j)
        if s.get("follow_at") is not None:
            v, _ = find(s["follow_at"], sidx); s["follow_at"] = v if v is not None else base + 1.0
        if "at_value" in s:
            v, _ = find(s["at_value"], sidx); s["at_value"] = v if v is not None else base
        if s.get("mascot2"):
            v, _ = find(s["mascot2"].get("at"), sidx)
            s["mascot2"] = {"at": v if v is not None else base + 1.5, "src": pose(s["mascot2"].get("pose"))}
        if s.get("type") == "photo" and s.get("src"):
            imgs[s["src"]] = uri(s["src"])
        scenes.append(s)
    for w in warns:
        print("WARN", w)
    first_step = next((s["start"] for s in scenes if s.get("step")), None)
    trk = scenes[0].get("card", {}).get("at") if isinstance(scenes[0].get("card"), dict) else None
    trk = trk or first_step or 0
    last = max([i for i, s in enumerate(scenes) if s.get("step")], default=99)
    return {"words": words, "sent": sent, "scenes": scenes, "steps": spec.get("steps", []), "img": imgs, "trkStart": trk, "lastStepIdx": last}


async def render_frames(html, n, fdir):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.set_content(html)
        await pg.wait_for_timeout(300)
        for i in range(n):
            await pg.evaluate(f"render({i / FPS})")
            await pg.screenshot(path=f"{fdir}/f{i:05d}.jpg", type="jpeg", quality=90)
        await b.close()
        if errs:
            raise SystemExit("JS error: " + errs[0])


def main(d):
    spec = json.load(open(f"{d}/spec.json"))
    data = build_data(d, spec)
    voice = f"{d}/narration.wav"
    vd = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice]).decode())
    total = LEAD + vd + 1.6
    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    fdir = f"{d}/frames"
    shutil.rmtree(fdir, ignore_errors=True); os.makedirs(fdir)
    n = int(total * FPS)
    if not spec.get("cover", {}).get("title"):
        raise SystemExit("spec.cover.title обязателен: обложка делается отдельно, в стиле канала")
    asyncio.run(render_cover(spec["cover"], f"{d}/cover.jpg"))
    asyncio.run(render_frames(html, n, fdir))
    compose(f"{d}/music.wav", total + 1, seed=spec.get("seed", 1))
    out = f"{d}/reel.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{fdir}/f%05d.jpg",
                    "-i", f"{d}/music.wav", "-i", voice, "-filter_complex",
                    f"[1:a]volume=0.13[mu];[2:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},aformat=channel_layouts=stereo,volume=1.05[vo];"
                    f"[mu][vo]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={total - 1.5:.2f}:d=1.5[a]",
                    "-map", "0:v", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                    "-pix_fmt", "yuv420p", "-ar", "44100", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)
    # контактный лист для проверки
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-vf", "fps=1/2,scale=270:-1,tile=8x3", "-frames:v", "1",
                    f"{d}/preview.jpg"], check=True)
    intro = spec.get("intro_video")
    if intro:
        ipath = intro if os.path.isabs(intro) else os.path.join(ROOT, intro)
        os.replace(out, f"{d}/_body.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ipath, "-i", f"{d}/_body.mp4", "-filter_complex",
                        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0xf4ecdc,setsar=1,fps=30,format=yuv420p[iv];"
                        "[0:a]aresample=44100,aformat=channel_layouts=stereo[ia];[1:v]setsar=1,fps=30,format=yuv420p[bv];"
                        "[1:a]aresample=44100,aformat=channel_layouts=stereo[ba];[iv][ia][bv][ba]concat=n=2:v=1:a=1[v][a]",
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)
        os.remove(f"{d}/_body.mp4")
    # «Холодный старт»: первые cold_open секунд поверх ролика — обложка канала (крючок крупно с первого кадра).
    co = float(spec.get("cold_open", 1.5))
    if co > 0:
        os.replace(out, f"{d}/_nocold.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{d}/_nocold.mp4", "-loop", "1", "-t", f"{co + 0.4:.2f}",
                        "-i", f"{d}/cover.jpg", "-filter_complex",
                        f"[1:v]scale=1080:1920,format=rgba,fade=t=out:st={co:.2f}:d=0.35:alpha=1[c];[0:v][c]overlay=0:0:eof_action=pass,format=yuv420p[v]",
                        "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "copy",
                        "-movflags", "+faststart", out], check=True)
        os.remove(f"{d}/_nocold.mp4")
    shutil.rmtree(fdir, ignore_errors=True)
    os.remove(f"{d}/music.wav")
    print(out, f"{total:.1f}s", n, "frames")


if __name__ == "__main__":
    main(sys.argv[1])
