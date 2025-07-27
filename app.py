from flask import Flask, request, render_template_string
import os
import uuid
from yt_dlp import YoutubeDL
from deep_translator import GoogleTranslator
import openai
import logging

app = Flask(__name__)

# إعداد مفتاح OpenAI من المتغيرات البيئية
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("يرجى تعيين متغير بيئة OPENAI_API_KEY")

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# HTML مع إضافة خيار لتحديد اللغة
HTML = """
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8" />
<title>ترجمة صوت يوتيوب</title>
<style>
body { direction: rtl; font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 2em; }
textarea { width: 100%; height: 150px; }
input[type=text], select { width: 100%; padding: 8px; margin-bottom: 10px; }
input[type=submit] { padding: 10px 20px; font-size: 16px; cursor: pointer; }
.result { background: #f0f0f0; padding: 1em; margin-top: 1em; border-radius: 6px; }
.error { color: red; }
</style>
</head>
<body>
<h1>ترجمة صوت فيديو يوتيوب للعربية (بدون ترجمة يوتيوب)</h1>
<form method="post">
    <label>رابط فيديو يوتيوب:</label><br>
    <input type="text" name="url" required placeholder="https://www.youtube.com/watch?v=..." />
    <label>لغة الترجمة:</label><br>
    <select name="target_lang">
        <option value="ar">العربية</option>
        <option value="en">الإنجليزية</option>
    </select>
    <input type="submit" value="تحويل" />
</form>
{% if original_text %}
<div class="result">
    <h3>النص المستخرج:</h3>
    <textarea readonly>{{ original_text }}</textarea>
    <h3>الترجمة:</h3>
    <textarea readonly>{{ translated_text }}</textarea>
</div>
{% endif %}
{% if error %}
<div class="error">{{ error }}</div>
{% endif %}
</body>
</html>
"""

def download_audio(url):
    try:
        filename = f"audio_{uuid.uuid4()}.mp3"
        cookie_file = os.getenv("COOKIE_FILE", None)  # مسار ملف التعريف من المتغيرات البيئية
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
            'cookiefile': cookie_file if cookie_file and os.path.exists(cookie_file) else None,  # إضافة ملف التعريف إذا وجد
            'retries': 3,  # إعادة المحاولة 3 مرات في حالة الفشل
            'fragment_retries': 3,
            'http_headers': {'User-Agent': 'Mozilla/5.0'},  # تحسين التوافق
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return filename
    except Exception as e:
        logging.error(f"[تحميل الصوت] خطأ: {e}")
        return None

def transcribe_audio(filename):
    try:
        with open(filename, "rb") as audio_file:
            result = openai.Audio.transcribe("whisper-1", audio_file)
            return result.get("text", "")
    except Exception as e:
        logging.error(f"[تحويل نصي] خطأ: {e}")
        return None

def translate_text(text, target='ar'):
    try:
        if not text:
            return ""
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as e:
        logging.error(f"[ترجمة] خطأ: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    original_text = ""
    translated_text = ""
    error = ""

    if request.method == "POST":
        url = request.form.get("url")
        target_lang = request.form.get("target_lang", "ar")

        if not url.startswith("http"):
            error = "رابط غير صالح"
        else:
            filename = download_audio(url)
            if filename:
                try:
                    original_text = transcribe_audio(filename)
                    if original_text:
                        translated_text = translate_text(original_text, target_lang)
                    else:
                        error = "فشل تحويل الصوت إلى نص"
                finally:
                    if os.path.exists(filename):
                        os.remove(filename)
            else:
                error = "فشل تحميل الفيديو (تأكد من ملف التعريف إذا كان الفيديو محميًا)"

    return render_template_string(HTML, original_text=original_text, translated_text=translated_text, error=error)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)  # تعطيل الوضع التجريبي في الإنتاج
