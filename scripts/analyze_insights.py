"""Summarise data/insights.json: format, topic and posting-time performance plus reach-drop / suppression checks.

Usage: python3 scripts/analyze_insights.py [--days 7]
Prints a plain-text summary. Posts younger than 20 hours are left out of comparisons (their numbers are still growing).
"""
import json, statistics, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=-4))  # Toronto (EDT); close enough for hour-of-day buckets
DAYS = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 14
MIN_AGE_H = 20

TOPICS = [  # first match wins
    ("Pre-construction spotlight", ["pre-construction", "precon", "by great gulf", "towns by", "freehold townhomes"]),
    ("Market stats", ["trreb", "crea", "bild", "average selling price", "sold stats", "market", "bank of canada", "policy interest rate"]),
    ("First-time buyer money", ["fhsa", "down payment", "pre-approval", "home buyers' plan", "land transfer", "closing costs", "first-time", "first home"]),
    ("Buying process how-to", ["offer", "inspection", "status certificate", "start to finish", "conditions", "closing"]),
    ("Listing / property", ["bed", "bath", "move-in ready", "just listed"]),
    ("Lifestyle / engagement", ["this or that", "happy ", "neighbourhood", "coffee", "patio", "kitchen", "home office", "fall", "summer"]),
]


def topic_of(caption):
    c = (caption or "").lower()
    for name, keys in TOPICS:
        if any(k in c for k in keys):
            return name
    return "Other"


def num(v):
    """Meta sometimes returns a list (several periods) or a dict (breakdown) instead of a number."""
    if isinstance(v, list):
        return max((num(x) for x in v), default=0)
    if isinstance(v, dict):
        return sum(num(x) for x in v.values())
    return v or 0


def facebook_section(d, now):
    fb = d.get("facebook", {})
    if not fb.get("page"):
        print("\nFacebook: no data (check FB_PAGE_TOKEN)"); return
    print(f"\nFacebook Page '{fb['page'].get('name')}' | followers {fb['page'].get('followers_count')}")
    daily = fb.get("daily", {})
    days = sorted(k for k in daily if "page_media_view" in daily[k])
    if days:
        last, prev = days[-8:-1], days[-15:-8]
        def tot(ks, m): return sum(num(daily[k].get(m)) for k in ks)
        for m, label in (("page_media_view", "views"), ("page_total_media_view_unique", "accounts reached"),
                         ("page_post_engagements", "engagements")):
            print(f"  {label}: last 7 days {tot(last, m)} vs prior 7 days {tot(prev, m)}")
        f = [num(daily[k].get("page_follows")) for k in days if daily[k].get("page_follows") is not None]
        if f:
            print(f"  followers trend: {f[0]} -> {f[-1]} over {len(f)} days")
    rows = []
    for p in fb.get("posts", {}).values():
        m = p.get("metrics") or {}
        if not m or not p.get("created_time"):
            continue
        t = parse(p["created_time"])
        if (now - t).days > DAYS:
            continue
        views = max(num(m.get(k)) for k in ("post_media_view", "post_total_media_view_unique", "blue_reels_play_count", "fb_reels_total_plays"))
        eng = num(m.get("post_reactions_by_type_total")) + num(p.get("comments")) + num(p.get("shares")) + num(m.get("post_clicks"))
        rows.append((views, eng, p.get("scheduled_type") or p["kind"], t.astimezone(TZ), (p.get("caption_start") or "").split("\n")[0][:60]))
    if rows:
        by = defaultdict(list)
        for r in rows:
            by[r[2]].append(r[0])
        print("  by format: " + "; ".join(f"{k} {len(v)} posts, avg views {statistics.mean(v):.1f}" for k, v in sorted(by.items())))
        print("  top posts:")
        for r in sorted(rows, key=lambda r: (-r[0], -r[1]))[:3]:
            print(f"    {r[0]} views, {r[1]} eng | {r[2]} {r[3]:%a %b %d %H:%M} | {r[4]}")


def parse(t):
    return datetime.fromisoformat(t.replace("+0000", "+00:00").replace("Z", "+00:00"))


def summarise(groups, label):
    out = []
    for k, vals in sorted(groups.items(), key=lambda kv: -statistics.mean(v["reach"] for v in kv[1])):
        r = [v["reach"] for v in vals]
        eng = sum(v["eng"] for v in vals)
        out.append(f"  {k:<28} posts {len(vals):>2} | avg reach {statistics.mean(r):5.1f} | median {statistics.median(r):4.1f} | engagements {eng}")
    return f"{label}\n" + "\n".join(out)


def main():
    d = json.load(open("data/insights.json"))
    ig = d.get("instagram", {})
    now = parse(d["updated_at"])
    rows = []
    for pid, p in ig.get("posts", {}).items():
        m = p.get("metrics") or {}
        if m.get("reach") is None or not p.get("timestamp"):
            continue
        t = parse(p["timestamp"])
        age_h = (now - t).total_seconds() / 3600
        if age_h < MIN_AGE_H or age_h > DAYS * 24:
            continue
        eng = sum(m.get(k) or 0 for k in ("likes", "comments", "saved", "shares", "replies"))
        rows.append({"id": pid, "t": t.astimezone(TZ), "kind": p["kind"], "reach": m["reach"], "views": m.get("views") or 0,
                     "eng": eng, "saves": m.get("saved") or 0, "shares": m.get("shares") or 0,
                     "visits": m.get("profile_visits") or 0, "follows": m.get("follows") or 0,
                     "topic": "Story" if p["kind"] == "story" else topic_of(p.get("caption_start")),
                     "cap": (p.get("caption_start") or "").split("\n")[0][:70], "link": p.get("permalink")})
    print(f"Instagram @{ig.get('account', {}).get('username')} | followers {ig.get('account', {}).get('followers_count')} "
          f"| posts compared: {len(rows)} (last {DAYS} days, older than {MIN_AGE_H}h)\n")
    if not rows:
        print("Not enough Instagram data yet.")
        facebook_section(d, now); return
    by = lambda key: {k: [r for r in rows if key(r) == k] for k in {key(r) for r in rows}}
    print(summarise(by(lambda r: r["kind"]), "By format"))
    print(summarise(by(lambda r: r["topic"]), "\nBy topic"))
    slot = lambda r: ("Morning 8-11" if r["t"].hour < 11 else "Midday 11-14" if r["t"].hour < 14 else
                      "Afternoon 14-17" if r["t"].hour < 17 else "Evening 17-20" if r["t"].hour < 20 else "Night 20-24")
    print(summarise(by(slot), "\nBy posting time (Toronto)"))
    print("\nTop 5 posts by reach")
    for r in sorted(rows, key=lambda r: -r["reach"])[:5]:
        print(f"  {r['reach']:>3} reach, {r['views']:>3} views, {r['eng']} eng | {r['kind']:<8} {r['t']:%a %b %d %H:%M} | {r['cap']}")
    print("\nBottom 5 posts by reach")
    for r in sorted(rows, key=lambda r: r["reach"])[:5]:
        print(f"  {r['reach']:>3} reach, {r['views']:>3} views, {r['eng']} eng | {r['kind']:<8} {r['t']:%a %b %d %H:%M} | {r['cap']}")
    tot = {k: sum(r[k] for r in rows) for k in ("saves", "shares", "visits", "follows")}
    print(f"\nTotals: saves {tot['saves']}, shares {tot['shares']}, profile visits {tot['visits']}, follows from posts {tot['follows']}")

    # ---- reach drop / suppression checks
    daily = ig.get("daily", {})
    days = sorted(k for k in daily if "reach" in daily[k])
    print("\nAccount reach by day (last 14):", ", ".join(f"{k[5:]}={daily[k]['reach']}" for k in days[-14:]))
    flags = []
    last7 = [daily[k]["reach"] for k in days[-8:-1]]  # skip today (partial)
    prev7 = [daily[k]["reach"] for k in days[-15:-8]]
    if last7 and prev7 and statistics.mean(prev7) > 0:
        ch = (statistics.mean(last7) - statistics.mean(prev7)) / statistics.mean(prev7) * 100
        print(f"7-day avg account reach {statistics.mean(last7):.1f} vs prior 7 days {statistics.mean(prev7):.1f} ({ch:+.0f}%)")
        if ch <= -40:
            flags.append(f"account reach fell {ch:.0f}% week over week")
    for k in days[-7:-1]:
        i = days.index(k)
        base = [daily[x]["reach"] for x in days[max(0, i - 7):i]]
        if len(base) >= 4 and statistics.mean(base) >= 10 and daily[k]["reach"] < 0.4 * statistics.mean(base):
            flags.append(f"sudden drop on {k}: {daily[k]['reach']} vs ~{statistics.mean(base):.0f}")
    nf = [daily[k]["reach_by_follow_type"] for k in days if "reach_by_follow_type" in daily[k]]
    if nf:
        f, n = sum(x.get("FOLLOWER", 0) for x in nf), sum(x.get("NON_FOLLOWER", 0) for x in nf)
        share = n / (f + n) * 100 if f + n else 0
        print(f"Non-follower share of reach: {share:.0f}% ({n} of {f + n})")
        if f + n >= 20 and share < 15:
            flags.append(f"non-follower reach only {share:.0f}% (possible distribution limit)")
    reels = [r for r in rows if r["kind"] == "reel"]
    zero = [r for r in reels if r["reach"] <= 1]
    if len(reels) >= 3 and len(zero) / len(reels) >= 0.5:
        flags.append(f"{len(zero)} of {len(reels)} reels reached 1 account or fewer")
    q = ig.get("account", {}).get("publishing_quota", {})
    if q:
        print(f"Publishing quota used: {q.get('quota_usage')} of {q.get('config', {}).get('quota_total')} in 24h")
    fol = d.get("instagram", {}).get("followers_by_day", {})
    if len(fol) > 1:
        ks = sorted(fol)
        print(f"Followers: {fol[ks[0]]} on {ks[0]} -> {fol[ks[-1]]} on {ks[-1]}")
    print("\nSuppression / drop flags: " + ("; ".join(flags) if flags else "none"))
    facebook_section(d, now)


if __name__ == "__main__":
    main()
