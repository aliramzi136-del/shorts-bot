"""مراجع الحقائق التلقائي: بيراجع كل ادعاء في السكريبت بالبحث على الإنترنت قبل الإنتاج.
النتيجة: pass (يكمل) / fix (يصلّح ويراجع تاني) / reject (يرفض الفكرة ويجرب غيرها)."""
import json, re, time
import gemini

PROMPT = """You are a strict fact-checker for short educational videos in Arabic.
Below is a script split into scenes. Using web search, verify EVERY factual claim: numbers, dates, names, cause-and-effect, "scientists discovered", and superlatives like "the biggest / first / only".

SCRIPT:
{script}

SOURCE VIDEO TITLE (context only, it may itself be wrong): {title}

Decide:
- "pass": every claim is accurate and well supported by reliable sources.
- "fix": some claims are wrong, exaggerated or unverifiable, but the topic is fine. Return corrected scenes in the same structure: simple Arabic, 5-7 scenes, 90-115 words in total, remove or soften anything unverifiable, keep the hook, keep the final question to the audience, keep each scene's "query".
- "reject": the topic is mostly false or a myth, is medical/health advice, political, about breaking news, or cannot be made accurate.

When in doubt, choose "fix" or "reject", never "pass".

Return ONLY JSON, no markdown:
{{"verdict": "pass|fix|reject", "issues": ["..."], "title": "corrected Arabic title or the same one", "scenes": [{{"text": "", "query": ""}}]}}
"""

def _parse(text):
    text = re.sub(r"```(?:json)?", "", text)
    m = re.search(r"\{.*\}", text, flags=re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None

def _check(script, idea):
    scenes_txt = "\n".join(f"{i+1}. {s['text']}" for i, s in enumerate(script["scenes"]))
    prompt = PROMPT.format(script=f"Title: {script['title']}\n{scenes_txt}", title=idea["title"])
    try:
        text = gemini.call(prompt, search=True, temperature=0.2)
    except Exception as e:
        print(f"   [i] البحث مش متاح ({str(e)[:200]}) - مراجعة بدون بحث")
        text = gemini.call(prompt, json_mode=True, temperature=0.2)
    return _parse(text)

def review(script, idea, max_rounds=2):
    """بيرجع السكريبت الصالح (ممكن يكون معدّل) أو None لو مرفوض."""
    for round_ in range(max_rounds):
        res = _check(script, idea)   # لو الـ API فشل بيرمي خطأ (بيتحسب فشل مش رفض)
        if not res or res.get("verdict") not in ("pass", "fix", "reject"):
            print("   [!] رد المراجع مش مفهوم - بنرفض احتياطيًا")
            return None
        issues = "; ".join(res.get("issues", []))[:300]
        v = res["verdict"]
        print(f"   مراجع الحقائق: {v} {('- ' + issues) if issues else ''}")
        if v == "pass":
            return script
        if v == "reject":
            return None
        scenes = [s for s in res.get("scenes", []) if s.get("text", "").strip()]
        if len(scenes) < 3:
            return None
        script = {**script, "scenes": scenes, "title": res.get("title") or script["title"]}
        time.sleep(6)
    return None  # لسه محتاج تصليح بعد الجولات = مرفوض
