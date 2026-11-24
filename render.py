"""تجميع الفيديو بـ ffmpeg."""
import subprocess, os
import config

def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def render_scene(clip, audio, duration, out):
    W, H = config.VIDEO_W, config.VIDEO_H
    if clip:
        src = ["-stream_loop", "-1", "-i", clip]
    else:  # خلفية بديلة لو مفيش فوتيج
        src = ["-f", "lavfi", "-i", f"color=c=0x0f1b3d:s={W}x{H}:r={config.FPS}"]
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"setsar=1,fps={config.FPS},format=yuv420p")
    _run(["ffmpeg", "-y", *src, "-i", audio, "-t", f"{duration:.3f}",
          "-vf", vf, "-af", "apad,aresample=44100", "-map", "0:v", "-map", "1:a",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-c:a", "aac", "-ac", "2", out])

def concat(parts, out, workdir):
    lst = os.path.join(workdir, "list.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])

def make_music(out, duration):
    """موسيقى خلفية هادية مولّدة من نغمات بسيطة (مفيش حقوق)."""
    d = f"{duration:.2f}"
    notes = [196.0, 246.94, 293.66, 392.0]
    ins = []
    for f in notes:
        ins += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={d}"]
    fc = ("[0][1][2][3]amix=inputs=4:normalize=0,lowpass=f=900,tremolo=f=0.15:d=0.4,"
          f"afade=t=in:d=2,afade=t=out:st={max(duration - 2, 0):.2f}:d=2,volume=0.6[m]")
    _run(["ffmpeg", "-y", *ins, "-filter_complex", fc, "-map", "[m]", "-c:a", "aac", out])

def burn_subs(video, ass, out, music=None):
    if music:
        fc = (f"[0:v]ass={ass}[v];[1:a]volume={config.MUSIC_VOLUME}[m];"
              "[0:a][m]amix=inputs=2:duration=first:normalize=0[a]")
        _run(["ffmpeg", "-y", "-i", video, "-i", music, "-filter_complex", fc,
              "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
              "-crf", "22", "-c:a", "aac", "-movflags", "+faststart", out])
    else:
        _run(["ffmpeg", "-y", "-i", video, "-vf", f"ass={ass}",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
              "-c:a", "copy", "-movflags", "+faststart", out])


def render_clip(clip, duration, out):
    """مشهد فيديو بدون صوت (الصوت بيتركّب مرة واحدة في الآخر)."""
    W, H = config.VIDEO_W, config.VIDEO_H
    if clip:
        src = ["-stream_loop", "-1", "-i", clip]
    else:
        src = ["-f", "lavfi", "-i", f"color=c=0x0f1b3d:s={W}x{H}:r={config.FPS}"]
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"setsar=1,fps={config.FPS},format=yuv420p")
    _run(["ffmpeg", "-y", *src, "-t", f"{duration:.3f}", "-vf", vf, "-an",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out])

def finalize(video, ass, voice, out, music=None):
    """بيركّب الصوت المتصل + الموسيقى + الترجمة على الفيديو."""
    if music:
        fc = (f"[0:v]ass={ass}[v];[2:a]volume={config.MUSIC_VOLUME}[m];"
              "[1:a][m]amix=inputs=2:duration=first:normalize=0[a]")
        cmd = ["ffmpeg", "-y", "-i", video, "-i", voice, "-i", music, "-filter_complex", fc,
               "-map", "[v]", "-map", "[a]"]
    else:
        cmd = ["ffmpeg", "-y", "-i", video, "-i", voice, "-filter_complex", f"[0:v]ass={ass}[v]",
               "-map", "[v]", "-map", "1:a"]
    _run(cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac",
                "-shortest", "-movflags", "+faststart", out])


def render_image(img, duration, out):
    """صورة ثابتة بتتحول لمشهد فيديو بحركة تقريب بطيئة (Ken Burns)."""
    W, H = config.VIDEO_W, config.VIDEO_H
    frames = int(duration * config.FPS) + 2
    vf = (f"scale={int(W*1.2)}:{int(H*1.2)}:force_original_aspect_ratio=increase,crop={int(W*1.2)}:{int(H*1.2)},"
          f"zoompan=z='1+0.12*on/{frames}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={frames}:s={W}x{H}:fps={config.FPS},"
          "format=yuv420p")
    _run(["ffmpeg", "-y", "-i", img, "-t", f"{duration:.3f}", "-vf", vf, "-an",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", out])
