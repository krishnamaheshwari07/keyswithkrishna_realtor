"""Voice-clone test v3 (English) for Keys with Krishna (Chatterbox, MIT licence).
Voice prompt = Krishna's own Reel audio (2 Reels, Oct 24), background music removed with Demucs,
so the clone copies his real on-camera energy and pace. Renders 3 English variants."""
import os, subprocess, glob
import torch, torchaudio
os.makedirs("voice-tests", exist_ok=True)
for f in glob.glob("voice-tests/english-*.mp3"): os.remove(f)
W = "/tmp/vt"; os.makedirs(W, exist_ok=True)
raw = f"{W}/reels-en.wav"
subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:VOICE_KEY_EN2",
                "-in", "data/voice/ref-reels-en.wav.enc", "-out", raw], check=True)
# Reel 1 speech = 0-27.3 s of this file, Reel 2 speech = 27.3-57.4 s. Strip music/room sound, keep the voice.
src = raw
try:
    subprocess.run(["python", "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", f"{W}/sep", raw], check=True)
    v = glob.glob(f"{W}/sep/htdemucs/*/vocals.wav")[0]
    src = f"{W}/vocals.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", v, "-ac", "1", "-ar", "24000", "-af", "highpass=f=70,loudnorm=I=-18:TP=-2", src], check=True)
    print("demucs: vocals isolated")
except Exception as e:
    print("demucs failed, using raw audio:", e)
def cut(start, dur, name):
    out = f"{W}/{name}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", src, out], check=True)
    return out
REF1 = cut(1.0, 11, "ref-reel1")    # Reel 1, talking to camera
REF2 = cut(28.5, 11, "ref-reel2")   # Reel 2
EN = ["Buying in Halton Hills? Here are three closing costs nobody warns you about!",
      "Number one, land transfer tax. Ontario charges it on most purchases, but first-time buyers can get up to four thousand dollars back.",
      "Number two, legal fees and disbursements. Number three, title insurance and adjustments, like prepaid property tax.",
      "So before you make an offer, ask for a closing cost estimate. Save this, and call me at nine oh five, four five two, four two nine eight!"]
def render(model, lines, ref, path, tempo=1.03, **kw):
    parts = []
    for t in lines:
        parts += [model.generate(t, audio_prompt_path=ref, **kw), torch.zeros(1, int(model.sr * 0.10))]
    torchaudio.save(path + ".wav", torch.cat(parts, dim=1), model.sr)
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.2:stop_threshold=-45dB,"
          f"atempo={tempo},loudnorm=I=-16:TP=-1.5")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path + ".wav", "-af", af, "-b:a", "160k", path + ".mp3"], check=True)
    os.remove(path + ".wav")
from chatterbox.tts import ChatterboxTTS
m = ChatterboxTTS.from_pretrained(device="cpu")
torch.manual_seed(7); render(m, EN, REF1, "voice-tests/english-A", exaggeration=0.6, cfg_weight=0.3)
torch.manual_seed(7); render(m, EN, REF2, "voice-tests/english-B", exaggeration=0.6, cfg_weight=0.3)
torch.manual_seed(7); render(m, EN, REF1, "voice-tests/english-C", exaggeration=0.8, cfg_weight=0.25)
print("done")
