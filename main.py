"""المنسّق الرئيسي: اكتشاف -> فكرة -> سكريبت -> صوت -> فيديو -> رفع وجدولة."""
import argparse, os, random, shutil, tempfile, time, datetime as dt
import config, state, sources, scriptgen, factcheck, voice, footage, render

def schedule_slots(n):
    """مواعيد بكرة (UTC) مع jitter عشان مايبانش نمط ثابت."""
    day = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).date()
    out = []
    for s in config.SLOTS_UTC[:n]:
        h, m = map(int, s.split(":"))
        t = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=dt.timezone.utc)
        t += dt.timedelta(minutes=random.randint(-config.SLOT_JITTER_MIN, config.SLOT_JITTER_MIN))
        out.append(t)
    return out

def make_video(idea, script, workdir):
    voice_name = random.choice(config.VOICES)
    used_clips, parts, scene_words, offset = set(), [], [], 0.0
    for i, sc in enumerate(script["scenes"]):
        audio = os.path.join(workdir, f"a{i}.mp3")
        dur, words = voice.synth_scene(sc["text"], voice_name, audio)
        dur += 0.15
        clip = footage.find_clip(sc.get("query", "nature"), used_clips, os.path.join(workdir, f"c{i}.mp4"))
        part = os.path.join(workdir, f"s{i}.mp4")
        render.render_scene(clip, audio, dur, part)
        parts.append(part)
        scene_words.append((offset, words))
        offset += dur
    if offset > config.MAX_VIDEO_SECONDS + 2:
        print(f"[!] الفيديو {offset:.0f}ث - أطول من المتوقع")
    ass = os.path.join(workdir, "subs.ass")
    voice.build_ass(scene_words, ass)
    joined = os.path.join(workdir, "joined.mp4")
    render.concat(parts, joined, workdir)
    final = os.path.join(workdir, "final.mp4")
    render.burn_subs(joined, ass, final)
    return final

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=config.VIDEOS_PER_DAY)
    ap.add_argument("--no-upload", action="store_true", help="اعمل الفيديو بس (للتجربة)")
    ap.add_argument("--out", default="output", help="فولدر الفيديوهات في وضع التجربة")
    args = ap.parse_args()

    st = state.load()
    candidates = sources.find_candidates(st["used_source_ids"])
    print(f"لقيت {len(candidates)} فكرة مرشحة")
    slots = schedule_slots(args.count)
    done = 0
    fails = 0

    for idea in candidates:
        if done >= args.count:
            break
        print(f"\n== [{done + 1}/{args.count}] {idea['title']} ({idea['channel']}, x{idea['score']:.1f})")
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
            final = make_video(idea, script, workdir)
            if args.no_upload:
                os.makedirs(args.out, exist_ok=True)
                dest = os.path.join(args.out, f"{done + 1}.mp4")
                shutil.copy(final, dest)
                print("   اتحفظ:", dest)
            else:
                when = slots[done].strftime("%Y-%m-%dT%H:%M:%SZ")
                vid = uploader_upload(final, script, when)
                st["published"].append({"video_id": vid, "title": script["title"],
                                        "source": idea["id"], "publish_at": when})
                print(f"   اترفع {vid} وهيتنشر {when}")
            st["used_source_ids"].append(idea["id"])
            state.save(st)
            done += 1
            fails = 0
        except Exception as e:
            fails += 1
            print(f"[!] فشلت الفكرة دي: {type(e).__name__}: {e}")
            if fails >= 3:
                print("[!] 3 فشل ورا بعض - بوقف عشان مضيّعش وقت. راجع الخطأ فوق.")
                break
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        time.sleep(7)  # احترام حدود Gemini المجانية
    print(f"\nخلصنا: {done}/{args.count}")

def uploader_upload(*a):
    import uploader
    return uploader.upload(*a)

if __name__ == "__main__":
    main()
