"""صوت (edge-tts) + ترجمة مكتوبة متزامنة مع الكلمات (ASS)."""
import asyncio, subprocess
import edge_tts
import config

def probe_duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path], text=True)
    return float(out.strip())

async def _synth(text, voice, out_path):
    try:
        comm = edge_tts.Communicate(text, voice, rate=config.TTS_RATE, boundary="WordBoundary")
    except TypeError:
        comm = edge_tts.Communicate(text, voice, rate=config.TTS_RATE)
    words = []
    with open(out_path, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7
                words.append((s, s + ch["duration"] / 1e7, ch["text"]))
    return words

def synth_scene(text, voice, out_path):
    """بيرجع (مدة الصوت، [(start,end,word)])"""
    words = asyncio.run(_synth(text, voice, out_path))
    dur = probe_duration(out_path)
    if not words:  # fallback: توزيع متساوي
        toks = text.split()
        step = dur / max(len(toks), 1)
        words = [(i * step, (i + 1) * step, t) for i, t in enumerate(toks)]
    return dur, words

def _ts(t):
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"

def build_ass(scene_words, path, hook=""):
    """scene_words: list of (scene_offset, [(s,e,word)...])"""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {config.VIDEO_W}
PlayResY: {config.VIDEO_H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.SUB_FONT},88,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,2,2,70,70,520,1
Style: Hook,{config.SUB_FONT},104,&H0000E6FF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,9,3,8,60,60,330,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    if hook:
        lines.append(f"Dialogue: 1,{_ts(0)},{_ts(config.HOOK_SECONDS)},Hook,,0,0,0,,{hook}")
    n = config.SUB_WORDS_PER_CHUNK
    for offset, words in scene_words:
        chunks = [words[i:i + n] for i in range(0, len(words), n)]
        for i, ch in enumerate(chunks):
            start = offset + ch[0][0]
            end = offset + (chunks[i + 1][0][0] if i + 1 < len(chunks) else ch[-1][1] + 0.1)
            text = " ".join(w[2] for w in ch)
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{text}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")
