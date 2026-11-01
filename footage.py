"""فوتيج مجاني من Pixabay (الأساسي) أو Pexels (لو عندك مفتاح قديم)."""
import os, random, requests

def _download(url, out_path):
    with requests.get(url, stream=True, timeout=60) as dl:
        dl.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in dl.iter_content(1 << 20):
                f.write(chunk)

def _pixabay(query, used_ids, out_path):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    r = requests.get("https://pixabay.com/api/videos/",
                     params={"key": key, "q": query, "per_page": 20, "safesearch": "true"}, timeout=30)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    random.shuffle(hits)
    for h in hits:
        if h["id"] in used_ids:
            continue
        v = h["videos"]
        pick = next((v[k] for k in ("large", "medium", "small") if v.get(k, {}).get("url")), None)
        if not pick:
            continue
        _download(pick["url"], out_path)
        used_ids.add(h["id"])
        return out_path
    return None

def _pexels(query, used_ids, out_path):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": query, "orientation": "portrait", "per_page": 15}, timeout=30)
    r.raise_for_status()
    vids = r.json().get("videos", [])
    random.shuffle(vids)
    for v in vids:
        if v["id"] in used_ids:
            continue
        files = [f for f in v["video_files"] if f.get("height", 0) > f.get("width", 0) >= 600]
        if not files:
            continue
        files.sort(key=lambda f: abs(f["height"] - 1920))
        _download(files[0]["link"], out_path)
        used_ids.add(v["id"])
        return out_path
    return None

def find_clip(query, used_ids, out_path):
    for fn in (_pixabay, _pexels):
        try:
            res = fn(query, used_ids, out_path)
            if res:
                return res
        except Exception as e:
            print(f"[i] فوتيج '{query}' فشل ({fn.__name__}): {e}")
    return None
