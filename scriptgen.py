"""كتابة سكريبت عربي أصلي بـ Gemini (free tier) - بيختار الموديل المتاح تلقائيًا."""
import json, re
import config, gemini

PROMPT = """You are a scriptwriter for a viral Arabic YouTube Shorts channel about: {niche} ({desc}).

An English video in this niche performed exceptionally well. Use it ONLY as topic inspiration:
Title: {title}
Description: {description}
Transcript excerpt: {transcript}

TASK: Extract the core topic, pick a FRESH angle, and write a brand-new ORIGINAL script in simple Modern Standard Arabic that sounds natural when spoken aloud. Do NOT translate or closely paraphrase the source.

RULES:
- 85-105 words of narration in total (about 32-42 seconds). Never longer.
- The first sentence is a strong hook (a question or surprising claim), under 12 words.
- Use only well-established, verifiable facts. Never invent statistics, quotes, names, or dates. If unsure, speak generally.
- Avoid medical/health advice, politics, religion, breaking news, and crime. Prefer timeless science, nature, space, history and how-things-work topics.
- Prefer a curiosity question for the Arabic title and hook (why / what if / how), but only when it fits the topic naturally.
- Near the end: a short question that invites comments, then ONE very short follow line (e.g. "تابعنا لحقيقة جديدة كل يوم") as the last sentence.
- Split into 5-7 scenes. Each scene has "text" (1-2 short Arabic sentences, no emojis, no tashkeel), "query" and "alt". The visuals MUST match what that scene says: "query" = the specific physical subject being discussed, in 2-3 English words, searchable in a stock photo/video library (e.g. "black hole", "spider web", "human brain", "volcano eruption", "ocean current"); "alt" = a broader but still relevant fallback (e.g. "galaxy stars", "spider", "neurons", "lava"). Never use abstract words (idea, power, secret, mystery).
- "title": Arabic, max 60 chars, curiosity-driven but honest.
- "description": 2 short Arabic sentences.
- "tags": 6 tags (Arabic and English), no '#'.
- "category": exactly one of: space, earth, animals, human-body, physics, chemistry, history, how-it-works, other.
- "topic_query": 2 English words for a generic stock-footage search that fits the whole topic.

Return ONLY valid JSON:
{{"title": "", "description": "", "tags": [], "category": "", "topic_query": "", "scenes": [{{"text": "", "query": "", "alt": ""}}]}}
"""

def generate(idea, transcript):
    prompt = PROMPT.format(niche=config.NICHE_NAME, desc=config.NICHE_DESCRIPTION,
                           title=idea["title"], description=idea["description"],
                           transcript=transcript or "(not available)")
    for _ in range(3):
        raw = gemini.call(prompt, json_mode=True)
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
