"""كل الإعدادات في مكان واحد. عدّل هنا بس."""

# ---------- النيش ----------
NICHE_NAME = "حقائق علمية وغرائب الكون"
NICHE_DESCRIPTION = "حقائق مدهشة عن العلوم والفضاء والجسم البشري والحيوانات والتاريخ الغريب"

# قنوات إنجليزي من نفس النيش (راجع إن الـ handles صح قبل التشغيل)
SOURCE_CHANNELS = [
    "@RealLifeLore", "@Kurzgesagt", "@veritasium", "@AsapSCIENCE",
    "@TheInfographicsShow", "@Vsauce", "@SciShow", "@TomScottGo",
]

# ---------- اكتشاف الـ Outliers ----------
VIDEOS_PER_CHANNEL = 25      # playlistItems = وحدة quota واحدة لكل استدعاء
MIN_VIEWS = 50_000
MIN_AGE_DAYS = 3
MAX_AGE_DAYS = 365
MAX_PER_CHANNEL_PER_DAY = 2  # تنوع في المصادر
MAX_SOURCE_DURATION_SEC = 40 * 60

# ---------- الإنتاج ----------
VOICES = ["ar-SA-HamedNeural", "ar-EG-ShakirNeural"]  # بيتختار واحد عشوائي لكل فيديو
TTS_RATE = "+5%"
VIDEO_W, VIDEO_H, FPS = 1080, 1920, 30
MAX_VIDEO_SECONDS = 58
SUB_WORDS_PER_CHUNK = 3
SUB_FONT = "Noto Sans Arabic"

# ---------- الجدولة (بتوقيت UTC) ----------
# مصر شتاءً = UTC+2 ، السعودية = UTC+3
SLOTS_UTC = ["08:00", "11:30", "15:00", "18:30", "21:30"]
SLOT_JITTER_MIN = 25
VIDEOS_PER_DAY = 5
CATEGORY_ID = "27"  # Education

# ---------- جودة الفيديو ----------
MUSIC_VOLUME = 0.10      # موسيقى خلفية هادية (مولّدة بـ ffmpeg، من غير حقوق)
HOOK_SECONDS = 2.6       # مدة ظهور الجملة الافتتاحية الكبيرة

# ---------- التعلم من النتايج ----------
LEARN_MIN_VIDEOS = 8     # أقل عدد فيديوهات منشورة عليها بيانات قبل ما نبدأ نتعلم
LEARN_MIN_AGE_HOURS = 48

# ---------- حماية لما تكون مش موجود ----------
CANARY_PER_DAY = 1       # لحد ما أول فيديو يتنشر علنًا فعلًا: فيديو واحد بس في اليوم
MAX_RUN_MINUTES = 40     # أقصى مدة للتشغيل الواحد (بيوفر دقائق GitHub)
