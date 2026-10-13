"""Publish approved, due items from posts/*/schedule.json to Instagram (Graph API, free).
Env: IG_USER_ID, IG_ACCESS_TOKEN; optional FB_PAGE_ID, FB_PAGE_TOKEN (also cross-posts to the Facebook Page). Only items with "approved": true and "status": "pending" are posted."""
import glob, json, urllib.error, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
API = "https://graph.instagram.com/v21.0"
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

FB = "https://graph.facebook.com/v21.0"
PID, PTOK = os.environ.get("FB_PAGE_ID"), os.environ.get("FB_PAGE_TOKEN")

def fb(path, data, headers=None):
    data = dict(data, access_token=PTOK)
    req = urllib.request.Request(f"{FB}/{path}", urllib.parse.urlencode(data).encode(), headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:250])

def fb_publish(item):
    t, url, cap = item["type"], item["media_url"], item.get("caption", "")
    if t == "feed":
        return fb(f"{PID}/photos", {"url": url, "caption": cap, "published": "true"})["id"]
    if t == "story":
        if url.endswith(".mp4"):
            raise RuntimeError("video stories not supported")
        pid = fb(f"{PID}/photos", {"url": url, "published": "false"})["id"]
        return fb(f"{PID}/photo_stories", {"photo_id": pid}).get("post_id", pid)
    if t == "reel":
        st = fb(f"{PID}/video_reels", {"upload_phase": "start"})
        vid = st["video_id"]
        req = urllib.request.Request(st["upload_url"], headers={"Authorization": "OAuth " + PTOK, "file_url": url}, method="POST")
        urllib.request.urlopen(req, timeout=180).read()
        fb(f"{PID}/video_reels", {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": cap})
        return vid
    raise ValueError(t)

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
        if it.get("status") == "posted" and it.get("fb_backfill") and "fb_status" not in it and PID and PTOK:
            try:
                it["fb_id"] = fb_publish(it); it["fb_status"] = "posted"
            except Exception as e:
                it["fb_status"] = "failed"; it["fb_error"] = str(e)[:300]
            changed = True; print(it["id"], "facebook backfill", it["fb_status"], it.get("fb_error", ""))
            continue
        if it.get("status") != "pending" or not it.get("approved"): continue
        if datetime.fromisoformat(it["publish_at"]) > now: continue
        try:
            it["ig_media_id"] = publish(it); it["status"] = "posted"
        except Exception as e:
            it["status"] = "failed"; it["error"] = str(e)[:300]
        changed = True
        print(it["id"], it["status"])
        if it["status"] == "posted" and PID and PTOK:
            try:
                it["fb_id"] = fb_publish(it); it["fb_status"] = "posted"
            except Exception as e:
                it["fb_status"] = "failed"; it["fb_error"] = str(e)[:300]
            print(it["id"], "facebook", it["fb_status"], it.get("fb_error", ""))
    if changed: json.dump(items, open(path, "w"), indent=2)
