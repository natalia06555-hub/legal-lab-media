"""Рендер карусели Legal.Lab.Ai из JSON.

python3 tools/render_carousel.py spec.json out_dir

spec.json: {"slides": [ {...}, ... ]}
Типы слайдов:
  cover    : kicker, title, accent, sub
  text     : kicker, title, paras[], foot
  big      : kicker, big, paras[], foot
  list     : kicker, items[], foot
  numbered : kicker, items[], foot
  cta      : title, accent, button
Выход: slide_1.jpg ... slide_N.jpg (1080x1350) + slide_N.png
"""
import asyncio, json, os, sys, html
from playwright.async_api import async_playwright

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:#0f2a22;color:#f3ead7;font-family:'Inter',sans-serif;overflow:hidden}
.s{position:relative;width:1080px;height:1350px;padding:110px 96px;display:flex;flex-direction:column}
.s:before{content:'';position:absolute;inset:36px;border:2px solid rgba(201,166,92,.55);pointer-events:none}
.brand{font-size:26px;letter-spacing:.22em;text-transform:uppercase;color:#c9a65c;font-weight:600;max-width:760px}
.num{position:absolute;right:96px;top:110px;font-size:26px;color:#c9a65c;letter-spacing:.1em}
h1{font-family:'Noto Serif','DejaVu Serif',serif;font-weight:700;font-size:88px;line-height:1.08;margin-top:auto}
h2{font-family:'Noto Serif','DejaVu Serif',serif;font-weight:700;font-size:66px;line-height:1.12;margin-top:110px}
.gold{color:#d9b56a}
p{font-size:40px;line-height:1.42;color:#e6dcc5;margin-top:40px}
.sub{font-size:46px;margin-top:56px;color:#d9b56a;font-weight:600}
.big{font-family:'Noto Serif','DejaVu Serif',serif;font-size:170px;line-height:1;color:#d9b56a;margin-top:100px;font-weight:700}
ul,ol{list-style:none;margin-top:56px}
li{font-size:42px;line-height:1.35;padding:24px 0 24px 64px;position:relative;border-bottom:1px solid rgba(201,166,92,.25)}
ul li:before{content:'';position:absolute;left:8px;top:42px;width:22px;height:22px;background:#c9a65c;transform:rotate(45deg)}
ol{counter-reset:n}
ol li:before{counter-increment:n;content:counter(n);position:absolute;left:0;top:20px;font-family:'Noto Serif','DejaVu Serif',serif;font-size:48px;color:#d9b56a;font-weight:700}
.foot{margin-top:auto;font-size:30px;color:#c9a65c;letter-spacing:.04em}
.btn{display:inline-block;margin-top:50px;padding:28px 46px;border:2px solid #d9b56a;color:#d9b56a;font-size:36px;font-weight:600}
"""

e = lambda t: html.escape(t or "")


def body(s):
    t = s.get("type", "text")
    k = f'<div class="brand">{e(s.get("kicker", "Legal.Lab.Ai"))}</div>'
    foot = f'<div class="foot">{e(s["foot"])}</div>' if s.get("foot") else ""
    paras = "".join(f"<p>{e(p)}</p>" for p in s.get("paras", []))
    if t == "cover":
        return (k + f'<h1>{e(s.get("title"))}<br><span class="gold">{e(s.get("accent"))}</span></h1>'
                + (f'<div class="sub">{e(s["sub"])}</div>' if s.get("sub") else "")
                + '<div class="foot" style="margin-top:90px">Листайте →</div>')
    if t == "big":
        return k + f'<div class="big">{e(s.get("big"))}</div>' + paras + foot
    if t in ("list", "numbered"):
        tag = "ul" if t == "list" else "ol"
        items = "".join(f"<li>{e(i)}</li>" for i in s.get("items", []))
        return k + (f'<h2 style="margin-top:70px">{e(s["title"])}</h2>' if s.get("title") else "") + f"<{tag}>{items}</{tag}>" + foot
    if t == "cta":
        return ('<div class="brand">Legal.Lab.Ai</div><div style="margin-top:auto">'
                f'<h2 style="margin-top:0">{e(s.get("title"))}<br><span class="gold">{e(s.get("accent"))}</span></h2>'
                f'<div class="btn">{e(s.get("button", "Бесплатный помощник — в боте в шапке профиля"))}</div></div>')
    return k + f'<h2>{e(s.get("title"))}</h2>' + paras + foot


async def main(spec, out):
    os.makedirs(out, exist_ok=True)
    slides = json.load(open(spec))["slides"]
    from PIL import Image
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        for i, s in enumerate(slides, 1):
            num = f'<div class="num">{i}/{len(slides)}</div>'
            await pg.set_content(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='s'>{num}{body(s)}</div></body></html>")
            await pg.wait_for_timeout(150)
            png = f"{out}/slide_{i}.png"
            await pg.screenshot(path=png)
            Image.open(png).convert("RGB").save(f"{out}/slide_{i}.jpg", quality=85, optimize=True)
        await b.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
