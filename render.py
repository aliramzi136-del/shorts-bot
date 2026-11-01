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

def burn_subs(video, ass, out):
    _run(["ffmpeg", "-y", "-i", video, "-vf", f"ass={ass}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
          "-c:a", "copy", "-movflags", "+faststart", out])
