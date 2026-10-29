"""Add Krishna's cloned voiceover (Qwen3-TTS 1.7B Base, Apache-2.0; voice prompt = his 2nd Reel, the 'v4-qwen-B' voice
he approved on Oct 24, 2026) to pending Reels.
A Reel opts in with  "vo_pending": true  and  "frames": [{"img": "posts/DATE/ID-frames/f01.png", "say": "...", "min": 4.0}, ...]
Each frame is held for max(min, voice length + padding), the voice is mixed over quiet royalty-free music, the result is saved
as posts/DATE/<file>-vo.mp4 and becomes the item's media_url. On any failure the original (music-only) Reel is kept."""
import os, sys, glob, json, subprocess, hashlib, time, shutil
from datetime import datetime, timezone, timedelta
RAW = "https://raw.githubusercontent.com/krishnamaheshwari07/keyswithkrishna_realtor/main/"
W = "/tmp/vo"; os.makedirs(W, exist_ok=True)
LEAD, TAIL = 0.12, 0.22   # tight cuts (Krishna, Oct 24: Reels felt slow)
TEMPO = 1.12              # pitch-preserving speed-up of the voice
MIN_FRAME = 2.2
READ_FACTOR = 0.65        # slide stays up for 65% of its reading time "min" unless the voice needs longer (Oct 24: avoid silent gaps)
DISCLOSE = "Voiceover: AI-generated in Krishna's own voice."
STAGED = {}   # repo path -> generated file in /tmp (copied in after the git reset in save())
def sh(*a): subprocess.run(list(a), check=True)
def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))

def todo():
    now = datetime.now(timezone.utc); out = []
    for path in sorted(glob.glob("posts/*/schedule.json")):
        for it in json.load(open(path)):
            if it.get("type") == "reel" and it.get("vo_pending") and it.get("status") == "pending" and it.get("frames") \
               and datetime.fromisoformat(it["publish_at"]) + timedelta(minutes=90) > now:
                out.append((path, it))
            elif it.get("type") == "reel" and it.get("tt_revoice") and it.get("frames"):   # already posted: rebuild only the TikTok copy
                out.append((path, it))
    return out

def voice_prompt():
    raw = f"{W}/reels.wav"
    sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:VOICE_KEY_EN2",
       "-in", "data/voice/ref-reels-en.wav.enc", "-out", raw)
    src = raw
    try:
        sh("python", "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", f"{W}/sep", raw)
        src = f"{W}/vocals.wav"
        sh("ffmpeg", "-y", "-v", "error", "-i", glob.glob(f"{W}/sep/htdemucs/*/vocals.wav")[0], "-ac", "1", "-ar", "24000",
           "-af", "highpass=f=70,loudnorm=I=-18:TP=-2", src)
    except Exception as e:
        print("demucs failed, using raw audio:", e)
    from faster_whisper import WhisperModel
    wm = WhisperModel("small.en", device="cpu", compute_type="int8")
    words = [w for s in wm.transcribe(src, language="en", word_timestamps=True)[0] for w in s.words]
    ws = [w for w in words if w.start >= 27.3 and w.end <= 57.4]    # Reel 2 = the approved 'B' voice
    best = None
    for i, w in enumerate(ws):
        d = w.end - ws[0].start
        if d > 15.5: break
        if d >= 8 and (w.word.strip()[-1:] in ".!?," or i == len(ws) - 1 or ws[i + 1].start - w.end > 0.25): best = i
    if best is None: best = min(len(ws) - 1, 30)
    a, b = max(ws[0].start - 0.15, 0), ws[best].end + 0.2
    ref = f"{W}/ref.wav"; sh("ffmpeg", "-y", "-v", "error", "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", src, ref)
    return ref, "".join(w.word for w in ws[:best + 1]).strip()

def build_sfx(cues_path, total, sr=48000, gain=0.30):
    """Mix the sound-effect cues (motion/sfx/*.wav) into one track; gain keeps them under the voice."""
    import numpy as np, soundfile as sf
    try: cues = json.load(open(cues_path))
    except Exception: return None
    if not cues: return None
    track = np.zeros(int((total + 1) * sr), dtype=np.float32); bank = {}
    for c in cues:
        if c["s"] not in bank: bank[c["s"]] = sf.read(f"motion/sfx/{c['s']}.wav", dtype="float32")[0]
        w = bank[c["s"]] * c.get("v", 1) * gain; i = int(c["t"] * sr); track[i:i + len(w)] += w[: len(track) - i]
    out = cues_path.replace(".sfx.json", "-sfx.wav"); sf.write(out, np.clip(track, -1, 1), sr); return out

def music(seed, mood=None):
    tracks = sorted(glob.glob(f"posts/audio/{mood}/*.mp3")) if mood else []   # e.g. posts/audio/tense/ for Market Watch
    tracks = tracks or sorted(glob.glob("posts/audio/*.mp3"))
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return (tracks[h % len(tracks)], h >> 16) if tracks else (None, 0)

def build(m, prompt, it):
    import numpy as np, soundfile as sf
    sr = None; voice = []; frames = it["frames"]; durs = []
    for f in frames:
        wavs, sr = m.generate_voice_clone(text=f["say"], language="English", voice_clone_prompt=prompt)
        v = np.asarray(wavs[0], dtype=np.float32).squeeze()
        nz = np.where(np.abs(v) > 0.01)[0]                       # trim generated leading/trailing silence
        if len(nz): v = v[max(nz[0] - int(0.05 * sr), 0): nz[-1] + int(0.1 * sr)]
        if TEMPO != 1.0:
            a, b = f"{W}/t_in.wav", f"{W}/t_out.wav"; sf.write(a, v, sr)
            sh("ffmpeg", "-y", "-v", "error", "-i", a, "-af", f"atempo={TEMPO}", b); v, _ = sf.read(b, dtype="float32")
        d = max(MIN_FRAME, READ_FACTOR * float(f.get("min", 0)), LEAD + len(v) / sr + TAIL)
        seg = np.zeros(int(round(d * sr)), dtype=np.float32); s0 = int(LEAD * sr)
        seg[s0:s0 + len(v)] = v[: len(seg) - s0]
        voice.append(seg); durs.append(d)
    vw = f"{W}/{it['id']}-voice.wav"; sf.write(vw, np.concatenate(voice), sr)
    total = sum(durs)
    if it.get("motion"):   # animated Reel (motion/reel.html): scenes timed to the voice
        spec = f"{W}/{it['id']}-spec.json"; json.dump(it["motion"], open(spec, "w"))
        silent = f"{W}/{it['id']}-silent.mp4"
        sh("python", "scripts/render_motion.py", spec, json.dumps([round(d, 3) for d in durs]), silent)
        vin = ["-i", silent]
        sfx_track = build_sfx(silent + ".sfx.json", total)
    else:                  # static frames
        sfx_track = None
        lst = f"{W}/{it['id']}.txt"
        with open(lst, "w") as fh:
            for f, d in zip(frames, durs): fh.write(f"file '{os.path.abspath(f['img'])}'\nduration {d:.3f}\n")
            fh.write(f"file '{os.path.abspath(frames[-1]['img'])}'\n")
        vin = ["-f", "concat", "-safe", "0", "-i", lst]
    base = it["media_url"].split("/main/", 1)[1].rsplit(".", 1)[0]
    out = f"{base}-vo{int(time.time()) % 100000}.mp4"   # new name each run (no stale copies/caches)
    tmp_out = f"{W}/{os.path.basename(out)}"; STAGED[out] = tmp_out
    track, h = music(it["id"], it.get("music_mood"))
    venc = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p", "-r", "30", "-g", "30",
            "-b:v", "1800k", "-maxrate", "2200k", "-bufsize", "3000k"]
    if track:
        start = h % max(1, int(min(25, dur(track) - total - 1)))
        fc = (f"[0:v]fps=30,scale=1080:1920,format=yuv420p[v];[1:a]loudnorm=I=-15:TP=-1.5,aresample=48000[vo];"
              f"[2:a]loudnorm=I=-16:TP=-1.5,aresample=48000,volume=0.16,afade=t=in:d=0.4,afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5[mu];"
              + (f"[3:a]aresample=48000[fx];[vo][mu][fx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95[a]" if sfx_track
                 else f"[vo][mu]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"))
        cmd = ["ffmpeg", "-y", "-v", "error", *vin, "-i", vw, "-ss", str(start), "-i", track, *(["-i", sfx_track] if sfx_track else []),
               "-filter_complex", fc, "-map", "[v]", "-map", "[a]", *venc, "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", "-movflags", "+faststart", tmp_out]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", *vin, "-i", vw, "-filter_complex",
               "[0:v]fps=30,scale=1080:1920,format=yuv420p[v];[1:a]loudnorm=I=-15:TP=-1.5,aresample=48000[a]", "-map", "[v]", "-map", "[a]",
               *venc, "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", "-movflags", "+faststart", tmp_out]
    sh(*cmd)
    # TikTok copy: VOICE ONLY (TikTok muted music+voice and voice+sfx on Oct 28; this isolates the cause)
    tt = f"{base}-tt{int(time.time()) % 100000}.mp4"; tmp_tt = f"{W}/{os.path.basename(tt)}"
    try:
        fct = ("[0:v]fps=30,scale=1080:1920,format=yuv420p[v];[1:a]loudnorm=I=-15:TP=-1.5,aresample=48000[vo];"
               + "[vo]anull[a]")
        sh("ffmpeg", "-y", "-v", "error", *vin, "-i", vw, "-filter_complex", fct,
           "-map", "[v]", "-map", "[a]", *venc, "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", "-movflags", "+faststart", tmp_tt)
        STAGED[tt] = tmp_tt; it["_tt"] = tt
    except Exception as e:
        print(it["id"], "tiktok copy failed:", e)
    # cover image = the finished hook (Facebook otherwise picks a frame from the middle of the Reel; Krishna, Oct 26)
    cover = f"{base}-cover.jpg"; tmp_cover = f"{W}/{os.path.basename(cover)}"
    try:
        sh("ffmpeg", "-y", "-v", "error", "-ss", f"{min(1.0, max(0.1, durs[0] - 0.4)):.2f}", "-i", tmp_out, "-frames:v", "1", "-q:v", "2", tmp_cover)
        STAGED[cover] = tmp_cover; it["_cover"] = cover
    except Exception as e:
        print(it["id"], "cover failed:", e)
    print(it["id"], out, f"{total:.1f}s", "frames:", ", ".join(f"{d:.1f}" for d in durs), "music:", track)
    return out, total, durs

def caption(c):
    if DISCLOSE in c: return c
    key = "\n\nKrishna Rander, Realtor"
    return c.replace(key, f"\n\n{DISCLOSE}{key}", 1) if key in c else c + f"\n\n{DISCLOSE}"

def save(results):
    for attempt in range(6):
        sh("git", "fetch", "-q", "origin", "main"); sh("git", "reset", "-q", "--hard", "origin/main")
        files = []
        for dst, src in STAGED.items(): shutil.copy(src, dst)
        for path, upd in results.items():
            items = json.load(open(path))
            for it in items:
                if it["id"] in upd and (it.get("status") == "pending" or "tt_revoice" in upd[it["id"]]): it.update(upd[it["id"]])
            json.dump(items, open(path, "w"), indent=2); files.append(path)
            files += [u["media_url"].split("/main/", 1)[1] for u in upd.values() if "media_url" in u]
            files += [u["cover_url"].split("/main/", 1)[1] for u in upd.values() if "cover_url" in u]
            files += [u["tt_media_url"].split("/main/", 1)[1] for u in upd.values() if "tt_media_url" in u]
        sh("git", "add", *files)
        if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0: return
        sh("git", "-c", "user.name=kwk-bot", "-c", "user.email=bot@users.noreply.github.com", "commit", "-qm", "Add AI voiceover to Reels")
        if subprocess.run(["git", "push", "-q", "origin", "HEAD:main"]).returncode == 0: return
    sys.exit("could not push voiceover results")

def main():
    jobs = todo()
    if not jobs: print("nothing to do"); return
    results = {}
    try:
        import torch
        from qwen_tts import Qwen3TTSModel
        torch.manual_seed(7)
        m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", dtype=torch.float32)
        ref, ref_text = voice_prompt(); print("voice prompt:", ref_text)
        prompt = m.create_voice_clone_prompt(ref_audio=ref, ref_text=ref_text)
    except Exception as e:
        print("voice setup failed:", e); m = None
    for path, it in jobs:
        revoice = bool(it.get("tt_revoice")) and it.get("status") == "posted"
        upd = {"vo_pending": False}
        try:
            if m is None: raise RuntimeError("voice model unavailable")
            out, total, durs = build(m, prompt, it)
            if revoice:
                results.setdefault(path, {})[it["id"]] = {"tt_media_url": RAW + it["_tt"], "tt_revoice": False}; continue
            upd.update({"media_url": RAW + out, "vo_status": "done", "vo_seconds": round(total, 1),
                        "vo_frame_seconds": [round(d, 2) for d in durs], "caption": caption(it["caption"])})
            if it.get("_cover"): upd["cover_url"] = RAW + it["_cover"]
            if it.get("_tt"): upd["tt_media_url"] = RAW + it["_tt"]
        except Exception as e:
            upd.update({"vo_status": "failed", "vo_error": str(e)[:300]}); print(it["id"], "voiceover failed:", e)
        results.setdefault(path, {})[it["id"]] = upd
    save(results)

if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]: print("run=true" if todo() else "run=false")
    else: main()
