"""Voice-clone test for Keys with Krishna (Chatterbox, MIT licence). Decrypts Krishna's reference recordings,
detects which is English vs Hinglish, and renders sample voiceovers into voice-tests/."""
import json, os, subprocess, sys, re
import torch, torchaudio
os.makedirs("voice-tests", exist_ok=True)
refs = {}
for name in ("a4", "a2"):
    out = f"/tmp/ref-{name}.wav"
    subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:VOICE_KEY",
                    "-in", f"data/voice/ref-{name}.wav.enc", "-out", out], check=True)
    refs[name] = out
import whisper
wm = whisper.load_model("small")
info = {}
for n, p in refs.items():
    r = wm.transcribe(p)
    info[n] = {"language": r["language"], "text": r["text"][:300]}
json.dump(info, open("voice-tests/transcripts.json", "w"), indent=1, ensure_ascii=False)
en = next((n for n in info if info[n]["language"] == "en" and not re.search(r"\b(hai|mein|karo|ghar|pehli)\b", info[n]["text"].lower())), "a4")
hi = "a2" if en == "a4" else "a4"
EN = ["Buying in Halton Hills? Here are three closing costs nobody warns you about.",
      "One. Land transfer tax. Ontario charges it on most purchases, but first-time buyers may get up to four thousand dollars back.",
      "Two. Legal fees and disbursements.",
      "Three. Title insurance and adjustments, like prepaid property tax.",
      "Ask for a closing cost estimate before you make an offer.",
      "Save this, and call me at nine oh five, four five two, four two nine eight."]
HR = ["Halton Hills mein ghar le rahe ho? Yeh teen closing costs koi nahi batata.",
      "Pehla. Land transfer tax. Ontario mein yeh almost har purchase pe lagta hai, lekin first-time buyers ko chaar hazaar dollars tak wapas mil sakte hain.",
      "Doosra. Lawyer ki fees aur disbursements.",
      "Teesra. Title insurance aur adjustments, jaise prepaid property tax.",
      "Offer dene se pehle closing cost ka estimate zaroor lo.",
      "Isko save karo, aur mujhe call karo, nine oh five, four five two, four two nine eight pe."]
HD = ["हॉल्टन हिल्स में घर ले रहे हो? ये तीन क्लोज़िंग कॉस्ट्स कोई नहीं बताता।",
      "पहला। लैंड ट्रांसफ़र टैक्स। ओंटारियो में ये लगभग हर परचेज़ पे लगता है, लेकिन फ़र्स्ट-टाइम बायर्स को चार हज़ार डॉलर्स तक वापस मिल सकते हैं।",
      "दूसरा। लॉयर की फ़ीस और डिस्बर्समेंट्स।",
      "तीसरा। टाइटल इंश्योरेंस और एडजस्टमेंट्स, जैसे प्रीपेड प्रॉपर्टी टैक्स।",
      "ऑफ़र देने से पहले क्लोज़िंग कॉस्ट का एस्टिमेट ज़रूर लो।",
      "इसे सेव करो, और मुझे कॉल करो, नाइन ओ फ़ाइव, फ़ोर फ़ाइव टू, फ़ोर टू नाइन एट पे।"]
def render(model, lines, ref, path, **kw):
    parts = []
    for t in lines:
        w = model.generate(t, audio_prompt_path=ref, **kw)
        parts += [w, torch.zeros(1, int(model.sr * 0.35))]
    wav = torch.cat(parts, dim=1)
    torchaudio.save(path + ".wav", wav, model.sr)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path + ".wav", "-af", "loudnorm=I=-16:TP=-1.5", "-b:a", "160k", path + ".mp3"], check=True)
    os.remove(path + ".wav")
from chatterbox.tts import ChatterboxTTS
m = ChatterboxTTS.from_pretrained(device="cpu")
render(m, EN, refs[en], "voice-tests/english", exaggeration=0.5, cfg_weight=0.5)
render(m, HR, refs[hi], "voice-tests/hinglish-roman", exaggeration=0.5, cfg_weight=0.5)
del m
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
mm = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
render(mm, HD, refs[hi], "voice-tests/hinglish-devanagari", language_id="hi", exaggeration=0.5, cfg_weight=0.5)
print("done", info)
