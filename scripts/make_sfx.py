"""Synthesize Keys with Krishna's original sound effects (no third-party audio, no licensing): motion/sfx/*.wav, 48 kHz mono."""
import numpy as np, soundfile as sf, os
SR = 48000; rng = np.random.default_rng(7); os.makedirs("motion/sfx", exist_ok=True)
t = lambda d: np.arange(int(SR * d)) / SR
def lp(x, a):   # one-pole low-pass; a may be an array (sweeping cutoff)
    y = np.zeros_like(x); s = 0.0; a = np.broadcast_to(a, x.shape)
    for i in range(len(x)): s += a[i] * (x[i] - s); y[i] = s
    return y
def norm(x, peak=0.7): return (x / (np.abs(x).max() + 1e-9) * peak).astype(np.float32)
def fade(x, ms=4):
    n = int(SR * ms / 1000); x[:n] *= np.linspace(0, 1, n); x[-n:] *= np.linspace(1, 0, n); return x
# whoosh: noise through a sweeping low-pass, swelling then fading (0.42 s)
d = t(0.42); env = np.sin(np.pi * d / d[-1]) ** 2
cut = 0.02 + 0.25 * np.sin(np.pi * d / d[-1]); w = lp(rng.standard_normal(len(d)), cut)
w = w - lp(w, 0.01); sf.write("motion/sfx/whoosh.wav", norm(fade(w * env), 0.6), SR)
# pop: fast pitch drop sine with a tiny click (0.09 s)
d = t(0.09); f = 900 * np.exp(-d * 30) + 180; ph = 2 * np.pi * np.cumsum(f) / SR
p = np.sin(ph) * np.exp(-d * 45); p[:60] += rng.standard_normal(60) * 0.3; sf.write("motion/sfx/pop.wav", norm(fade(p), 0.55), SR)
# thud (stamp): low body + soft noise slap (0.3 s)
d = t(0.30); body = np.sin(2 * np.pi * (70 + 60 * np.exp(-d * 25)) * d) * np.exp(-d * 14)
slap = lp(rng.standard_normal(len(d)), 0.25) * np.exp(-d * 60); sf.write("motion/sfx/thud.wav", norm(fade(body + 0.6 * slap), 0.75), SR)
# tick: short bright click (0.02 s)
d = t(0.02); k = np.sin(2 * np.pi * 2600 * d) * np.exp(-d * 300); sf.write("motion/sfx/tick.wav", norm(fade(k, 1), 0.35), SR)
# ka-ching: drawer "cha" noise + two bell tones with harmonics (0.9 s)
d = t(0.9); bell = np.zeros(len(d))
for f0, st in ((2093, 0.06), (2637, 0.13)):
    m = d >= st; dd = d[m] - st
    bell[m] += sum(a * np.sin(2 * np.pi * f0 * h * dd) for h, a in ((1, 1), (2.76, .35), (5.4, .15))) * np.exp(-dd * 5)
cha = lp(rng.standard_normal(len(d)), 0.5) * np.exp(-d * 40); sf.write("motion/sfx/kaching.wav", norm(fade(0.5 * cha + bell), 0.6), SR)
# riser: rising sine sweep + airy noise, building over 0.7 s
d = t(0.7); f = 220 * (6 ** (d / d[-1])); r = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5 + lp(rng.standard_normal(len(d)), 0.3) * 0.5
r *= (d / d[-1]) ** 1.5; sf.write("motion/sfx/riser.wav", norm(fade(r), 0.45), SR)
print(sorted(os.listdir("motion/sfx")))
