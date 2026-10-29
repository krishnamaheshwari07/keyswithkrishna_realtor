"""Write the status of recent Buffer (TikTok) posts to data/buffer-status.json (no secrets)."""
import json, os, sys
sys.path.insert(0, "scripts")
import tiktok
out = {}
try:
    t = tiktok._gql('query { __type(name: "Post") { fields { name } } }')
    fields = [f["name"] for f in (t.get("__type") or {}).get("fields", [])]
    out["post_fields"] = fields
    want = [f for f in ["id", "status", "error", "errorMessage", "sentAt", "dueAt", "createdAt", "externalLink", "text"] if f in fields]
    org = tiktok._gql("query { account { organizations { id } } }")["account"]["organizations"][0]["id"]
    chans = tiktok._gql('query { channels(input: {organizationId: "%s"}) { id service name isQueuePaused } }' % org)["channels"]
    out["channels"] = chans
    cid = tiktok._buffer_channel()
    sel = " ".join(want).replace("error", "error { message }") if "error" in want else " ".join(want)
    for st in ["sent", "error", "scheduled", "buffer", "draft", "sending"]:
        try:
            r = tiktok._gql('query { posts(input: {organizationId: "%s", filter: {status: %s, channelIds: ["%s"]}}) { edges { node { %s } } } }' % (org, st, cid, sel))
            out[st] = [e["node"] for e in r["posts"]["edges"]][:10]
        except Exception as e:
            out[st] = "query error: " + str(e)[:300]
except Exception as e:
    out["error"] = str(e)[:500]
for k, v in out.items():
    if isinstance(v, list):
        for n in v:
            if isinstance(n, dict) and "text" in n: n["text"] = n["text"][:60]
os.makedirs("data", exist_ok=True)
json.dump(out, open("data/buffer-status.json", "w"), indent=2)
