from flask import Flask, request, render_template
from main import download_audio, extract_audio, transcribe_and_translate
import os

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    translation = ""
    if request.method == "POST":
        url = request.form["url"]
        try:
            mp4_file = download_audio(url)
            wav_file = extract_audio(mp4_file)
            translation = transcribe_and_translate(wav_file)
            os.remove(mp4_file)
            os.remove(wav_file)
        except Exception as e:
            translation = f"حدث خطأ: {str(e)}"
    return render_template("index.html", translation=translation)

if __name__ == "__main__":
    app.run(debug=True)