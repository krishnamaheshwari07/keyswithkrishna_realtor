"""Collect free Instagram + Facebook Page insights with the Meta Graph API and save them to data/insights.json.

Also writes data/insights-permissions.json: a per-metric check of what the existing tokens can read.
Env (same secrets as publish.py): IG_USER_ID, IG_ACCESS_TOKEN, FB_PAGE_ID, FB_PAGE_TOKEN.
Standard library only. Tokens are never printed or saved.

Usage:  python3 scripts/insights.py            # check permissions, then collect
        python3 scripts/insights.py --check    # permission check only
"""
import glob, json, os, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

VER = os.environ.get("GRAPH_VERSION", "v23.0")
IG_API = f"https://graph.instagram.com/{VER}"
FB_API = f"https://graph.facebook.com/{VER}"
UID, ITOK = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
PID, PTOK = os.environ.get("FB_PAGE_ID"), os.environ.get("FB_PAGE_TOKEN")
DATA = "data/insights.json"
PERMS = "data/insights-permissions.json"
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()

# Metrics per Instagram media kind. Each is tried as a batch first, then one by one.
IG_MEDIA_METRICS = {
    "feed": ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions", "profile_visits", "follows"],
    "carousel": ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions", "profile_visits", "follows"],
    "reel": ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions",
             "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"],
    "story": ["reach", "views", "replies", "shares", "total_interactions", "follows", "profile_visits", "navigation"],
}
IG_DAY_SERIES = ["reach", "follower_count"]                       # period=day time series
IG_DAY_TOTALS = ["views", "profile_views", "accounts_engaged", "total_interactions",
                 "likes", "comments", "saves", "shares", "replies", "website_clicks"]  # metric_type=total_value
FB_PAGE_DAY = ["page_follows", "page_media_view", "page_total_media_view_unique", "page_post_engagements",
               "page_daily_follows_unique", "page_daily_unfollows_unique", "page_impressions_unique"]
FB_POST_METRICS = ["post_media_view", "post_total_media_view_unique", "post_impressions", "post_impressions_unique",
                   "post_engaged_users", "post_clicks", "post_reactions_by_type_total"]
FB_REEL_METRICS = ["blue_reels_play_count", "post_impressions_unique", "post_video_avg_time_watched",
                   "post_video_view_time", "fb_reels_total_plays", "fb_reels_replay_count"]


def scrub(s):
    for t in (ITOK, PTOK):
        if t:
            s = s.replace(t, "***")
    return s


def get(base, path, params, token):
    """GET and return (ok, payload). On failure payload is {'code','subcode','type','message'}."""
    q = dict(params, access_token=token)
    url = f"{base}/{path}?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return True, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
        except Exception:
            err = {"message": f"HTTP {e.code}"}
        return False, {"code": err.get("code"), "subcode": err.get("error_subcode"), "type": err.get("type"),
                       "message": scrub(str(err.get("message", ""))[:300])}
    except Exception as e:  # network etc.
        return False, {"code": None, "message": scrub(str(e)[:300])}


def paged(base, path, params, token, limit=100):
    out, url_params = [], dict(params)
    ok, d = get(base, path, url_params, token)
    while ok:
        out += d.get("data", [])
        nxt = d.get("paging", {}).get("cursors", {}).get("after")
        if len(out) >= limit or not nxt or not d.get("paging", {}).get("next"):
            break
        url_params["after"] = nxt
        ok, d = get(base, path, url_params, token)
    return ok, (out[:limit] if ok else d)


def probe(name, ok, payload, extra=None):
    row = {"name": name, "ok": bool(ok)}
    if not ok:
        row.update({k: payload.get(k) for k in ("code", "subcode", "message")})
    if extra:
        row.update(extra)
    return row


def ts(d):  # unix seconds at UTC midnight
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def values_of(d):
    """Flatten an /insights response into {metric: value or {breakdown..}}."""
    out = {}
    for m in d.get("data", []):
        v = m.get("values")
        if v:
            out[m["name"]] = v[0].get("value") if len(v) == 1 else [x.get("value") for x in v]
        elif "total_value" in m:
            out[m["name"]] = m["total_value"].get("value")
    return out


# ----------------------------------------------------------------- Instagram
def ig_media_insights(mid, kind):
    """Return (metrics, errors). Batch first, then per-metric fallback so one bad metric doesn't hide the rest."""
    names = IG_MEDIA_METRICS.get(kind, IG_MEDIA_METRICS["feed"])
    ok, d = get(IG_API, f"{mid}/insights", {"metric": ",".join(names)}, ITOK)
    if ok:
        return values_of(d), {}
    metrics, errs = {}, {}
    for n in names:
        ok, d = get(IG_API, f"{mid}/insights", {"metric": n}, ITOK)
        if ok:
            metrics.update(values_of(d))
        else:
            errs[n] = {"code": d.get("code"), "message": d.get("message", "")[:160]}
    return metrics, errs


def kind_of(m):
    pt, mt = m.get("media_product_type", ""), m.get("media_type", "")
    if pt == "STORY":
        return "story"
    if pt == "REELS":
        return "reel"
    return "carousel" if mt == "CAROUSEL_ALBUM" else "feed"


def check_and_collect_ig(store, perms):
    P = perms["instagram"] = {"probes": []}
    if not (UID and ITOK):
        P["error"] = "IG_USER_ID / IG_ACCESS_TOKEN not set"
        return
    ok, me = get(IG_API, "me", {"fields": "user_id,username,followers_count,follows_count,media_count"}, ITOK)
    P["probes"].append(probe("profile (me)", ok, me))
    if not ok:
        return
    store["account"].update({"username": me.get("username"), "followers_count": me.get("followers_count"),
                             "media_count": me.get("media_count"),
                             "snapshot": {str(TODAY): {"followers_count": me.get("followers_count")}}})
    store.setdefault("followers_by_day", {})[str(TODAY)] = me.get("followers_count")

    # --- account-level insights
    daily = store.setdefault("daily", {})
    since, until = ts(TODAY - timedelta(days=29)), ts(TODAY + timedelta(days=1))
    for m in IG_DAY_SERIES:
        ok, d = get(IG_API, f"{UID}/insights", {"metric": m, "period": "day", "since": since, "until": until}, ITOK)
        P["probes"].append(probe(f"account insight: {m}", ok, d))
        if ok:
            for mm in d.get("data", []):
                for v in mm.get("values", []):
                    day = v["end_time"][:10]
                    daily.setdefault(day, {})[m] = v["value"]
    y0, y1 = ts(TODAY - timedelta(days=1)), ts(TODAY)
    for m in IG_DAY_TOTALS:
        ok, d = get(IG_API, f"{UID}/insights", {"metric": m, "period": "day", "metric_type": "total_value",
                                                "since": y0, "until": y1}, ITOK)
        P["probes"].append(probe(f"account insight: {m}", ok, d))
        if ok:
            daily.setdefault(str(TODAY - timedelta(days=1)), {}).update(values_of(d))
    ok, d = get(IG_API, f"{UID}/insights", {"metric": "reach", "period": "day", "metric_type": "total_value",
                                            "breakdown": "follow_type", "since": y0, "until": y1}, ITOK)
    P["probes"].append(probe("account insight: reach by follower / non-follower", ok, d))
    if ok:
        try:
            res = d["data"][0]["total_value"]["breakdowns"][0]["results"]
            daily.setdefault(str(TODAY - timedelta(days=1)), {})["reach_by_follow_type"] = {
                r["dimension_values"][0]: r["value"] for r in res}
        except Exception:
            pass

    # --- media list (feed, reels, carousels) + live stories
    fields = "id,media_type,media_product_type,timestamp,caption,permalink,like_count,comments_count"
    ok, media = paged(IG_API, f"{UID}/media", {"fields": fields, "limit": 50}, ITOK, limit=150)
    P["probes"].append(probe("list media", ok, media))
    items = media if ok else []
    ok, stories = get(IG_API, f"{UID}/stories", {"fields": fields}, ITOK)
    P["probes"].append(probe("list live stories", ok, stories))
    if ok:
        have = {m["id"] for m in items}
        items += [s for s in stories.get("data", []) if s["id"] not in have]

    # --- join to the publish schedule so each post carries its planned type/time/caption
    sched = {}
    for path in glob.glob("posts/*/schedule.json"):
        try:
            for it in json.load(open(path)):
                if it.get("ig_media_id"):
                    sched[str(it["ig_media_id"])] = it
        except Exception:
            pass

    posts = store.setdefault("posts", {})
    first_ok = {}
    for m in items:
        kind = kind_of(m)
        rec = posts.setdefault(m["id"], {})
        rec.update({"kind": kind, "timestamp": m.get("timestamp"), "permalink": m.get("permalink"),
                    "like_count": m.get("like_count"), "comments_count": m.get("comments_count"),
                    "caption_start": (m.get("caption") or "")[:140]})
        s = sched.get(m["id"])
        if s:
            rec.update({"schedule_id": s.get("id"), "scheduled_for": s.get("publish_at")})
        # Only pull insights for posts under 60 days old (keeps API use small); stories only while live.
        age = (NOW - datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))).days if m.get("timestamp") else 0
        if age > 60:
            continue
        metrics, errs = ig_media_insights(m["id"], kind)
        if metrics:
            rec.setdefault("metrics", {}).update(metrics)
            rec["metrics_at"] = NOW.isoformat(timespec="seconds")
            first_ok.setdefault(kind, True)
        if errs:
            rec["metric_errors"] = errs
    # one permission row per kind of media
    for kind in IG_MEDIA_METRICS:
        sample = [r for r in posts.values() if r.get("kind") == kind]
        if not sample:
            P["probes"].append({"name": f"media insights: {kind}", "ok": None, "message": "no posts of this kind found"})
            continue
        good = [r for r in sample if r.get("metrics")]
        errs = [r.get("metric_errors") for r in sample if r.get("metric_errors")]
        row = {"name": f"media insights: {kind}", "ok": bool(good), "posts_with_data": len(good), "posts_seen": len(sample)}
        if errs:
            row["sample_errors"] = errs[0]
        P["probes"].append(row)
    # content publishing limit (also useful as a health signal)
    ok, d = get(IG_API, f"{UID}/content_publishing_limit", {"fields": "quota_usage,config"}, ITOK)
    P["probes"].append(probe("content publishing limit", ok, d))
    if ok:
        store["account"]["publishing_quota"] = d.get("data", [{}])[0]


# ------------------------------------------------------------------ Facebook
def fb_try_metrics(path, names, extra=None):
    got, errs = {}, {}
    for n in names:
        ok, d = get(FB_API, path, dict({"metric": n}, **(extra or {})), PTOK)
        if ok and d.get("data"):
            got.update(values_of(d))
        elif not ok:
            errs[n] = {"code": d.get("code"), "message": d.get("message", "")[:160]}
    return got, errs


def check_and_collect_fb(store, perms):
    P = perms["facebook"] = {"probes": []}
    if not (PID and PTOK):
        P["error"] = "FB_PAGE_ID / FB_PAGE_TOKEN not set"
        return
    ok, d = get(FB_API, "debug_token", {"input_token": PTOK}, PTOK)
    if ok:
        info = d.get("data", {})
        P["token_scopes"] = info.get("scopes")
        P["token_type"] = info.get("type")
        P["token_expires_at"] = info.get("expires_at")
        P["token_data_access_expires_at"] = info.get("data_access_expires_at")
    else:
        P["token_debug_error"] = d.get("message")
    ok, pg = get(FB_API, PID, {"fields": "name,followers_count,fan_count"}, PTOK)
    P["probes"].append(probe("page profile / followers", ok, pg))
    if ok:
        store["page"].update({"name": pg.get("name"), "followers_count": pg.get("followers_count"),
                              "fan_count": pg.get("fan_count")})
        store.setdefault("followers_by_day", {})[str(TODAY)] = pg.get("followers_count")

    daily = store.setdefault("daily", {})
    since, until = ts(TODAY - timedelta(days=28)), ts(TODAY + timedelta(days=1))
    for m in FB_PAGE_DAY:
        ok, d = get(FB_API, f"{PID}/insights", {"metric": m, "period": "day", "since": since, "until": until}, PTOK)
        P["probes"].append(probe(f"page insight: {m}", ok, d))
        if ok:
            for mm in d.get("data", []):
                for v in mm.get("values", []):
                    daily.setdefault(v["end_time"][:10], {})[m] = v["value"]

    pf = "id,created_time,message,permalink_url,status_type,shares,reactions.summary(true).limit(0),comments.summary(true).limit(0)"
    ok, posts = paged(FB_API, f"{PID}/posts", {"fields": pf, "limit": 50}, PTOK, limit=100)
    P["probes"].append(probe("list page posts", ok, posts))
    store_posts = store.setdefault("posts", {})
    sched = {}
    for path in glob.glob("posts/*/schedule.json"):
        try:
            for it in json.load(open(path)):
                if it.get("fb_id"):
                    sched[str(it["fb_id"])] = it
        except Exception:
            pass
    post_metric_ok, post_metric_errs, n_with_metrics = False, {}, 0
    for p in (posts if ok else []):
        rec = store_posts.setdefault(p["id"], {})
        rec.update({"kind": "post", "created_time": p.get("created_time"), "permalink": p.get("permalink_url"),
                    "status_type": p.get("status_type"), "caption_start": (p.get("message") or "")[:140],
                    "reactions": p.get("reactions", {}).get("summary", {}).get("total_count"),
                    "comments": p.get("comments", {}).get("summary", {}).get("total_count"),
                    "shares": (p.get("shares") or {}).get("count", 0)})
        s = sched.get(p["id"]) or sched.get(p["id"].split("_")[-1])
        if s:
            rec.update({"schedule_id": s.get("id"), "scheduled_type": s.get("type"), "scheduled_for": s.get("publish_at")})
        if (NOW - datetime.fromisoformat(p["created_time"].replace("+0000", "+00:00"))).days <= 60:
            got, errs = fb_try_metrics(f"{p['id']}/insights", FB_POST_METRICS)
            if got:
                rec.setdefault("metrics", {}).update(got)
                rec["metrics_at"] = NOW.isoformat(timespec="seconds")
                post_metric_ok = True
                n_with_metrics += 1
            elif errs:
                post_metric_errs = errs
    P["probes"].append({"name": "post insights (reach, views, engagement)", "ok": post_metric_ok,
                        "posts_with_data": n_with_metrics, **({"sample_errors": post_metric_errs} if not post_metric_ok else {})})

    ok, reels = paged(FB_API, f"{PID}/video_reels", {"fields": "id,created_time,description,permalink_url,length", "limit": 25},
                      PTOK, limit=50)
    P["probes"].append(probe("list page reels", ok, reels))
    reel_ok = False
    for r in (reels if ok else []):
        rec = store_posts.setdefault(r["id"], {})
        rec.update({"kind": "reel", "created_time": r.get("created_time"), "permalink": r.get("permalink_url"),
                    "caption_start": (r.get("description") or "")[:140], "length": r.get("length")})
        s = sched.get(r["id"])
        if s:
            rec.update({"schedule_id": s.get("id"), "scheduled_type": s.get("type"), "scheduled_for": s.get("publish_at")})
        got, _ = fb_try_metrics(f"{r['id']}/video_insights", FB_REEL_METRICS)
        if got:
            rec.setdefault("metrics", {}).update(got)
            rec["metrics_at"] = NOW.isoformat(timespec="seconds")
            reel_ok = True
    if ok and reels:
        P["probes"].append({"name": "reel insights", "ok": reel_ok})


# ---------------------------------------------------------------------- main
def classify(perms):
    """Summarise which probes failed because of permissions vs other reasons."""
    missing = []
    for plat in ("instagram", "facebook"):
        for pr in perms.get(plat, {}).get("probes", []):
            if pr.get("ok") is False:
                msg = (pr.get("message") or "").lower()
                perm = pr.get("code") in (10, 200, 190, 3) or "permission" in msg or "scope" in msg
                missing.append({"platform": plat, "what": pr["name"], "permission_problem": perm,
                                "code": pr.get("code"), "message": pr.get("message")})
    perms["failed_probes"] = missing
    unset = [p for p in ("instagram", "facebook") if perms.get(p, {}).get("error")]
    perms["tokens_missing_for"] = unset
    perms["all_insights_readable"] = not missing and not unset


def main():
    os.makedirs("data", exist_ok=True)
    store = {"account": {}, "page": {}}
    if os.path.exists(DATA):
        try:
            store = json.load(open(DATA))
        except Exception:
            pass
    ig, fb = store.setdefault("instagram", {"account": {}, "posts": {}}), store.setdefault("facebook", {"page": {}, "posts": {}})
    ig.setdefault("account", {}); fb.setdefault("page", {})
    perms = {"checked_at": NOW.isoformat(timespec="seconds"), "graph_version": VER}
    check_and_collect_ig(ig, perms)
    check_and_collect_fb(fb, perms)
    classify(perms)
    json.dump(perms, open(PERMS, "w"), indent=2)
    if "--check" not in sys.argv:
        store.pop("account", None); store.pop("page", None)
        store["updated_at"] = NOW.isoformat(timespec="seconds")
        json.dump(store, open(DATA, "w"), indent=1, sort_keys=True)
    bad = perms["failed_probes"]
    print(f"insights: {len(bad)} failed probe(s); ig posts={len(ig.get('posts', {}))} fb posts={len(fb.get('posts', {}))}")
    for b in bad:
        print(" -", b["platform"], b["what"], "| code", b["code"], "|", (b["message"] or "")[:120])


if __name__ == "__main__":
    main()
