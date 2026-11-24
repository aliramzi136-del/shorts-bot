"""تجهيز النص للنطق: تشكيل + أرقام بالحروف + أسماء أجنبية بحروف عربية (بنداء Gemini واحد)."""
import json, re
import config, gemini, voice

PROMPT = """You prepare Arabic narration for a text-to-speech engine so that every word is pronounced correctly.

For EACH scene below:
- Add full Arabic diacritics (tashkeel) so pronunciation is unambiguous, especially on scientific terms and verbs.
- Write all numbers, years, percentages and units as Arabic words (e.g. 5 -> خمسة, 1969 -> ألف وتسعمئة وتسعة وستين).
- Transliterate foreign names and terms into Arabic letters (with diacritics).
- Do NOT change the meaning, wording, or order. Do NOT merge or split scenes. Keep punctuation.

{notes}SCENES:
{scenes}

Return ONLY JSON: {{"scenes": ["...", "..."]}} with exactly {n} items, in the same order."""

def _notes():
    if not config.PRONUNCIATION_NOTES:
        return ""
    return "Pronunciation notes (follow exactly):\n" + "\n".join(f"- {n}" for n in config.PRONUNCIATION_NOTES) + "\n\n"

def prepare(script):
    """بيضيف مفتاح tts لكل مشهد. لو فشل، النص الأصلي بيتستخدم زي ما هو."""
    scenes = script["scenes"]
    try:
        listing = "\n".join(f"{i + 1}. {s['text']}" for i, s in enumerate(scenes))
        text = gemini.call(PROMPT.format(scenes=listing, n=len(scenes), notes=_notes()), json_mode=True, temperature=0.1)
        m = re.search(r"\{.*\}", text, flags=re.S)
        out = json.loads(m.group(0))["scenes"]
        if len(out) != len(scenes):
            raise ValueError("عدد المشاهد اتغير")
        for s, t in zip(scenes, out):
            base = len(voice.strip_marks(s["text"]))
            new = len(voice.strip_marks(str(t)))
            ok = str(t).strip() and base and 0.6 <= new / base <= 1.8   # يمنع إعادة الكتابة
            s["tts"] = str(t).strip() if ok else s["text"]
        print("   ✔ اتجهز النطق (تشكيل وأرقام)")
    except Exception as e:
        print(f"   [i] تجهيز النطق فشل ({str(e)[:120]}) - هكمل بالنص الأصلي")
        for s in scenes:
            s.setdefault("tts", s["text"])
    return script
