from pytube import YouTube
import speech_recognition as sr
from pydub import AudioSegment
from googletrans import Translator
import os
import uuid
import subprocess

def download_audio(youtube_url):
    yt = YouTube(youtube_url)
    stream = yt.streams.filter(only_audio=True).first()
    filename = f"{uuid.uuid4()}.mp4"
    stream.download(filename=filename)
    return filename

def extract_audio(mp4_file):
    wav_file = mp4_file.replace(".mp4", ".wav")
    command = ["ffmpeg", "-i", mp4_file, wav_file]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_file

def split_audio(wav_file, chunk_length_ms=30000):  # 30 ثانية
    audio = AudioSegment.from_wav(wav_file)
    chunks = [audio[i:i+chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
    return chunks

def transcribe_and_translate(wav_file):
    recognizer = sr.Recognizer()
    chunks = split_audio(wav_file)
    full_text = ""
    translator = Translator()

    for i, chunk in enumerate(chunks):
        chunk_file = f"chunk_{i}.wav"
        chunk.export(chunk_file, format="wav")
        with sr.AudioFile(chunk_file) as source:
            audio_data = recognizer.record(source)
            try:
                text_tr = recognizer.recognize_google(audio_data, language="tr-TR")
                translated = translator.translate(text_tr, src='tr', dest='ar').text
                full_text += f"\n---\n{translated}\n"
            except Exception as e:
                full_text += f"\n[خطأ في المقطع {i}]: {str(e)}\n"
        os.remove(chunk_file)

    return full_text