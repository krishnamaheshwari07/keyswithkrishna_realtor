"""Dump Buffer GraphQL input types related to TikTok metadata to data/buffer-schema.json (no secrets)."""
import json, sys
sys.path.insert(0, "scripts")
import tiktok
q = '''query { __schema { types { name kind inputFields { name type { name kind ofType { name kind } } } enumValues { name } } } }'''
types = tiktok._gql(q)["__schema"]["types"]
keep = [t for t in types if any(k in (t["name"] or "").lower() for k in ["tiktok", "metadata", "createpost", "postinput", "assetinput", "videoinput", "sharemode", "schedulingtype"])]
json.dump(keep, open("data/buffer-schema.json", "w"), indent=1)
