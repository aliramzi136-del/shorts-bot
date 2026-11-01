"""كتابة سكريبت عربي أصلي بـ Gemini (free tier)."""
import os, json, re, time, requests
import config

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

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

def _call(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "responseMimeType": "application/json"}}
    for attempt in range(4):
        r = requests.post(URL, params={"key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=90)
        if r.status_code in (429, 500, 503):
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError("Gemini مش بيرد")

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
