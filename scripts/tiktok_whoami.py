"""Diagnostic: which TikTok account the stored token posts to, and the status of the latest inbox upload. Writes data/tiktok-whoami.json (no secrets)."""
import json, glob, sys
sys.path.insert(0, "scripts"); import tiktok
tok = tiktok.access_token(); out = {}
try:
    u = tiktok._req(tiktok.API + "/user/info/?fields=open_id,display_name,username,avatar_url", None, token=tok, method="GET")
    d = u.get("data", {}).get("user", {}); out["account"] = {"display_name": d.get("display_name"), "username": d.get("username")}
except Exception as e: out["account_error"] = str(e)[:300]
pids = [(it["id"], it["tt_publish_id"]) for f in sorted(glob.glob("posts/2026-10-2*/schedule.json")) for it in json.load(open(f))
        if str(it.get("tt_publish_id", "")).startswith("v_inbox")]
for iid, pid in pids[-3:]:
    try: out[iid] = tiktok._req(tiktok.API + "/post/publish/status/fetch/", {"publish_id": pid}, token=tok).get("data")
    except Exception as e: out[iid] = str(e)[:300]
json.dump(out, open("data/tiktok-whoami.json", "w"), indent=1); print(json.dumps(out, indent=1))
