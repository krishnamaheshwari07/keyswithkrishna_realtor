"""Diagnostic: find the Facebook place (Page) ID for Mississauga, Ontario, for Instagram/Facebook location tags. Writes data/location-lookup.json (no secrets)."""
import json, os, urllib.request, urllib.parse, urllib.error
FB = "https://graph.facebook.com/v21.0"
toks = {"page": os.environ.get("FB_PAGE_TOKEN"), "ig": os.environ.get("IG_ACCESS_TOKEN")}
out = {}
def get(path, tok, **p):
    p["access_token"] = tok
    try:
        with urllib.request.urlopen(f"{FB}/{path}?{urllib.parse.urlencode(p)}", timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e: return {"error": e.read().decode()[:300]}
for name, tok in toks.items():
    if not tok: continue
    out["search_" + name] = get("pages/search", tok, q="Mississauga, Ontario", fields="id,name,location,verification_status,link")
    out["places_" + name] = get("search", tok, type="place", q="Mississauga", fields="id,name,location")
pid = os.environ.get("FB_PAGE_ID")
if pid and toks["page"]:
    out["page_posts_place"] = get(f"{pid}/posts", toks["page"], fields="id,place{id,name,location},created_time", limit=25)
if pid and toks["page"]:
    out["page_videos_place"] = get(f"{pid}/videos", toks["page"], fields="id,title,description,place{id,name,location},created_time", limit=25)
    out["page_reels_place"] = get(f"{pid}/video_reels", toks["page"], fields="id,description,place{id,name,location},created_time", limit=25)
    out["page_feed_place"] = get(f"{pid}/feed", toks["page"], fields="id,message,place{id,name,location},created_time", limit=25)
json.dump(out, open("data/location-lookup.json", "w"), indent=1); print(json.dumps(out, indent=1)[:3000])
