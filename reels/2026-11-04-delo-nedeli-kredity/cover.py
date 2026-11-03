import os
from playwright.sync_api import sync_playwright
here=os.path.dirname(os.path.abspath(__file__))
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"])
    pg=b.new_page(viewport={"width":1080,"height":1920})
    pg.goto("file://"+os.path.join(here,"scene.html")); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
    pg.evaluate("""()=>{render(5.3);
      for(const id of ['cal','t1','t2','t3','t4','n1','n2','src','dots2']) document.getElementById(id).style.display='none';
      const c=document.getElementById('clip'); c.style.top='430px'; c.style.transform='rotate(-1.5deg)';
      const st=document.getElementById('strip'); st.style.top='300px';
      const s=document.getElementById('stamp'); s.style.left='540px'; s.style.top='1010px'; s.style.transform='rotate(-12deg)';
      const lab=document.createElement('div'); lab.textContent='LEGAL.LAB.AI';
      lab.style.cssText='position:absolute;left:96px;top:200px;font:700 30px/1 Osw;letter-spacing:.32em;color:#c9a24a';
      document.getElementById('stage').appendChild(lab);
      const tag=document.createElement('div'); tag.textContent='Дело недели · Верховный суд';
      tag.style.cssText='position:absolute;left:96px;top:1300px;padding:22px 32px;background:#c9a24a;color:#1d1a16;font:700 40px/1 Osw;letter-spacing:.02em';
      document.getElementById('stage').appendChild(tag);
      const b=document.getElementById('brand'); b.style.display='none';
      st.style.display='none';
    }""")
    pg.screenshot(path="cover.jpg",type="jpeg",quality=92)
    b.close()
