"""اكتشاف الفيديوهات الـ Outlier من قنوات المنافسين (قراءة فقط، quota قليلة)."""
import os, re, datetime as dt, requests
import config

API = "https://www.googleapis.com/youtube/v3"

def _get(path, **params):
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    r = requests.get(f"{API}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def _dur_seconds(iso):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s

def channel_info(handle):
    d = _get("channels", part="snippet,statistics,contentDetails", forHandle=handle.lstrip("@"))
    items = d.get("items", [])
    if not items:
        print(f"[!] القناة مش موجودة: {handle}")
        return None
    it = items[0]
    return {
        "title": it["snippet"]["title"],
        "subs": int(it["statistics"].get("subscriberCount", 0)),
        "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"],
    }

def recent_videos(ch):
    d = _get("playlistItems", part="contentDetails", playlistId=ch["uploads"],
             maxResults=config.VIDEOS_PER_CHANNEL)
    ids = [i["contentDetails"]["videoId"] for i in d.get("items", [])]
    if not ids:
        return []
    v = _get("videos", part="snippet,statistics,contentDetails", id=",".join(ids))
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for it in v.get("items", []):
        views = int(it["statistics"].get("viewCount", 0))
        pub = dt.datetime.fromisoformat(it["snippet"]["publishedAt"].replace("Z", "+00:00"))
        age = (now - pub).days
        dur = _dur_seconds(it["contentDetails"].get("duration"))
        if views < config.MIN_VIEWS or not (config.MIN_AGE_DAYS <= age <= config.MAX_AGE_DAYS):
            continue
        if dur > config.MAX_SOURCE_DURATION_SEC or dur < 15:
            continue
        out.append({
            "id": it["id"], "title": it["snippet"]["title"],
            "description": it["snippet"].get("description", "")[:800],
            "channel": ch["title"], "views": views, "age_days": age,
            # الـ Outlier score: المشاهدات نسبةً لحجم القناة
            "score": views / max(ch["subs"], 1000),
        })
    return out

def find_candidates(used_ids):
    pool = []
    for h in config.SOURCE_CHANNELS:
        try:
            ch = channel_info(h)
            if ch:
                pool += recent_videos(ch)
        except Exception as e:
            print(f"[!] فشل {h}: {e}")
    pool = [v for v in pool if v["id"] not in set(used_ids)]
    pool.sort(key=lambda v: v["score"], reverse=True)
    picked, per = [], {}
    for v in pool:
        if per.get(v["channel"], 0) >= config.MAX_PER_CHANNEL_PER_DAY:
            continue
        per[v["channel"]] = per.get(v["channel"], 0) + 1
        picked.append(v)
    return picked

def get_transcript(video_id, max_chars=6000):
    """بيفشل كتير من IPs السحابة (GitHub Actions)، فالسيستم بيكمل من غيره."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            data = YouTubeTranscriptApi().fetch(video_id, languages=["en"])
            text = " ".join(s.text for s in data)
        except AttributeError:
            data = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
            text = " ".join(d["text"] for d in data)
        return text[:max_chars]
    except Exception as e:
        print(f"[i] مفيش transcript ({type(e).__name__}) - هنكمل بالعنوان والوصف")
        return ""
