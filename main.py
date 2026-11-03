"""المنسّق الرئيسي.
كل تشغيل بيكمّل الناقص ليوم بكرة (UTC) لحد ما يوصل لـ 5 فيديوهات مجدولة.
الـ workflow بيشتغل أكتر من مرة في اليوم، فلو فشل مرة التشغيل اللي بعده بيكمّل."""
import argparse, os, random, re, shutil, sys, tempfile, time, datetime as dt
import config, state, sources, scriptgen, factcheck, topicfilter, learning, voice, footage, render

def utcnow():
    return dt.datetime.now(dt.timezone.utc)

def target_day():
    """الجدولة دايمًا لليوم اللي بعده، مش نفس اليوم."""
    return (utcnow() + dt.timedelta(days=1)).date()

def scheduled_for(st, day):
    return [p for p in st.get("published", []) if str(p.get("publish_at", "")).startswith(day.isoformat())]

def slot_times(day, first_index, n):
    out = []
    for i in range(first_index, first_index + n):
        h, m = map(int, config.SLOTS_UTC[i % len(config.SLOTS_UTC)].split(":"))
        t = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=dt.timezone.utc)
        out.append(t + dt.timedelta(minutes=random.randint(-config.SLOT_JITTER_MIN, config.SLOT_JITTER_MIN)))
    return out

def hook_text(script):
    t = script["scenes"][0]["text"].strip()
    first = re.split(r"[.!؟?،,:]", t)[0].strip() or t
    words = first.split()[:9]
    return r"\N".join(" ".join(words[i:i + 3]) for i in range(0, len(words), 3))

def make_video(script, workdir):
    voice_name = random.choice(config.VOICES)
    used_clips, parts, scene_words, offset = set(), [], [], 0.0
    for i, sc in enumerate(script["scenes"]):
        audio = os.path.join(workdir, f"a{i}.mp3")
        dur, words = voice.synth_scene(sc["text"], voice_name, audio)
        dur += 0.15
        clip = None
        for q in (sc.get("query"), script.get("topic_query"), "abstract background"):
            if q:
                clip = footage.find_clip(q, used_clips, os.path.join(workdir, f"c{i}.mp4"))
                if clip:
                    break
        part = os.path.join(workdir, f"s{i}.mp4")
        render.render_scene(clip, audio, dur, part)
        parts.append(part)
        scene_words.append((offset, words))
        offset += dur
    if offset > config.MAX_VIDEO_SECONDS + 2:
        print(f"[!] الفيديو {offset:.0f}ث - أطول من المتوقع")
    ass = os.path.join(workdir, "subs.ass")
    voice.build_ass(scene_words, ass, hook=hook_text(script))
    joined = os.path.join(workdir, "joined.mp4")
    render.concat(parts, joined, workdir)
    music = os.path.join(workdir, "music.m4a")
    try:
        render.make_music(music, offset + 1)
    except Exception as e:
        print(f"[i] الموسيقى فشلت ({e}) - هكمل من غيرها")
        music = None
    final = os.path.join(workdir, "final.mp4")
    render.burn_subs(joined, ass, final, music=music)
    return final

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=config.VIDEOS_PER_DAY, help="العدد المطلوب ليوم بكرة")
    ap.add_argument("--no-upload", action="store_true", help="اعمل الفيديو بس (للتجربة)")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()

    st = state.load()
    st.setdefault("published", [])
    st.setdefault("fails", {})
    learning.refresh_stats(st)
    state.save(st)

    day = target_day()
    existing = len(scheduled_for(st, day))
    full = args.no_upload or learning.confirmed_public(st) is True
    target = args.count if full else min(args.count, config.CANARY_PER_DAY)
    if not full:
        print(f"🐤 وضع الاختبار: {target} فيديو في اليوم لحد ما أول فيديو يتنشر علنًا (الـ Audit غالبًا لسه ما اتوافقش).")
    need = target if args.no_upload else target - existing
    if need <= 0:
        print(f"✅ يوم {day} مكتمل ({existing} فيديو مجدول). مفيش حاجة تتعمل.")
        return 0
    print(f"الهدف: {target} فيديو ليوم {day} | موجود {existing} | ناقص {need}")
    slots = slot_times(day, existing, need)

    candidates = sources.find_candidates(st["used_source_ids"])
    candidates = [c for c in candidates if st["fails"].get(c["id"], 0) < 2]
    print(f"لقيت {len(candidates)} فكرة مرشحة")
    candidates = topicfilter.filter_candidates(candidates, hints=learning.hints(st))

    done = fails = 0
    deadline = time.time() + config.MAX_RUN_MINUTES * 60
    for idea in candidates:
        if done >= need or fails >= 3:
            break
        if time.time() > deadline:
            print("⏱️ خلّصت المدة المسموحة للتشغيل ده - التشغيل الجاي هيكمّل.")
            break
        print(f"\n== [{done + 1}/{need}] {idea['title']} ({idea['channel']}, x{idea['score']:.1f})")
        workdir = tempfile.mkdtemp(prefix="short_")
        try:
            transcript = sources.get_transcript(idea["id"])
            script = scriptgen.generate(idea, transcript)
            script = factcheck.review(script, idea)
            if script is None:
                print("   [x] الفكرة اترفضت من مراجع الحقائق - بنجرب غيرها")
                st["used_source_ids"].append(idea["id"])
                state.save(st)
                continue
            print("   العنوان:", script["title"])
            final = make_video(script, workdir)
            if args.no_upload:
                os.makedirs(args.out, exist_ok=True)
                dest = os.path.join(args.out, f"{done + 1}.mp4")
                shutil.copy(final, dest)
                print("   اتحفظ:", dest)
            else:
                import uploader
                when = slots[done].strftime("%Y-%m-%dT%H:%M:%SZ")
                vid = uploader.upload(final, script, when)
                st["published"].append({"video_id": vid, "title": script["title"], "source": idea["id"],
                                        "source_channel": idea["channel"],
                                        "category": script.get("category", "other"), "publish_at": when})
                print(f"   اترفع {vid} وهيتنشر {when}")
            st["used_source_ids"].append(idea["id"])
            state.save(st)
            done += 1
            fails = 0
        except Exception as e:
            fails += 1
            st["fails"][idea["id"]] = st["fails"].get(idea["id"], 0) + 1
            state.save(st)
            print(f"[!] فشلت الفكرة دي: {type(e).__name__}: {str(e)[:300]}")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        time.sleep(7)

    print(f"\nخلصنا: {done}/{need}")
    if done < need:
        print("⚠️ العدد ناقص. التشغيل الجاي في الـ workflow هيكمّل الباقي تلقائيًا.")
        return 1 if not args.no_upload or done == 0 else 0
    return 0

if __name__ == "__main__":
    sys.exit(main())
