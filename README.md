Privacy Policy: https://gist.github.com/aliramzi136-del/8f3b28b22cf9491e8415dc59c1b6c5a4
# Arabic Shorts Bot — نظام شورتس عربي أوتوماتيك

الفكرة: كل يوم يدخل على قنوات إنجليزي في النيش، يطلع الفيديوهات الـ Outlier (مشاهدات عالية نسبةً لحجم القناة)،
ياخد **الفكرة بس** ويكتب سكريبت عربي أصلي، يعمل صوت + فوتيج + ترجمة، ويرفع 5 شورتس مجدولين على بكرة.

## الـ Setup (مرة واحدة)

1. **Google Cloud**: اعمل مشروع، فعّل *YouTube Data API v3*.
   - اعمل **API key** → `YOUTUBE_API_KEY` (للقراءة)
   - اعمل **OAuth client** نوع Desktop ونزّل `client_secret.json`
   - في OAuth consent screen خلّي الحالة **In production** (في Testing الـ refresh token بيموت بعد 7 أيام)
2. شغّل محليًا مرة: `python auth_setup.py` → هيطلعلك `YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN`
3. **Gemini key** من aistudio.google.com → `GEMINI_API_KEY`
4. **Pixabay key** من pixabay.com/api/docs (بعد تسجيل الدخول) → `PIXABAY_API_KEY` (Pexels موقف المفاتيح الجديدة)
5. ارفع المشروع على GitHub repo، وحط الـ 6 قيم (YOUTUBE_API_KEY, GEMINI_API_KEY, PIXABAY_API_KEY, YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN) في *Settings → Secrets → Actions*
6. قدّم طلب **YouTube API Audit** (من صفحة Quota في Google Cloud / نموذج YouTube API Services Audit).
   لحد ما يتوافق عليه، فيديوهاتك هتفضل Private حتى لو مجدولة.

## تجربة محلية (من غير رفع)
```
pip install -r requirements.txt   # ومعاك ffmpeg + خط Noto Sans Arabic
export YOUTUBE_API_KEY=... GEMINI_API_KEY=... PIXABAY_API_KEY=...
python main.py --count 1 --no-upload
```
هيطلعلك `output/1.mp4`. اتفرج عليه وظبّط `config.py` قبل ما تفعّل الرفع.

## التشغيل التلقائي
الـ workflow في `.github/workflows/daily.yml` بيشتغل كل يوم 01:00 UTC، وبيحفظ `state.json` عشان ما يكررش أفكار.

## الـ Quota
5 رفع × 1600 = 8000 + ~20 وحدة قراءة، من أصل 10,000 يوميًا.

## لازم تعرفه
- `youtube-transcript-api` غالبًا بيتحجب من IPs السحابة، فالسيستم بيكمل بالعنوان والوصف لو فشل.
- Gemini ممكن يغلط في معلومة. راجع أول 20-30 فيديو بنفسك وعدّل الـ prompt في `scriptgen.py`.
- راجع الـ `SOURCE_CHANNELS` في `config.py` وتأكد إن الـ handles صح.
