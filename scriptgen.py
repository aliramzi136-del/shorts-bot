"""كتابة سكريبت عربي أصلي بـ Gemini (free tier) - بيختار الموديل المتاح تلقائيًا."""
import os, json, re, time, requests
import config

BASE = "https://generativelanguage.googleapis.com/v1beta"
_models_cache = []

PROMPT = """You are a scriptwriter for a viral Arabic YouTube Shorts channel about: {niche} ({desc}).

An English video in this niche performed exceptionally well. Use it ONLY as topic inspiration:
Title: {title}
Description: {description}
Transcript excerpt: {transcript}

TASK: Extract the core topic, pick a FRESH angle, and write a brand-new ORIGINAL script in simple Modern Standard Arabic that sounds natural when spoken aloud. Do NOT translate or closely paraphrase the source.

RULES:
- 90-115 words of narration in total (about 35-45 seconds).
- The first sentence is a strong hook (a question or surprising claim), under 12 words.
- Use only well-established, verifiable facts. Never invent statistics, quotes, names, or dates. If unsure, speak generally.
- Last line is a short question that invites comments.
- Split into 5-7 scenes. Each scene has "text" (1-2 short Arabic sentences, no emojis, no tashkeel) and "query" (2-3 English words describing a concrete visual for stock footage, e.g. "galaxy stars", "ocean waves").
- "title": Arabic, max 60 chars, curiosity-driven but honest.
- "description": 2 short Arabic sentences.
- "tags": 6 tags (Arabic and English), no '#'.

Return ONLY valid JSON:
{{"title": "", "description": "", "tags": [], "scenes": [{{"text": "", "query": ""}}]}}
"""

def _candidate_models():
    """بيسأل جوجل إيه الموديلات المتاحة لمفتاحك، ويرتّب الأحدث (flash) الأول."""
    if _models_cache:
        return _models_cache
    key = os.environ["GEMINI_API_KEY"]
    forced = os.environ.get("GEMINI_MODEL")
    names = [forced] if forced else []
    try:
        r = requests.get(f"{BASE}/models", params={"key": key, "pageSize": 200}, timeout=30)
        r.raise_for_status()
        avail = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
        bad = ("image", "tts", "live", "audio", "embedding", "exp", "lite", "robotics",
               "computer", "native", "thinking", "learnlm", "gemma", "vision", "latest")
        ok = [n for n in avail if n.startswith("gemini") and "flash" in n and not any(b in n for b in bad)]
        def rank(n):
            m = re.match(r"gemini-(\d+(?:\.\d+)?)", n)
            return (float(m.group(1)) if m else 0, "preview" not in n)
        ok.sort(key=rank, reverse=True)
        names += ok[:4]
        print("[i] موديلات متاحة:", ", ".join(ok[:4]) or "مفيش flash - هجرب الافتراضي")
    except Exception as e:
        print(f"[i] مقدرتش أجيب قايمة الموديلات: {e}")
    names += ["gemini-flash-latest", "gemini-2.5-flash"]
    seen = []
    for n in names:
        if n and n not in seen:
            seen.append(n)
    _models_cache.extend(seen)
    return _models_cache

def _call(prompt):
    key = os.environ["GEMINI_API_KEY"]
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "responseMimeType": "application/json"}}
    last = ""
    for model in _candidate_models():
        for attempt in range(2):
            r = requests.post(f"{BASE}/models/{model}:generateContent",
                              params={"key": key}, json=body, timeout=90)
            if r.status_code in (429, 500, 503):
                last = f"{model}: {r.status_code} {r.text[:150]}"
                time.sleep(8 * (attempt + 1))
                continue
            if r.status_code in (400, 403, 404):
                last = f"{model}: {r.status_code} {r.text[:200]}"
                break  # جرّب الموديل اللي بعده
            r.raise_for_status()
            try:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                last = f"{model}: رد فاضي"
                break
    raise RuntimeError(f"Gemini فشل. آخر خطأ: {last}")

def generate(idea, transcript):
    prompt = PROMPT.format(niche=config.NICHE_NAME, desc=config.NICHE_DESCRIPTION,
                           title=idea["title"], description=idea["description"],
                           transcript=transcript or "(not available)")
    for _ in range(3):
        raw = _call(prompt)
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        try:
            data = json.loads(raw)
            scenes = [s for s in data["scenes"] if s.get("text", "").strip()]
            if len(scenes) >= 3 and data.get("title"):
                data["scenes"] = scenes
                return data
        except Exception:
            pass
    raise RuntimeError("السكريبت اتولد بصيغة غلط")
