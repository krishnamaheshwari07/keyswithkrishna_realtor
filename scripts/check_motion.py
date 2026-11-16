"""Pre-publish visual check for animated Reels: saves one settled still per scene so the batch run can look at them,
and flags any visible text that runs off the 1080x1920 canvas.
Usage: python3 scripts/check_motion.py posts/YYYY-MM-DD/schedule.json <out-dir>"""
import json, sys, pathlib
from playwright.sync_api import sync_playwright
sched, outdir = json.load(open(sys.argv[1])), pathlib.Path(sys.argv[2]); outdir.mkdir(parents=True, exist_ok=True)
items = sched if isinstance(sched, list) else sched.get("items", [])
root = pathlib.Path(__file__).resolve().parent.parent
OFF = """() => { const out = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode, s = n.textContent.trim(); if (!s) continue;
    const el = n.parentElement, cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    let o = 1; for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); if (o < 0.5) continue;
    const r = document.createRange(); r.selectNodeContents(n); const b = r.getBoundingClientRect(); if (!b.width || !b.height) continue;
    if (b.left < -2 || b.right > 1082 || b.top < -2 || b.bottom > 1922) out.push(s.slice(0, 60)); }
  return out; }"""
bad = 0
with sync_playwright() as pw:
    exe = "/opt/pw-browsers/chromium"
    b = pw.chromium.launch(executable_path=exe) if pathlib.Path(exe).exists() else pw.chromium.launch()
    for it in items:
        if not it.get("motion"): continue
        durs = [float(f.get("min", 4)) for f in it.get("frames", [])]
        html = (root / "motion/reel.html").read_text().replace("<script src=\"props.js\"></script>",
               f"<script>window.SPEC={json.dumps(it['motion'])};window.DURS={json.dumps(durs)};</script><script src=\"props.js\"></script>")
        page_path = root / "motion/_check.html"; page_path.write_text(html)
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(page_path.as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready"); pg.evaluate("window.fontsReady || null")
        t0 = 0.0
        for i, d in enumerate(durs):
            pg.evaluate(f"renderAt({t0 + max(0.1, d - 0.5):.3f})")
            png = outdir / f"{it['id']}-s{i + 1:02d}.png"; pg.screenshot(path=str(png))
            off = pg.evaluate(OFF)
            if off: bad += 1
            print(png, "OFF-CANVAS: " + " | ".join(off) if off else "ok")
            t0 += d
        pg.close(); page_path.unlink(missing_ok=True)
    b.close()
print("off-canvas scenes:", bad)
