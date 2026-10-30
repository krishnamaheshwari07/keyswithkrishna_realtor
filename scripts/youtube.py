"""YouTube Shorts for Keys with Krishna, straight to YouTube's own API (free, no third-party tool).
Env: YT_CLIENT_ID, YT_CLIENT_SECRET (Google Cloud OAuth client), TIKTOK_TOKEN_KEY (passphrase that encrypts the stored token, shared with TikTok).
The refresh token is kept only in encrypted form in data/youtube-token.enc.
CLI: python3 scripts/youtube.py connect <code>   (one-time, run by the 'Connect YouTube' workflow)"""
import json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
CID, CSEC, PASS = os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET"), os.environ.get("TIKTOK_TOKEN_KEY")
REDIRECT = "https://krishnamaheshwari07.github.io/keyswithkrishna_realtor/youtube-callback.html"
TOKFILE = "data/youtube-token.enc"

def enabled():
    return bool(CID and CSEC and PASS and os.path.exists(TOKFILE))

def _crypt(data, decrypt=False):
    args = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt", "-pass", "env:TIKTOK_TOKEN_KEY", "-a", "-A"]
    if decrypt: args.append("-d")
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout

def _token_request(**fields):
    body = urllib.parse.urlencode(dict(client_id=CID, client_secret=CSEC, **fields)).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", body), timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"youtube token {e.code}: {e.read().decode()[:250]}")

def connect(code):
    t = _token_request(code=code, grant_type="authorization_code", redirect_uri=REDIRECT)
    if "refresh_token" not in t: raise RuntimeError("youtube: no refresh token returned (use the Connect YouTube page again): " + json.dumps(t)[:200])
    open(TOKFILE, "wb").write(_crypt(json.dumps({"refresh_token": t["refresh_token"]}).encode()))
    print("YouTube connected")

def access_token():
    rt = json.loads(_crypt(open(TOKFILE, "rb").read(), decrypt=True))["refresh_token"]
    return _token_request(grant_type="refresh_token", refresh_token=rt)["access_token"]

def _title(cap):
    first = re.sub(r"#\w+", "", cap.strip().split("\n")[0]).strip()
    return (first[:88].rstrip(" .,;:") or "Keys with Krishna") + " #Shorts"

def _desc(cap):
    cap = re.sub(r"(?im)^.*\bcomment\s+(info|checklist)\b.*$", "Call 905-452-4298 for full details.", cap)   # no comment auto-reply on YouTube
    if "#shorts" not in cap.lower(): cap += "\n\n#Shorts"
    return cap[:4900]

def post_short(item):
    tok = access_token()
    with urllib.request.urlopen(item.get("yt_media_url") or item["media_url"], timeout=180) as r:   # pinned-hook copy when there is one
        video = r.read(); want = int(r.headers.get("Content-Length") or len(video))
    if len(video) != want: raise RuntimeError(f"youtube: downloaded {len(video)} of {want} bytes")
    cap = item.get("caption", "")
    meta = {"snippet": {"title": _title(cap), "description": _desc(cap), "categoryId": "22", "defaultLanguage": "en"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": item.get("vo_status") == "done",
                       "embeddable": True, "publicStatsViewable": True}}
    hdr = {"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8",
           "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(video))}
    init = urllib.request.Request("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                                  json.dumps(meta).encode(), hdr, method="POST")
    try:
        with urllib.request.urlopen(init, timeout=60) as r: loc = r.headers["Location"]
        up = urllib.request.Request(loc, video, {"Content-Type": "video/mp4", "Content-Length": str(len(video))}, method="PUT")
        with urllib.request.urlopen(up, timeout=600) as r: res = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"youtube {e.code}: {e.read().decode()[:250]}")
    st = res.get("status", {})
    if item.get("cover_url"):   # YouTube otherwise picks a mid-Reel frame; show the hook (Krishna, Oct 29)
        try: set_thumb(res["id"], item["cover_url"], tok); item["yt_thumb"] = "set"
        except Exception as e: item["yt_thumb"] = "failed: " + str(e)[:200]
    return res["id"], "UPLOADED_" + str(st.get("privacyStatus", "?")).upper()

def set_thumb(vid, url, tok=None):
    tok = tok or access_token()
    with urllib.request.urlopen(url, timeout=60) as r: img = r.read()
    req = urllib.request.Request(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}", img,
                                 {"Authorization": "Bearer " + tok, "Content-Type": "image/jpeg", "Content-Length": str(len(img))}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"youtube thumbnail {e.code}: {e.read().decode()[:250]}")

if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "connect":
    connect(sys.argv[2].strip())
