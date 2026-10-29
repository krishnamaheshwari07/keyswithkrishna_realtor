"""YouTube Shorts via Buffer (free, fully automatic, no Google Cloud project): the Reel's MP4 with Krishna's voice and music goes up as a public Short.
Needs the YouTube channel connected in Buffer (Channels > Add) and the BUFFER_API_KEY secret already used for TikTok."""
import json, os, re, tiktok

def _channel():
    cid = os.environ.get("BUFFER_YOUTUBE_CHANNEL")
    if cid: return cid
    for org in tiktok._gql("query { account { organizations { id } } }")["account"]["organizations"]:
        for c in tiktok._gql('query { channels(input: {organizationId: "%s"}) { id service } }' % org["id"])["channels"]:
            if c.get("service", "").lower() == "youtube": return c["id"]
    return None

def _title(cap):
    first = re.split(r"\n", cap.strip())[0].strip()
    first = re.sub(r"#\w+", "", first).strip()
    return (first[:88].rstrip(" .,;:") or "Keys with Krishna") + " #Shorts"

def _desc(cap):
    cap = re.sub(r"(?im)^.*\bcomment\s+(info|checklist)\b.*$", "Call 905-452-4298 for full details.", cap)   # no comment auto-reply on YouTube
    if "#shorts" not in cap.lower(): cap += "\n\n#Shorts"
    return cap[:4900]

def post_short(item):
    cid = _channel()
    if not cid: return None, "no_channel"
    cap = item.get("caption", "")
    sel = "{ ... on PostActionSuccess { post { id } } ... on MutationError { message } }"
    last = None
    for priv in ("public", "PUBLIC"):
        meta = 'metadata: { youtube: { title: %s, privacy: %s, madeForKids: false, isAiGenerated: true, notifySubscribers: false } }' % (json.dumps(_title(cap)), priv)
        q = ('mutation { createPost(input: { text: %s, channelId: "%s", schedulingType: automatic, mode: shareNow, '
             'assets: [{ video: { url: %s } }], %s }) %s }') % (json.dumps(_desc(cap)), cid, json.dumps(item["media_url"]), meta, sel)
        try:
            res = tiktok._gql(q)["createPost"]
        except RuntimeError as e:
            last = str(e)
            if "privacy" in last.lower() or "enum" in last.lower(): continue
            raise
        if res.get("post"): return "buffer:" + res["post"]["id"], "BUFFER_SHARENOW"
        raise RuntimeError("buffer: " + str(res.get("message"))[:250])
    raise RuntimeError(last or "buffer: short not created")
