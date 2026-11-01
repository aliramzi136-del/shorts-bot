"""فلتر مواضيع بنداء Gemini واحد: بيستبعد الأفكار اللي مش مناسبة قبل ما نضيع عليها طلبات."""
import json, re
import gemini

PROMPT = """You are the editor of an Arabic YouTube Shorts channel about timeless science, nature, space, history, and how-things-work facts.
Below are numbered titles of high-performing English videos. Pick only those whose TOPIC can become an accurate, safe 40-second educational short.

EXCLUDE: medical/health advice or cancer/disease claims, politics, war and military scenarios, crime, religion, breaking news, AI/tech industry news and predictions, products/ads, personal stories, philosophy word games, and anything that needs very recent facts.

TITLES:
{titles}

Return ONLY JSON: {{"keep": [numbers in order of best fit first]}}"""

def filter_candidates(cands, limit=20):
    cands = cands[:limit]
    if not cands:
        return cands
    titles = "\n".join(f"{i+1}. {c['title']} ({c['channel']})" for i, c in enumerate(cands))
    try:
        text = gemini.call(PROMPT.format(titles=titles), json_mode=True, temperature=0.1)
        m = re.search(r"\{.*\}", text, flags=re.S)
        keep = [int(k) - 1 for k in json.loads(m.group(0)).get("keep", [])]
        picked = [cands[k] for k in dict.fromkeys(keep) if 0 <= k < len(cands)]
        if picked:
            print(f"[i] فلتر المواضيع: {len(picked)} من {len(cands)} مناسبين")
            return picked
    except Exception as e:
        print(f"[i] فلتر المواضيع فشل ({str(e)[:150]}) - هكمل من غيره")
    return cands
