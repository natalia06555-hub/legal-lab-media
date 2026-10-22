"""Сборка Reels Legal.Lab.Ai: золотая обложка + слайды + неоклассическая музыка.

python3 tools/make_reel.py spec.json out_dir

spec.json:
{
  "cover": {"title": "Нейросеть ошиблась —", "accent": "отвечаете вы", "badge": "30 секунд о ваших рисках"},
  "slides": [ ... те же типы, что в render_carousel.py ... ],
  "seed": 7                      # вариант музыки (любое число)
}
Выход: reel.mp4 (1080x1920, ~25-35 c), cover.jpg (1080x1920)
"""
import asyncio, json, os, subprocess, sys, html
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
import render_carousel as rc
from music_neoclassic import compose

COVER = """<html><head><meta charset='utf-8'><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;background:#d9b56a;font-family:'Inter',sans-serif;color:#0f2a22}
.w{position:absolute;left:0;top:240px;width:1080px;height:1440px;padding:110px 96px;display:flex;flex-direction:column}
.w:before{content:'';position:absolute;inset:36px;border:3px solid rgba(15,42,34,.55)}
.b{font-size:28px;letter-spacing:.22em;font-weight:700}
h1{font-family:'Noto Serif','DejaVu Serif',serif;font-size:112px;line-height:1.05;font-weight:700;margin-top:auto}
.s{display:inline-block;margin-top:70px;background:#0f2a22;color:#d9b56a;font-size:44px;font-weight:600;padding:22px 34px}
.f{margin-top:auto;font-size:32px;font-weight:600}
</style></head><body><div class='w'><div class='b'>LEGAL.LAB.AI</div>
<h1>%s<br>%s</h1><div><span class='s'>%s</span></div><div class='f'>Юрист объясняет без занудства</div></div></body></html>"""


async def render_cover(c, path):
    e = html.escape
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        await pg.set_content(COVER % (e(c["title"]), e(c.get("accent", "")), e(c.get("badge", "30 секунд о ваших рисках"))))
        await pg.wait_for_timeout(200)
        await pg.screenshot(path=path)
        await b.close()


def main(spec_path, out):
    os.makedirs(out, exist_ok=True)
    spec = json.load(open(spec_path))
    asyncio.run(render_cover(spec["cover"], f"{out}/cover.png"))
    from PIL import Image
    Image.open(f"{out}/cover.png").convert("RGB").save(f"{out}/cover.jpg", quality=90)
    json.dump({"slides": spec["slides"]}, open(f"{out}/_slides.json", "w"), ensure_ascii=False)
    asyncio.run(rc.main(f"{out}/_slides.json", f"{out}/frames"))
    n = len(spec["slides"])
    files = [f"{out}/cover.png"] + [f"{out}/frames/slide_{i}.png" for i in range(1, n + 1)]
    D = [1.8] + [4.4] * n
    D[-1] = 4.6
    X = 0.5
    total = sum(D) - X * (len(D) - 1)
    compose(f"{out}/music.wav", total + 1, seed=spec.get("seed", 1))
    inp, f = [], []
    for i, (fn, d) in enumerate(zip(files, D)):
        inp += ["-loop", "1", "-t", str(d), "-i", fn]
        if i == 0:
            f.append("[0:v]scale=1080:1920,setsar=1,fps=30,format=yuv420p[v0]")
        else:
            f.append(f"[{i}:v]scale=1080:1350,pad=1080:1920:0:285:color=0x0f2a22,setsar=1,fps=30,format=yuv420p[v{i}]")
    prev, off = "v0", 0
    for i in range(1, len(D)):
        off += D[i - 1] - X
        f.append(f"[{prev}][v{i}]xfade=transition=fade:duration={X}:offset={off:.2f}[x{i}]")
        prev = f"x{i}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-i", f"{out}/music.wav",
                    "-filter_complex", ";".join(f), "-map", f"[{prev}]", "-map", f"{len(D)}:a",
                    "-t", f"{total:.2f}", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-af", f"afade=t=out:st={total - 2:.2f}:d=2",
                    "-movflags", "+faststart", f"{out}/reel.mp4"], check=True)
    print(f"{out}/reel.mp4", round(total, 1), "s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
