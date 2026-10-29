"""TikTok posting for Keys with Krishna (Content Posting API, free).
Env: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_TOKEN_KEY (passphrase that encrypts the stored token),
optional TIKTOK_PRIVACY (default SELF_ONLY until the app passes TikTok's audit), TIKTOK_MODE (direct|draft, default draft until the app passes the audit).
Tokens are kept only in encrypted form in data/tiktok-token.enc.
CLI: python3 scripts/tiktok.py connect <code>   (one-time, run by the 'Connect TikTok' workflow)"""
import json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
API = "https://open.tiktokapis.com/v2"
REDIRECT = "https://krishnamaheshwari07.github.io/keyswithkrishna_realtor/tiktok-callback.html"
TOKFILE = "data/tiktok-token.enc"
KEY, SECRET, PASS = os.environ.get("TIKTOK_CLIENT_KEY"), os.environ.get("TIKTOK_CLIENT_SECRET"), os.environ.get("TIKTOK_TOKEN_KEY")

BUFFER_KEY = os.environ.get("BUFFER_API_KEY")   # free Buffer account with TikTok connected: posts publicly, fully automatic (Krishna, Oct 28)

PAUSED = True   # Oct 28: TikTok mutes every Buffer-posted Reel (voice + music, and music-free too). Held until Krishna picks a fix.

def enabled():
    return bool(BUFFER_KEY) or bool(KEY and SECRET and PASS and os.path.exists(TOKFILE))

def _gql(query):
    r = _req("https://api.buffer.com", {"query": query}, token=BUFFER_KEY)
    if r.get("errors"): raise RuntimeError("buffer: " + json.dumps(r["errors"])[:250])
    return r.get("data", {})

def _buffer_channel():
    cid = os.environ.get("BUFFER_TIKTOK_CHANNEL")
    if cid: return cid
    for org in _gql("query { account { organizations { id } } }")["account"]["organizations"]:
        chans = _gql('query { channels(input: {organizationId: "%s"}) { id service isQueuePaused } }' % org["id"])["channels"]
        for c in chans:
            if c.get("service", "").lower() == "tiktok": return c["id"]
    raise RuntimeError("buffer: no TikTok channel connected")

def post_via_buffer(item):
    cid = _buffer_channel()
    text = json.dumps(caption_for_tiktok(item.get("caption", "")))
    # normal Reels keep their music on TikTok; "tt_nomusic": true sends the music-free copy (e.g. a resend after TikTok removed a sound)
    url = json.dumps(item.get("tt_media_url") if item.get("tt_nomusic") and item.get("tt_media_url") else item["media_url"])
    sel = "{ ... on PostActionSuccess { post { id } } ... on MutationError { message } }"
    last = None
    for mode in ("shareNow", "shareNext", "addToQueue"):
        q = ('mutation { createPost(input: { text: %s, channelId: "%s", schedulingType: automatic, mode: %s, '
             'assets: [{ video: { url: %s, metadata: { thumbnailOffset: 1000 } } }], '
             'metadata: { tiktok: { isAiGenerated: true } } }) %s }') % (text, cid, mode, url, sel)   # TikTok AI-generated content label (cloned voice)
        try:
            res = _gql(q)["createPost"]
        except RuntimeError as e:
            last = str(e)
            if "mode" in last.lower() or "enum" in last.lower(): continue   # try the next scheduling mode
            raise
        if res.get("post"): return "buffer:" + res["post"]["id"], "BUFFER_" + mode.upper()
        raise RuntimeError("buffer: " + str(res.get("message"))[:250])
    raise RuntimeError(last or "buffer: post not created")

def _crypt(data, decrypt=False):
    args = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt", "-pass", "env:TIKTOK_TOKEN_KEY", "-a", "-A"]
    if decrypt: args.append("-d")
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout

def _save(tok):
    tok["obtained_at"] = int(time.time())
    open(TOKFILE, "wb").write(_crypt(json.dumps(tok).encode()))

def _load():
    return json.loads(_crypt(open(TOKFILE, "rb").read(), decrypt=True))

def _req(url, data=None, token=None, form=False, method=None, headers=None, raw=None):
    h = dict(headers or {})
    if token: h["Authorization"] = "Bearer " + token
    body = raw
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode(); h["Content-Type"] = "application/json; charset=UTF-8"
    req = urllib.request.Request(url, body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            t = r.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"tiktok {e.code}: {e.read().decode()[:250]}")

def _token_request(**fields):
    r = _req(f"{API}/oauth/token/", dict(client_key=KEY, client_secret=SECRET, **fields), form=True)
    if "access_token" not in r: raise RuntimeError("tiktok token error: " + json.dumps(r)[:250])
    return r

def connect(code):
    _save(_token_request(code=code, grant_type="authorization_code", redirect_uri=REDIRECT))
    print("TikTok connected for open_id", _load().get("open_id", "?")[:6] + "...")

def access_token():
    tok = _load()
    if time.time() > tok["obtained_at"] + int(tok.get("expires_in", 86400)) - 600:
        tok = _token_request(grant_type="refresh_token", refresh_token=tok["refresh_token"])
        _save(tok)
    return tok["access_token"]

def caption_for_tiktok(cap):
    import re   # TikTok has no comment auto-reply: swap any INFO/CHECKLIST comment line for the phone CTA
    cap = re.sub(r"(?im)^.*\bcomment\s+(info|checklist)\b.*$", "Call 905-452-4298 for full details.", cap)
    return cap[:2200]

def post_video(item):
    if BUFFER_KEY: return post_via_buffer(item)
    tok = access_token()
    with urllib.request.urlopen(item["media_url"], timeout=180) as r:
        video = r.read()
        want = int(r.headers.get("Content-Length") or len(video))
    n = len(video)
    if n != want: raise RuntimeError(f"tiktok: downloaded {n} of {want} bytes")
    mode = os.environ.get("TIKTOK_MODE") or "draft"
    # TikTok: under 5MB upload whole; otherwise chunks of 5-64MB, last chunk (up to 128MB) takes the remainder
    CH = 10 * 1024 * 1024
    chunk = n if n < 5 * 1024 * 1024 else CH
    count = max(1, n // chunk)
    if count == 1: chunk = n
    src = {"source": "FILE_UPLOAD", "video_size": n, "chunk_size": chunk, "total_chunk_count": count}
    if mode == "draft":
        init = _req(f"{API}/post/publish/inbox/video/init/", {"source_info": src}, token=tok)
    else:
        info = _req(f"{API}/post/publish/creator_info/query/", {}, token=tok).get("data", {})
        privacy = os.environ.get("TIKTOK_PRIVACY") or "SELF_ONLY"
        if privacy not in info.get("privacy_level_options", [privacy]): privacy = "SELF_ONLY"
        post = {"title": caption_for_tiktok(item.get("caption", "")), "privacy_level": privacy,
                "disable_comment": False, "disable_duet": False, "disable_stitch": False}
        init = _req(f"{API}/post/publish/video/init/", {"post_info": post, "source_info": src}, token=tok)
    d = init.get("data", {})
    if "upload_url" not in d: raise RuntimeError("tiktok init error: " + json.dumps(init)[:250])
    for i in range(count):
        a = i * chunk; b = n if i == count - 1 else a + chunk
        _req(d["upload_url"], raw=video[a:b], method="PUT",
             headers={"Content-Type": "video/mp4", "Content-Range": f"bytes {a}-{b-1}/{n}", "Content-Length": str(b - a)})
    pid = d["publish_id"]
    for _ in range(30):
        st = _req(f"{API}/post/publish/status/fetch/", {"publish_id": pid}, token=tok).get("data", {})
        s = st.get("status")
        if s in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"): return pid, s
        if s == "FAILED": raise RuntimeError("tiktok failed: " + str(st.get("fail_reason"))[:200])
        time.sleep(10)
    return pid, "PROCESSING"

if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "connect":
    connect(sys.argv[2].strip())

if __name__ == "__main__" and len(sys.argv) == 2 and sys.argv[1] == "test":
    import glob
    reels = [it for f in sorted(glob.glob("posts/*/schedule.json")) for it in json.load(open(f))
             if it["type"] == "reel" and it.get("status") == "posted"]
    pid, status = post_video(reels[-1])
    print("TikTok test post:", reels[-1]["id"], status)
