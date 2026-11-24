"""صوت (edge-tts) + ترجمة مكتوبة متزامنة مع الكلمات (ASS)."""
import asyncio, os, re, subprocess
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


# ============ صوت واحد متصل للفيديو كله (أطبع من مشهد مشهد) ============
_MARKS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")

def strip_marks(s):
    """بيشيل التشكيل عشان الترجمة المكتوبة تطلع نضيفة."""
    return _MARKS.sub("", s)

def _trim_trailing(src, dst, extra=""):
    af = "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse" + extra
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", af, dst], check=True)

def _synth_per_scene(texts, voice_name, workdir):
    """طريقة بديلة: مشهد مشهد، بعد قص الصمت الزايد، وبعدين دمج في ملف واحد."""
    pieces, durs, scene_words, offset = [], [], [], 0.0
    for i, t in enumerate(texts):
        raw = os.path.join(workdir, f"p{i}.mp3")
        words = asyncio.run(_synth(t, voice_name, raw))
        wav = os.path.join(workdir, f"p{i}.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
                        "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,apad=pad_dur=0.12",
                        "-ar", "44100", "-ac", "1", wav], check=True)
        d = probe_duration(wav)
        if not words:
            toks = t.split()
            step = max(d - 0.12, 0.1) / max(len(toks), 1)
            words = [(k * step, (k + 1) * step, w) for k, w in enumerate(toks)]
        scene_words.append([(offset + s, offset + e, strip_marks(w)) for s, e, w in words])
        durs.append(d)
        offset += d
        pieces.append(wav)
    lst = os.path.join(workdir, "voice_list.txt")
    with open(lst, "w") as f:
        for p in pieces:
            f.write(f"file '{os.path.abspath(p)}'\n")
    out = os.path.join(workdir, "voice.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", out], check=True)
    return out, durs, scene_words

def synth_script(texts, voice_name, workdir):
    """بيرجع (ملف الصوت، مدة كل مشهد، كلمات كل مشهد بالتوقيت المطلق).
    الأساس: قراءة واحدة متصلة للنص كله (نبرة طبيعية من غير وقفات بين المشاهد)،
    وبعدين تقسيمه على المشاهد بتوقيت الكلمات."""
    counts = [len(t.split()) for t in texts]
    raw = os.path.join(workdir, "voice_raw.mp3")
    try:
        words = asyncio.run(_synth(" ".join(texts), voice_name, raw))
    except Exception as e:
        print(f"[i] القراءة المتصلة فشلت ({e})")
        words = []
    if words and sum(counts) == len(words):
        trimmed = os.path.join(workdir, "voice.m4a")
        _trim_trailing(raw, trimmed)
        scenes, k = [], 0
        for n in counts:
            scenes.append(words[k:k + n])
            k += n
        total = max(probe_duration(trimmed), scenes[-1][-1][1] + 0.25)
        bounds = [0.0] + [(scenes[i - 1][-1][1] + scenes[i][0][0]) / 2 for i in range(1, len(scenes))] + [total]
        durs = [max(bounds[i + 1] - bounds[i], 0.5) for i in range(len(scenes))]
        sw = [[(s, e, strip_marks(w)) for s, e, w in sc] for sc in scenes]
        return trimmed, durs, sw
    print("[i] تقسيم الكلمات مش مطابق - هستخدم الطريقة البديلة (مشهد مشهد)")
    return _synth_per_scene(texts, voice_name, workdir)
