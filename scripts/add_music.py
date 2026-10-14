"""Add royalty-free music from posts/audio/ to a Reel (replaces its audio) or turn a Story image into a short video with music.
Usage:
  python3 scripts/add_music.py reel  <in.mp4> <out.mp4> <seed>
  python3 scripts/add_music.py story <in.png> <out.mp4> <seed> [seconds=8]
The seed (e.g. the item id) picks the track and start point, so tracks rotate between posts."""
import glob, hashlib, subprocess, sys

def pick(seed):
    tracks = sorted(glob.glob("posts/audio/*.mp3"))
    if not tracks:
        sys.exit("no tracks in posts/audio")
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return tracks[h % len(tracks)], (h >> 16)

def dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(out)

def audio_args(track, h, length):
    start = h % max(1, int(min(25, dur(track) - length - 1)))
    af = f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.4,afade=t=out:st={max(0, length-1.5):.2f}:d=1.5"
    return ["-ss", str(start), "-i", track], af

def main():
    kind, src, out, seed = sys.argv[1:5]
    track, h = pick(seed)
    if kind == "reel":
        length = dur(src)
        a, af = audio_args(track, h, length)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, *a, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p", "-r", "30", "-g", "30", "-b:v", "3M",
               "-af", af, "-c:a", "aac", "-b:a", "160k", "-t", f"{length:.2f}", "-movflags", "+faststart", out]
    elif kind == "story":
        length = float(sys.argv[5]) if len(sys.argv) > 5 else 8.0
        a, af = audio_args(track, h, length)
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-i", src, *a, "-t", str(length),
               "-vf", "scale=1080:1920,format=yuv420p", "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-r", "30", "-g", "30", "-b:v", "3M",
               "-af", af, "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    else:
        sys.exit(__doc__)
    subprocess.check_call(cmd)
    print(f"{out}: {track}")

main()
