"""Render an HTML design to PNG with Chromium and fail if it overflows.
Usage: python3 scripts/render.py <in.html> <out.png> [width=1080] [height=1350]"""
import sys, pathlib
from playwright.sync_api import sync_playwright
src, out = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 1080
h = int(sys.argv[4]) if len(sys.argv) > 4 else 1350
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if pathlib.Path("/opt/pw-browsers/chromium").exists() else p.chromium.launch()
    pg = b.new_page(viewport={"width": w, "height": h})
    pg.goto(pathlib.Path(src).resolve().as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
    ok = pg.evaluate("[...document.fonts].filter(f=>f.status==='loaded').length")
    over = pg.evaluate("""()=>{const bad=[];document.querySelectorAll('body *').forEach(e=>{const r=e.getBoundingClientRect();if(['wedge','glow','brand','ring'].some(c=>e.classList.contains(c)))return;if(r.right>%d+1||r.bottom>%d+1||r.left<-1)bad.push(e.className||e.tagName)});return bad}""" % (w, h))
    pg.screenshot(path=out); b.close()
print(out, "fonts loaded:", ok, "overflow:", over)
if over: sys.exit(1)
