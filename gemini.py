"""طبقة واحدة للتعامل مع Gemini: اختيار الموديل المتاح + إعادة محاولة ذكية + أخطاء واضحة."""
import os, re, time, requests

BASE = "https://generativelanguage.googleapis.com/v1beta"
_models = []
_dead = set()   # (model, search) اللي فشل بشكل نهائي النهارده

def models():
    if _models:
        return _models
    key = os.environ["GEMINI_API_KEY"]
    names = []
    if os.environ.get("GEMINI_MODEL"):
        names.append(os.environ["GEMINI_MODEL"])
    try:
        r = requests.get(f"{BASE}/models", params={"key": key, "pageSize": 200}, timeout=30)
        r.raise_for_status()
        avail = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
        bad = ("image", "tts", "live", "audio", "embedding", "exp", "robotics", "computer",
               "native", "thinking", "learnlm", "gemma", "vision", "latest", "customtools")
        flash = [n for n in avail if n.startswith("gemini") and "flash" in n and not any(b in n for b in bad)]
        def rank(n):
            m = re.match(r"gemini-(\d+(?:\.\d+)?)", n)
            return (float(m.group(1)) if m else 0, "preview" not in n)
        regular = sorted([n for n in flash if "lite" not in n], key=rank, reverse=True)
        lite = sorted([n for n in flash if "lite" in n], key=rank, reverse=True)
        names += regular[:3] + lite[:2]   # الـ lite عنده حصة مجانية أكبر
    except Exception as e:
        print(f"[i] مقدرتش أجيب قايمة الموديلات: {e}")
    if not names:
        names = ["gemini-flash-latest"]
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    _models.extend(seen)
    print("[i] موديلات هستخدمها بالترتيب:", ", ".join(_models))
    return _models

def call(prompt, json_mode=False, search=False, temperature=0.9, timeout=None):
    timeout = timeout or (120 if search else 75)
    key = os.environ["GEMINI_API_KEY"]
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if search:
        body["tools"] = [{"google_search": {}}]
    elif json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    errors = []
    for model in models():
        if (model, search) in _dead:
            continue
        for attempt in range(2):
            try:
                r = requests.post(f"{BASE}/models/{model}:generateContent",
                                  params={"key": key}, json=body, timeout=timeout)
            except requests.exceptions.RequestException as e:
                # الموديل بطيء أو مش بيرد: نسيبه لباقي التشغيل ونجرب اللي بعده
                errors.append(f"{model}: {type(e).__name__}")
                print(f"[i] {model} مردش في الوقت - هجرب موديل تاني")
                _dead.add((model, search))
                break
            code = r.status_code
            if code == 200:
                try:
                    parts = r.json()["candidates"][0]["content"]["parts"]
                    text = "".join(p.get("text", "") for p in parts)
                    if text.strip():
                        return text
                except (KeyError, IndexError):
                    pass
                errors.append(f"{model}: رد فاضي")
                break
            errors.append(f"{model}: {code} {r.text[:140]!r}")
            if code == 429:
                if "PerDay" in r.text or "limit: 0" in r.text:
                    _dead.add((model, search))   # الحصة اليومية خلصت
                    break
                time.sleep(20)
                continue
            if code in (500, 503):
                time.sleep(10)
                continue
            if code in (400, 403, 404):
                _dead.add((model, search))
            break
    raise RuntimeError("Gemini فشل: " + " | ".join(errors[-4:]))
