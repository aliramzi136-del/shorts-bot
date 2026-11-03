"""حلقة التعلم: بتقرا مشاهدات فيديوهاتك المنشورة علنًا (بمفتاح الـ API) وبتطلّع تلميحات لاختيار المواضيع."""
import os, statistics, datetime as dt, requests
import config

API = "https://www.googleapis.com/youtube/v3"

def _parse(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

def refresh_stats(st):
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return
    now = dt.datetime.now(dt.timezone.utc)
    ids = []
    for p in st.get("published", []):
        t = _parse(p.get("publish_at"))
        if t and (now - t).total_seconds() >= config.LEARN_MIN_AGE_HOURS * 3600:
            ids.append(p["video_id"])
    stats = st.setdefault("stats", {})
    for i in range(0, len(ids), 50):
        try:
            r = requests.get(f"{API}/videos", params={"part": "statistics", "key": key,
                             "id": ",".join(ids[i:i + 50])}, timeout=30)
            r.raise_for_status()
            for it in r.json().get("items", []):   # الفيديوهات العامة بس هي اللي بترجع
                s = it["statistics"]
                stats[it["id"]] = {"views": int(s.get("viewCount", 0)),
                                   "likes": int(s.get("likeCount", 0))}
        except Exception as e:
            print(f"[i] تحديث الإحصائيات فشل: {e}")

def hints(st):
    """نص تلميحات للفلتر، أو "" لو لسه مفيش بيانات كفاية."""
    stats = st.get("stats", {})
    rows = [p for p in st.get("published", []) if p.get("video_id") in stats]
    if len(rows) < config.LEARN_MIN_VIDEOS:
        return ""
    by_cat = {}
    for p in rows:
        by_cat.setdefault(p.get("category", "other"), []).append(stats[p["video_id"]]["views"])
    ranked = sorted(((statistics.mean(v), c, len(v)) for c, v in by_cat.items()), reverse=True)
    if len(ranked) < 2:
        return ""
    best = ", ".join(f"{c} (avg {m:.0f} views, {n} videos)" for m, c, n in ranked[:3])
    worst = ", ".join(f"{c} (avg {m:.0f})" for m, c, n in ranked[-2:])
    return (f"Our own channel's results so far. Best categories: {best}. Weakest: {worst}. "
            "Prefer topics close to the best categories and avoid the weakest, but keep some variety.")

def confirmed_public(st):
    """True لو فيه فيديو من اللي رفعناه بقى علني فعلًا (يتشاف بمفتاح الـ API).
    False لو مفيش (غالبًا الـ Audit لسه ما اتوافقش والفيديوهات مقفولة). None لو مقدرناش نتأكد."""
    key = os.environ.get("YOUTUBE_API_KEY")
    now = dt.datetime.now(dt.timezone.utc)
    ids = []
    for p in st.get("published", []):
        t = _parse(p.get("publish_at"))
        if t and dt.timedelta(hours=3) <= (now - t) <= dt.timedelta(days=14):
            ids.append(p["video_id"])
    if not ids:
        return False
    if not key:
        return None
    try:
        r = requests.get(f"{API}/videos", params={"part": "id", "key": key, "id": ",".join(ids[:50])}, timeout=30)
        r.raise_for_status()
        return len(r.json().get("items", [])) > 0
    except Exception as e:
        print(f"[i] مقدرتش أتأكد من حالة الفيديوهات: {e}")
        return None
