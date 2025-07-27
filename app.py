from flask import Flask, request, render_template_string
import os
import uuid
import whisper
from yt_dlp import YoutubeDL
from deep_translator import GoogleTranslator
import logging

app = Flask(__name__)
model = whisper.load_model("base")  # أو "small" أو "medium" أو "large"

logging.basicConfig(level=logging.INFO)

def download_audio(url):
    try:
        filename = f"audio_{uuid.uuid4()}.mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filename,
            'quiet': True,
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
        logging.error(f"Download error: {e}")
        return None

def transcribe_audio(filename):
    try:
        result = model.transcribe(filename)
        return result['text']
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return "حدث خطأ أثناء تحويل الصوت إلى نص"

def translate_text(text, target='ar'):
    try:
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return "حدث خطأ أثناء الترجمة"

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

@app.route("/", methods=["GET", "POST"])
def index():
    original_text = ""
    translated_text = ""

    if request.method == "POST":
        url = request.form.get("url")
        filename = download_audio(url)

        if filename:
            original_text = transcribe_audio(filename)
            translated_text = translate_text(original_text)
            os.remove(filename)
        else:
            original_text = "فشل تحميل الفيديو"
            translated_text = ""

    return render_template_string(HTML, original_text=original_text, translated_text=translated_text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
