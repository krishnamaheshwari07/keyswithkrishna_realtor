"""Publish approved, due items from posts/*/schedule.json to Instagram (Graph API, free).
Env: IG_USER_ID, IG_ACCESS_TOKEN; optional FB_PAGE_ID, FB_PAGE_TOKEN (also cross-posts to the Facebook Page). Only items with "approved": true and "status": "pending" are posted."""
import glob, json, urllib.error, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import tiktok, youtube
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

def fb_get(path, fields):
    q = urllib.parse.urlencode({"fields": fields, "access_token": PTOK})
    try:
        with urllib.request.urlopen(f"{FB}/{path}?{q}", timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:250])

def fb_exists(vid):
    """True if the video shows up on the Page (the status read can fail right after upload even when the post went live)."""
    for path in (f"{PID}/video_reels", f"{PID}/videos", f"{PID}/video_stories"):
        try:
            data = fb_get(path, "id").get("data", [])
            if any(str(x.get("id")) == str(vid) or str(x.get("video_id")) == str(vid) for x in data): return True
        except Exception:
            pass
    return False

def fb_video_check(vid):
    """Wait until Facebook finishes processing an uploaded video; raise if any phase reports an error."""
    st = {}; misses = 0
    for _ in range(30):
        try:
            st = fb_get(vid, "status").get("status", {})
        except RuntimeError as e:
            if "does not exist" not in str(e): raise
            misses += 1   # the status read is not always allowed right after upload (Oct 28): retry, then look for the video on the Page
            if misses >= 4:
                if fb_exists(vid): return
                raise RuntimeError(f"facebook video {vid} not found after upload: " + str(e)[:150])
            time.sleep(15); continue
        phases = {k: (v or {}).get("status") for k, v in st.items() if isinstance(v, dict)}
        if st.get("video_status") == "error" or "error" in phases.values():
            raise RuntimeError("facebook video processing error: " + json.dumps(st)[:220])
        if st.get("video_status") == "ready" or phases.get("publishing_phase") == "complete":
            return
        time.sleep(10)
    raise RuntimeError("facebook video still processing after 5 min: " + json.dumps(st)[:200])

def fb_thumb(vid, img_url):
    """Make the hook frame the Facebook cover (otherwise Facebook picks a frame from the middle; Krishna, Oct 26)."""
    with urllib.request.urlopen(img_url, timeout=60) as r: img = r.read()
    bnd = "kwk" + str(int(time.time() * 1000))
    parts = []
    for k, val in {"access_token": PTOK, "is_preferred": "true"}.items():
        parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{val}\r\n'.encode())
    parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="source"; filename="cover.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + img + b"\r\n")
    body = b"".join(parts) + f"--{bnd}--\r\n".encode()
    req = urllib.request.Request(f"{FB}/{vid}/thumbnails", body, headers={"Content-Type": f"multipart/form-data; boundary={bnd}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:250])

def fb_publish(item):
    t, cap = item["type"], item.get("caption", "")
    url = item.get("media_url", "")
    if t == "feed":
        return fb(f"{PID}/photos", {"url": url, "caption": cap, "published": "true"})["id"]
    if t == "carousel":
        ids = [fb(f"{PID}/photos", {"url": u, "published": "false"})["id"] for u in item["media_urls"]]
        data = {"message": cap}
        for n, i in enumerate(ids): data[f"attached_media[{n}]"] = json.dumps({"media_fbid": i})
        return fb(f"{PID}/feed", data)["id"]
    if t == "story":
        if url.endswith(".mp4"):
            st = fb(f"{PID}/video_stories", {"upload_phase": "start"})
            vid = st["video_id"]
            req = urllib.request.Request(st["upload_url"], headers={"Authorization": "OAuth " + PTOK, "file_url": url}, method="POST")
            urllib.request.urlopen(req, timeout=180).read()
            fb(f"{PID}/video_stories", {"upload_phase": "finish", "video_id": vid})
            fb_video_check(vid)
            return vid
        pid = fb(f"{PID}/photos", {"url": url, "published": "false"})["id"]
        return fb(f"{PID}/photo_stories", {"photo_id": pid}).get("post_id", pid)
    if t == "reel":
        st = fb(f"{PID}/video_reels", {"upload_phase": "start"})
        vid = st["video_id"]
        req = urllib.request.Request(st["upload_url"], headers={"Authorization": "OAuth " + PTOK, "file_url": url}, method="POST")
        urllib.request.urlopen(req, timeout=180).read()
        fin = {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": cap}
        try:
            fb(f"{PID}/video_reels", dict(fin, **({"is_ai_generated": "true"} if item.get("vo_status") == "done" else {})))
        except RuntimeError as e:
            if item.get("vo_status") != "done" or "is_ai_generated" not in str(e): raise
            item["fb_ai_label_error"] = str(e)[:200]; fb(f"{PID}/video_reels", fin)
        fb_video_check(vid)
        if item.get("cover_url"):
            try:
                fb_thumb(vid, item["cover_url"]); item["fb_thumb"] = "set"
            except Exception as e:
                item["fb_thumb"] = "failed: " + str(e)[:200]
        return vid
    raise ValueError(t)

def wait(cid):
    for _ in range(40):
        st = call(f"{cid}?fields=status_code").get("status_code")
        if st == "FINISHED": return
        if st == "ERROR": raise RuntimeError("container error")
        time.sleep(6)

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
        if item.get("vo_status") == "done": p["is_ai_generated"] = "true"   # Meta "AI info" label: the voiceover is Krishna's AI-cloned voice (Oct 28)
        if item.get("cover_url"): p["cover_url"] = item["cover_url"]   # hook frame as the Instagram cover
        if item.get("trial"):   # Instagram Trial Reel: shown to non-followers first, joins the profile if it performs (Krishna, Oct 25)
            p["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})
    elif t == "carousel":
        kids = []
        for u in item["media_urls"]:
            k = call(f"{UID}/media", {"image_url": u, "is_carousel_item": "true"})["id"]
            wait(k); kids.append(k)
        p["media_type"] = "CAROUSEL"; p["children"] = ",".join(kids)
    else:
        raise ValueError(t)
    while True:   # drop only the optional field Instagram blames (trial first when it says so), never lose the post
        try:
            cid = call(f"{UID}/media", p)["id"]; break
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if "trial_params" in p and ("rial" in body or "is_ai_generated" not in p):
                item["trial_error"] = body[:300]; p.pop("trial_params")
            elif "is_ai_generated" in p:
                item["ai_label_error"] = body[:200]; p.pop("is_ai_generated")
            else: raise
    if "trial_params" in p: item["trial_status"] = "trial"
    wait(cid)
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
        if (it.get("status") == "posted" and it.get("fb_status") == "failed" and "does not exist" in it.get("fb_error", "")
                and not it.get("fb_rechecked") and PID and PTOK and path >= "posts/2026-10-21"):
            import re
            m = re.search(r"ID '(\d+)'", it["fb_error"]); it["fb_rechecked"] = True
            if m and fb_exists(m.group(1)):
                it["fb_status"] = "posted"; it["fb_id"] = m.group(1); it["fb_note"] = "verified on Page after a failed status read"
            changed = True; print(it["id"], "facebook recheck", it["fb_status"])
            continue
        if it.get("status") == "posted" and it.get("tt_resend") and it["type"] == "reel" and tiktok.enabled():
            try:
                it["tt_publish_id"], it["tt_status"] = tiktok.post_video(it); it.pop("tt_error", None)
            except Exception as e:
                it["tt_status"] = "failed"; it["tt_error"] = str(e)[:300]
            if "spam_risk_too_many_pending_share" in it.get("tt_error", "") and it.get("tt_resend_tries", 0) < 300:
                it["tt_resend_tries"] = it.get("tt_resend_tries", 0) + 1; it["tt_status"] = "waiting_inbox"   # inbox full: retry next run (Krishna posts the drafts)
            else:
                it.pop("tt_resend"); it["tt_resent_at"] = now.isoformat(timespec="minutes"); it.pop("tt_resend_tries", None)
            changed = True; print(it["id"], "tiktok resend", it["tt_status"], it.get("tt_error", ""))
            continue
        if it.get("status") == "posted" and it.get("fb_thumb_fix") and it.get("fb_id") and it.get("cover_url") and "fb_thumb" not in it and PID and PTOK:
            try:
                fb_thumb(it["fb_id"], it["cover_url"]); it["fb_thumb"] = "set"
            except Exception as e:
                it["fb_thumb"] = "failed: " + str(e)[:200]
            changed = True; print(it["id"], "facebook cover fix", it["fb_thumb"])
            continue
        if it.get("status") != "pending" or not it.get("approved"): continue
        if datetime.fromisoformat(it["publish_at"]) > now: continue
        # wait (up to 90 min past the slot) for the voiceover workflow; after that post the music-only version
        if it.get("vo_pending") and datetime.fromisoformat(it["publish_at"]) + timedelta(minutes=90) > now: continue
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
        if it["status"] == "posted" and it["type"] == "reel" and tiktok.enabled() and not it.get("tt_skip") and not tiktok.PAUSED:
            try:
                it["tt_publish_id"], it["tt_status"] = tiktok.post_video(it)
            except Exception as e:
                it["tt_status"] = "failed"; it["tt_error"] = str(e)[:300]
                if "spam_risk_too_many_pending_share" in it["tt_error"]: it["tt_resend"] = True; it["tt_status"] = "waiting_inbox"   # retried every run
            print(it["id"], "tiktok", it["tt_status"], it.get("tt_error", ""))
        if it["status"] == "posted" and it["type"] == "reel" and youtube.enabled() and not it.get("yt_status") and not it.get("yt_skip"):   # YouTube Short through YouTube's own API (Oct 29)
            try:
                it["yt_publish_id"], it["yt_status"] = youtube.post_short(it)
            except Exception as e:
                it["yt_status"] = "failed"; it["yt_error"] = str(e)[:300]
            print(it["id"], "youtube", it["yt_status"], it.get("yt_error", ""))
    if changed: json.dump(items, open(path, "w"), indent=2)
