"""Voice-clone test v2 for Keys with Krishna (Chatterbox, MIT licence).
Faster, more energetic delivery: higher exaggeration, lower cfg (faster pace), sentences grouped into longer chunks,
long pauses trimmed, slight pitch-preserving speed-up. Renders 2 variants each for English and Hinglish."""
import os, subprocess
import torch, torchaudio
os.makedirs("voice-tests", exist_ok=True)
for f in os.listdir("voice-tests"):
    if f.endswith(".mp3"): os.remove(os.path.join("voice-tests", f))
def dec(name):
    out = f"/tmp/ref-{name}.wav"
    subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:VOICE_KEY",
                    "-in", f"data/voice/ref-{name}.wav.enc", "-out", out], check=True)
    seg = f"/tmp/ref-{name}-seg.wav"   # a lively middle section of the recording works best as the voice prompt
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "6", "-t", "16", "-i", out, seg], check=True)
    return seg
EN_REF, HI_REF = dec("a2"), dec("a4")   # a2 = English recording, a4 = Hinglish recording (detected in test v1)
EN = ["Buying in Halton Hills? Here are three closing costs nobody warns you about!",
      "Number one, land transfer tax. Ontario charges it on most purchases, but first-time buyers can get up to four thousand dollars back.",
      "Number two, legal fees and disbursements. Number three, title insurance and adjustments, like prepaid property tax.",
      "So before you make an offer, ask for a closing cost estimate. Save this, and call me at nine oh five, four five two, four two nine eight!"]
HI = ["हॉल्टन हिल्स में घर ले रहे हो? तो ये तीन क्लोज़िंग कॉस्ट्स ज़रूर जान लो, जो कोई नहीं बताता!",
      "नंबर वन, लैंड ट्रांसफ़र टैक्स। ओंटारियो में ये लगभग हर घर पे लगता है, लेकिन फ़र्स्ट टाइम बायर्स को चार हज़ार डॉलर्स तक का रिफ़ंड मिल सकता है।",
      "नंबर टू, लीगल फ़ीस और डिस्बर्समेंट्स। नंबर थ्री, टाइटल इंश्योरेंस और एडजस्टमेंट्स, जैसे प्रीपेड प्रॉपर्टी टैक्स।",
      "तो ऑफ़र देने से पहले क्लोज़िंग कॉस्ट का एस्टिमेट ज़रूर ले लो। इसे सेव कर लो, और मुझे कॉल करो, नाइन ओ फ़ाइव, फ़ोर फ़ाइव टू, फ़ोर टू नाइन एट!"]
def render(model, lines, ref, path, tempo=1.08, **kw):
    parts = []
    for t in lines:
        parts += [model.generate(t, audio_prompt_path=ref, **kw), torch.zeros(1, int(model.sr * 0.12))]
    torchaudio.save(path + ".wav", torch.cat(parts, dim=1), model.sr)
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.22:stop_threshold=-45dB,"
          f"atempo={tempo},loudnorm=I=-16:TP=-1.5")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path + ".wav", "-af", af, "-b:a", "160k", path + ".mp3"], check=True)
    os.remove(path + ".wav")
torch.manual_seed(7)
from chatterbox.tts import ChatterboxTTS
m = ChatterboxTTS.from_pretrained(device="cpu")
render(m, EN, EN_REF, "voice-tests/english-A", exaggeration=0.7, cfg_weight=0.3)
render(m, EN, EN_REF, "voice-tests/english-B", exaggeration=0.9, cfg_weight=0.2)
del m
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
mm = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
render(mm, HI, HI_REF, "voice-tests/hinglish-A", language_id="hi", exaggeration=0.7, cfg_weight=0.3)
render(mm, HI, HI_REF, "voice-tests/hinglish-B", language_id="hi", exaggeration=0.9, cfg_weight=0.2)
print("done")
