import os
import tempfile
import yt_dlp
from faster_whisper import WhisperModel
from googletrans import Translator
from flask import Flask, request, jsonify

app = Flask(__name__)
translator = Translator()

model_size = "large-v3"
model = WhisperModel(model_size, compute_type="int8", cpu_threads=4)

def download_audio(url):
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "audio.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": audio_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return audio_path

def transcribe_and_translate(audio_path):
    segments, _ = model.transcribe(audio_path, language="tr", beam_size=5)
    
    full_text = ""
    for segment in segments:
        full_text += segment.text + " "

    translated = translator.translate(full_text, src='tr', dest='ar')
    return translated.text

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "يرجى إرسال رابط الفيديو"}), 400

        try:
            url = data["url"]
            audio_path = download_audio(url)
            translation = transcribe_and_translate(audio_path)
            os.remove(audio_path)
            return jsonify({"translation": translation})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return '''
        <form method="post" action="/" enctype="application/json">
            <input type="text" name="url" placeholder="ضع رابط الفيديو هنا">
            <input type="submit" value="ترجم">
        </form>
    '''

if __name__ == "__main__":
    app.run(debug=True)
