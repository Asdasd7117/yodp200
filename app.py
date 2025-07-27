from flask import Flask, request, render_template_string
import os
import uuid
import whisper
from yt_dlp import YoutubeDL
from deep_translator import GoogleTranslator
import logging

app = Flask(__name__)

# تحميل نموذج Whisper
model = whisper.load_model("base")  # استخدم "small" أو "medium" إذا كانت الموارد متوفرة

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

# HTML للواجهة
HTML = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8" />
    <title>تحويل صوت فيديو يوتيوب إلى نص وترجمة</title>
    <style>
        body { direction: rtl; font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 2em;}
        textarea {width: 100%; height: 150px;}
        input[type=text] {width: 100%; padding: 8px; margin-bottom: 10px;}
        input[type=submit] {padding: 10px 20px; font-size: 16px; cursor: pointer;}
        .result {background: #f0f0f0; padding: 1em; margin-top: 1em; border-radius: 6px;}
    </style>
</head>
<body>
    <h1>تحويل صوت فيديو يوتيوب إلى نص وترجمة</h1>
    <form method="post">
        <label>رابط الفيديو:</label><br>
        <input type="text" name="url" required placeholder="https://www.youtube.com/watch?v=..." />
        <input type="submit" value="تحويل" />
    </form>
    {% if original_text %}
    <div class="result">
        <h3>النص المستخرج:</h3>
        <textarea readonly>{{ original_text }}</textarea>
        <h3>الترجمة إلى العربية:</h3>
        <textarea readonly>{{ translated_text }}</textarea>
    </div>
    {% endif %}
</body>
</html>
"""

# تحميل الصوت من يوتيوب
def download_audio(url):
    try:
        filename = f"audio_{uuid.uuid4()}.mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filename,
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return filename
    except Exception as e:
        logging.error(f"[تنزيل] خطأ: {e}")
        return None

# تحويل الصوت إلى نص باستخدام Whisper
def transcribe_audio(filename):
    try:
        result = model.transcribe(filename)
        return result['text']
    except Exception as e:
        logging.error(f"[تحويل نصي] خطأ: {e}")
        return "حدث خطأ أثناء تحويل الصوت إلى نص"

# ترجمة النص
def translate_text(text, target='ar'):
    try:
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as e:
        logging.error(f"[ترجمة] خطأ: {e}")
        return "حدث خطأ أثناء الترجمة"

# المسار الرئيسي
@app.route("/", methods=["GET", "POST"])
def index():
    original_text = ""
    translated_text = ""

    if request.method == "POST":
        url = request.form.get("url")
        if not url.startswith("http"):
            return render_template_string(HTML, original_text="رابط غير صالح", translated_text="")

        filename = download_audio(url)

        if filename:
            try:
                original_text = transcribe_audio(filename)
                translated_text = translate_text(original_text)
            finally:
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            original_text = "فشل تحميل الفيديو"
            translated_text = ""

    return render_template_string(HTML, original_text=original_text, translated_text=translated_text)

# التشغيل
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
