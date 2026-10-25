"""Render an animated Reel (motion/reel.html + motion/props.js) frame by frame with Chromium and encode it.
Usage: python3 scripts/render_motion.py <spec.json> <durations-json-list> <out.mp4> [audio-file]"""
import json, subprocess, sys, pathlib
from playwright.sync_api import sync_playwright
spec, durs, out = json.load(open(sys.argv[1])), json.loads(sys.argv[2]), sys.argv[3]
audio = sys.argv[4] if len(sys.argv) > 4 else None
FPS = 30
root = pathlib.Path(__file__).resolve().parent.parent
html = (root / "motion/reel.html").read_text().replace("<script src=\"props.js\"></script>",
       f"<script>window.SPEC={json.dumps(spec)};window.DURS={json.dumps(durs)};</script><script src=\"props.js\"></script>")
page_path = root / "motion/_render.html"; page_path.write_text(html)
total = sum(durs); n = int(round(total * FPS))
enc = ["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-"]
if audio: enc += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "160k"]
enc += ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", "30",
        "-b:v", "3000k", "-maxrate", "3500k", "-bufsize", "6000k", "-t", f"{total:.3f}", "-movflags", "+faststart", out]
p = subprocess.Popen(enc, stdin=subprocess.PIPE)
with sync_playwright() as pw:
    exe = "/opt/pw-browsers/chromium"
    b = pw.chromium.launch(executable_path=exe) if pathlib.Path(exe).exists() else pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto(page_path.as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
    for i in range(n):
        # frame 0 = the finished hook screen, so Instagram/Facebook/TikTok use it as the cover (not a blank frame)
        pg.evaluate(f"renderAt({min(2.4, durs[0] - 0.35) if i == 0 else i / FPS})")
        p.stdin.write(pg.screenshot(type="jpeg", quality=90))
    b.close()
p.stdin.close(); p.wait(); page_path.unlink(missing_ok=True)
print(out, f"{total:.1f}s", n, "frames")
