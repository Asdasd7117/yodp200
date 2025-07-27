from flask import Flask, request, render_template_string
import os
import uuid
from yt_dlp import YoutubeDL
from deep_translator import GoogleTranslator
import openai
import logging
import re
import time

app = Flask(__name__)

# إعداد مفتاح OpenAI من المتغيرات البيئية
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("يرجى تعيين متغير بيئة OPENAI_API_KEY")

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# استخراج معرف الفيديو من الرابط
def get_video_id(url):
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|$)',
                              url)
    return video_id_match.group(1) if video_id_match else None

# HTML مع إضافة فيديو مضمّن
HTML = """
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8" />
<title>ترجمة صوت يوتيوب</title>
<style>
body { direction: rtl; font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 2em; }
textarea { width: 100%; height: 150px; }
input[type=text], select { width: 100%; padding: 8px; margin-bottom: 10px; }
input[type=submit] { padding: 10px 20px; font-size: 16px; cursor: pointer; }
.result { background: #f0f0f0; padding: 1em; margin-top: 1em; border-radius: 6px; }
.error { color: red; }
.loading { color: blue; font-style: italic; }
.video-container { margin-bottom: 1em; }
</style>
</head>
<body>
<h1>ترجمة صوت فيديو يوتيوب للعربية</h1>
<form method="post">
    <label>رابط فيديو يوتيوب:</label><br>
    <input type="text" name="url" required placeholder="https://www.youtube.com/watch?v=..." />
    <label>لغة الترجمة:</label><br>
    <select name="target_lang">
        <option value="ar">العربية</option>
        <option value="en">الإنجليزية</option>
    </select>
    <input type="submit" value="تحميل وترجمة" />
</form>
{% if video_id %}
<div class="video-container">
    <h3>الفيديو:</h3>
    <iframe width="560" height="315" src="https://www.youtube.com/embed/{{ video_id }}" frameborder="0" allowfullscreen></iframe>
</div>
{% endif %}
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
{% if loading %}
<div class="loading">{{ loading }}</div>
{% endif %}
</body>
</html>
"""

def download_audio(url):
    try:
        filename = f"audio_{uuid.uuid4()}.mp3"
        cookie_file = os.getenv("COOKIE_FILE", None)
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
            'cookiefile': cookie_file if cookie_file and os.path.exists(cookie_file) else None,
            'retries': 3,
            'fragment_retries': 3,
            'http_headers': {'User-Agent': 'Mozilla/5.0'},
            'socket_timeout': 10,
            'download_archive': 'downloaded_videos.txt',
        }
        start_time = time.time()
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logging.info(f"[تحميل الصوت] اكتمل في {time.time() - start_time:.2f} ثانية")
        return filename
    except Exception as e:
        logging.error(f"[تحميل الصوت] خطأ: {e}")
        return None

def transcribe_audio(filename):
    try:
        with open(filename, "rb") as audio_file:
            start_time = time.time()
            result = openai.Audio.transcribe("whisper-1", audio_file, language="tr")  # افتراض اللغة التركية
            logging.info(f"[تحويل نصي] اكتمل في {time.time() - start_time:.2f} ثانية")
            return result.get("text", "")
    except Exception as e:
        logging.error(f"[تحويل نصي] خطأ: {e}")
        return None

def translate_text(text, target='ar'):
    try:
        if not text:
            return ""
        start_time = time.time()
        translated = GoogleTranslator(source='auto', target=target).translate(text)
        logging.info(f"[ترجمة] اكتمل في {time.time() - start_time:.2f} ثانية")
        return translated
    except Exception as e:
        logging.error(f"[ترجمة] خطأ: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    original_text = ""
    translated_text = ""
    error = ""
    loading = ""
    video_id = ""

    if request.method == "POST":
        url = request.form.get("url")
        target_lang = request.form.get("target_lang", "ar")

        if not url.startswith("http"):
            error = "رابط غير صالح"
        else:
            video_id = get_video_id(url)
            if not video_id:
                error = "رابط يوتيوب غير صالح"
            else:
                loading = "جارٍ معالجة الطلب، قد يستغرق ذلك بضع ثوانٍ..."
                filename = download_audio(url)
                if filename:
                    try:
                        original_text = transcribe_audio(filename)
                        if original_text:
                            translated_text = translate_text(original_text, target_lang)
                        else:
                            error = "فشل تحويل الصوت إلى نص (قد يكون الفيديو طويلاً أو مشكلة في الاتصال)"
                    finally:
                        if os.path.exists(filename):
                            os.remove(filename)
                else:
                    error = "فشل تحميل الفيديو (تأكد من ملف التعريف أو جرب رابطًا أقصر)"

                loading = ""  # إزالة رسالة التحميل بعد الانتهاء

    return render_template_string(HTML, original_text=original_text, translated_text=translated_text, error=error, loading=loading, video_id=video_id)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
