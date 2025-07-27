from flask import Flask, request, render_template_string
import yt_dlp
from pydub import AudioSegment
import speech_recognition as sr
from deep_translator import GoogleTranslator
import os

app = Flask(__name__)

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloaded_audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return 'downloaded_audio.mp3'

def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(audio_file)
    audio.export("converted.wav", format="wav")

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "لم يتم التعرف على الكلام"
        except sr.RequestError:
            return "حدث خطأ في الاتصال بـ Google"

def translate_text(text, lang='ar'):
    try:
        translated = GoogleTranslator(source='auto', target=lang).translate(text)
        return translated
    except Exception as e:
        return f"خطأ أثناء الترجمة: {str(e)}"

HTML = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8" />
    <title>تحويل فيديو يوتيوب إلى نص وترجمة</title>
    <style>
        body { direction: rtl; font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 2em;}
        textarea {width: 100%; height: 150px;}
        input[type=text] {width: 100%; padding: 8px; margin-bottom: 10px;}
        input[type=submit] {padding: 10px 20px; font-size: 16px; cursor: pointer;}
        .result {background: #f0f0f0; padding: 1em; margin-top: 1em; border-radius: 6px;}
    </style>
</head>
<body>
    <h1>تحويل فيديو يوتيوب إلى نص وترجمة</h1>
    <form method="post">
        <label>أدخل رابط فيديو يوتيوب:</label><br>
        <input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." required />
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

@app.route('/', methods=['GET', 'POST'])
def index():
    original_text = None
    translated_text = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            try:
                audio_file = download_audio(url)
                original_text = transcribe_audio(audio_file)
                translated_text = translate_text(original_text)
            finally:
                if os.path.exists("downloaded_audio.mp3"):
                    os.remove("downloaded_audio.mp3")
                if os.path.exists("converted.wav"):
                    os.remove("converted.wav")
    return render_template_string(HTML, original_text=original_text, translated_text=translated_text)

if __name__ == '__main__':
    app.run(debug=True)
