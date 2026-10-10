"""Publish approved, due items from posts/*/schedule.json to Instagram (Graph API, free).
Env: IG_USER_ID, IG_ACCESS_TOKEN. Only items with "approved": true and "status": "pending" are posted."""
import glob, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
API = "https://graph.facebook.com/v21.0"
UID, TOK = os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"]

def call(path, data=None):
    url = f"{API}/{path}"
    if data is None:
        url += ("&" if "?" in url else "?") + "access_token=" + TOK
        req = urllib.request.Request(url)
    else:
        data = dict(data, access_token=TOK)
        req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def publish(item):
    p = {"caption": item.get("caption", "")}
    t = item["type"]
    if t == "feed":
        p["image_url"] = item["media_url"]
    elif t == "story":
        p["media_type"] = "STORIES"
        p["video_url" if item["media_url"].endswith(".mp4") else "image_url"] = item["media_url"]
        p.pop("caption")
    elif t == "reel":
        p["media_type"] = "REELS"; p["video_url"] = item["media_url"]
    else:
        raise ValueError(t)
    cid = call(f"{UID}/media", p)["id"]
    for _ in range(40):
        st = call(f"{cid}?fields=status_code").get("status_code")
        if st == "FINISHED": break
        if st == "ERROR": raise RuntimeError("container error")
        time.sleep(6)
    return call(f"{UID}/media_publish", {"creation_id": cid})["id"]

now = datetime.now(timezone.utc)
for path in sorted(glob.glob("posts/*/schedule.json")):
    items = json.load(open(path)); changed = False
    for it in items:
        if it.get("status") != "pending" or not it.get("approved"): continue
        if datetime.fromisoformat(it["publish_at"]) > now: continue
        try:
            it["ig_media_id"] = publish(it); it["status"] = "posted"
        except Exception as e:
            it["status"] = "failed"; it["error"] = str(e)[:300]
        changed = True
        print(it["id"], it["status"])
    if changed: json.dump(items, open(path, "w"), indent=2)
