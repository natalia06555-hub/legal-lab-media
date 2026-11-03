import sys, subprocess, os
from playwright.sync_api import sync_playwright

mode = sys.argv[1]  # "preview" or "full"
DUR, FPS = 13.0, 30
here = os.path.dirname(os.path.abspath(__file__))

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.goto("file://" + os.path.join(here, "scene.html"))
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(400)
    if mode == "preview":
        for t in map(float, sys.argv[2:]):
            pg.evaluate(f"render({t})")
            pg.screenshot(path=f"prev_{t}.jpg", type="jpeg", quality=88)
    else:
        tmp = "delo_tmp.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                               "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                               "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
        for i in range(int(DUR * FPS)):
            pg.evaluate(f"render({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
        ff.stdin.close()
        if ff.wait() == 0:
            os.replace(tmp, "delo_nedeli_test.mp4")
    b.close()
