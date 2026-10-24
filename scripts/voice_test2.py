"""Voice-clone shoot-out v4 (English) for Keys with Krishna. Free, commercial-use models only (Apache-2.0):
VoxCPM2 (openbmb) and Qwen3-TTS 1.7B Base (Qwen). Both clone in 'continuation' mode: they get a clip of Krishna's
Reel PLUS its exact transcript and carry on speaking in the same voice, pace and accent.
Usage: python scripts/voice_test2.py voxcpm|qwen"""
import os, sys, glob, json, subprocess
import numpy as np, soundfile as sf
ENGINE = sys.argv[1]
W = "/tmp/vt"; os.makedirs(W, exist_ok=True); os.makedirs("voice-tests", exist_ok=True)
for f in glob.glob(f"voice-tests/v4-{ENGINE}-*.mp3"): os.remove(f)
def sh(*a): subprocess.run(list(a), check=True)
raw = f"{W}/reels.wav"
sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:VOICE_KEY_EN2",
   "-in", "data/voice/ref-reels-en.wav.enc", "-out", raw)
src = raw
try:   # remove background music, keep only the voice
    sh("python", "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", f"{W}/sep", raw)
    src = f"{W}/vocals.wav"
    sh("ffmpeg", "-y", "-v", "error", "-i", glob.glob(f"{W}/sep/htdemucs/*/vocals.wav")[0], "-ac", "1", "-ar", "24000",
       "-af", "highpass=f=70,loudnorm=I=-18:TP=-2", src)
except Exception as e:
    print("demucs failed, using raw audio:", e)
# Transcribe with word timings, then cut each Reel's clip at a sentence/phrase end (9-15 s) so audio and text match exactly.
from faster_whisper import WhisperModel
wm = WhisperModel("small.en", device="cpu", compute_type="int8")
segs = list(wm.transcribe(src, language="en", word_timestamps=True, vad_filter=False)[0])
words = [w for s in segs for w in s.words]
def clip(t0, t1, name):
    ws = [w for w in words if w.start >= t0 and w.end <= t1]
    best = None
    for i, w in enumerate(ws):
        dur = w.end - ws[0].start
        if dur > 15.5: break
        if dur >= 8 and (w.word.strip()[-1:] in ".!?," or i == len(ws) - 1 or ws[i + 1].start - w.end > 0.25):
            best = i
    if best is None: best = min(len(ws) - 1, 30)
    a, b = max(ws[0].start - 0.15, 0), ws[best].end + 0.2
    out = f"{W}/{name}.wav"
    sh("ffmpeg", "-y", "-v", "error", "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", src, out)
    text = "".join(w.word for w in ws[:best + 1]).strip()
    print(name, f"{b - a:.1f}s", "|", text)
    return out, text
REFS = {"A": clip(0.0, 27.3, "reel1"), "B": clip(27.3, 57.4, "reel2")}
TEXT = ("Buying in Halton Hills? Here are three closing costs nobody warns you about! "
        "Number one, land transfer tax. Ontario charges it on most purchases, but first-time buyers can get up to four thousand dollars back. "
        "Number two, legal fees and disbursements. Number three, title insurance and adjustments, like prepaid property tax. "
        "So before you make an offer, ask for a closing cost estimate. Save this, and call me at nine oh five, four five two, four two nine eight!")
def finish(wav, sr, tag):
    tmp = f"{W}/{tag}.wav"; sf.write(tmp, np.asarray(wav, dtype=np.float32).squeeze(), sr)
    sh("ffmpeg", "-y", "-v", "error", "-i", tmp, "-af",
       "silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.35:stop_threshold=-45dB,loudnorm=I=-16:TP=-1.5",
       "-b:a", "160k", f"voice-tests/v4-{ENGINE}-{tag}.mp3")
if ENGINE == "voxcpm":
    from voxcpm import VoxCPM
    m = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, optimize=False, device="cpu")
    for tag, (ref, txt) in REFS.items():
        wav = m.generate(text=TEXT, prompt_wav_path=ref, prompt_text=txt, reference_wav_path=ref,
                         cfg_value=2.0, inference_timesteps=10)
        finish(wav, m.tts_model.sample_rate, tag); print("done", tag)
else:
    import torch
    from qwen_tts import Qwen3TTSModel
    torch.manual_seed(7)
    m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", dtype=torch.float32)
    for tag, (ref, txt) in REFS.items():
        wavs, sr = m.generate_voice_clone(text=TEXT, language="English", ref_audio=ref, ref_text=txt)
        finish(wavs[0], sr, tag); print("done", tag)
