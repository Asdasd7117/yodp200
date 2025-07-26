import os
import yt_dlp
from pydub import AudioSegment
import speech_recognition as sr
from googletrans import Translator

# 1. تحميل الفيديو وتحويله لصوت
def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloaded_audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return 'downloaded_audio.mp3'

# 2. تحويل الصوت إلى نص
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

# 3. الترجمة إلى العربية
def translate_text(text):
    translator = Translator()
    result = translator.translate(text, dest='ar')
    return result.text

# مثال للاستخدام:
if __name__ == "__main__":
    url = input("أدخل رابط الفيديو من يوتيوب: ")
    audio_file = download_audio(url)
    print("تم التحميل، جاري التحويل إلى نص...")
    transcribed = transcribe_audio(audio_file)
    print("\nالنص المستخرج:\n", transcribed)
    print("\nالترجمة إلى العربية:\n", translate_text(transcribed))
