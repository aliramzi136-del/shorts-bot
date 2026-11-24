"""اختيار صورة/فيديو مطابق للمشهد من Pixabay (مجاني): بنقيّم كل نتيجة بتطابق كلمات البحث مع وسومها،
ومش بنختار عشوائي. لو الفيديو مش مطابق بنجرب الصور (مكتبتها أكبر بكتير)."""
import os, re, time, requests

MIN_SCORE = 0.5   # لازم نص كلمات البحث على الأقل تظهر في وسوم النتيجة

def _norm(w):
    w = w.lower().strip()
    return w[:-1] if len(w) > 3 and w.endswith("s") else w

def _score(tags, query):
    words = {_norm(x) for x in re.findall(r"[A-Za-z]+", tags or "")}
    toks = [_norm(t) for t in re.findall(r"[A-Za-z]+", query or "") if len(t) > 2]
    if not toks:
        return 0.0
    return sum(1 for t in toks if t in words) / len(toks)

def _get(url, **params):
    for attempt in range(2):
        time.sleep(0.4)   # احترام حد الطلبات
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429 and attempt == 0:
            time.sleep(30)   # وصلنا حد الطلبات في الدقيقة: نستنى ونعيد
            continue
        r.raise_for_status()
        return r.json()

def _videos(query, key):
    out = []
    for h in _get("https://pixabay.com/api/videos/", key=key, q=query, per_page=30, safesearch="true").get("hits", []):
        v = h.get("videos", {})
        pick = next((v[k] for k in ("large", "medium", "small") if v.get(k, {}).get("url")), None)
        if pick:
            out.append(("video", _score(h.get("tags"), query), h.get("likes", 0), f"v{h['id']}", pick["url"]))
    return out

def _images(query, key):
    out = []
    for orient in ("vertical", "all"):
        hits = _get("https://pixabay.com/api/", key=key, q=query, image_type="photo", orientation=orient,
                    per_page=30, safesearch="true", min_width=700).get("hits", [])
        for h in hits:
            url = h.get("largeImageURL") or h.get("webformatURL")
            if url:
                bonus = 0.05 if orient == "vertical" else 0.0   # الصورة الرأسية أنسب للشورتس
                out.append(("image", _score(h.get("tags"), query) + bonus, h.get("likes", 0), f"i{h['id']}", url))
        if out:
            break
    return out

def _download(url, path):
    with requests.get(url, stream=True, timeout=60) as dl:
        dl.raise_for_status()
        with open(path, "wb") as f:
            for chunk in dl.iter_content(1 << 20):
                f.write(chunk)

def find_visual(queries, used_ids, base_path):
    """بيرجع (النوع، المسار) أو (None, None). النوع: video أو image."""
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None, None
    last_pool = []
    for q in queries:
        if not q:
            continue
        try:
            pool = _videos(q, key) + _images(q, key)
        except Exception as e:
            print(f"[i] بحث '{q}' فشل: {e}")
            continue
        pool = [c for c in pool if c[3] not in used_ids]
        good = [c for c in pool if c[1] >= MIN_SCORE]
        last_pool = pool or last_pool
        if good:
            # الأعلى تطابقًا، وبعدها الفيديو على الصورة، وبعدها الأكتر إعجابًا
            best = max(good, key=lambda c: (round(c[1], 2), c[0] == "video", c[2]))
            return _save(best, used_ids, base_path)
    if last_pool:   # مفيش تطابق كويس: أحسن المتاح بدل لا حاجة
        return _save(max(last_pool, key=lambda c: (c[1], c[2])), used_ids, base_path)
    return None, None

def _save(c, used_ids, base_path):
    kind, _, _, cid, url = c
    path = base_path + (".mp4" if kind == "video" else ".jpg")
    try:
        _download(url, path)
    except Exception as e:
        print(f"[i] التحميل فشل: {e}")
        return None, None
    used_ids.add(cid)
    return kind, path
