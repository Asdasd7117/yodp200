const express = require('express');
const ytdl = require('ytdl-core');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegStatic = require('@ffmpeg-installer/ffmpeg').path;
const { OpenAI } = require('openai');
const WebSocket = require('ws');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = process.env.PORT || 3000;

ffmpeg.setFfmpegPath(ffmpegStatic);

// إعداد OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// WebSocket
const wss = new WebSocket.Server({ port: 8080 });

app.use(express.static('public'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// الواجهة الرئيسية
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// نقطة الترجمة
app.post('/translate', async (req, res) => {
  const { url, target_lang } = req.body;
  if (!url || !url.startsWith('http')) {
    return res.json({ error: 'رابط غير صالح', loading: false });
  }

  const videoId = getVideoId(url);
  if (!videoId) {
    return res.json({ error: 'رابط يوتيوب غير صالح', loading: false });
  }

  res.json({ loading: true });

  broadcast({ videoId, loading: true });

  try {
    const audioStream = ytdl(url, { filter: 'audioonly' });
    const chunks = [];

    audioStream.on('data', chunk => chunks.push(chunk));
    audioStream.on('end', async () => {
      const audioBuffer = Buffer.concat(chunks);
      const audioPath = path.join(__dirname, `audio_${uuidv4()}.mp3`);
      fs.writeFileSync(audioPath, audioBuffer);

      const transcription = await transcribeAudio(audioPath);
      const translation = transcription ? await translateText(transcription, target_lang) : '';

      fs.unlinkSync(audioPath);

      broadcast({
        originalText: transcription,
        translatedText: translation,
        loading: false,
      });
    });

    audioStream.on('error', err => {
      console.error(`خطأ في تحميل الصوت: ${err.message}`);
      broadcast({ error: 'فشل تحميل صوت الفيديو', loading: false });
    });

  } catch (err) {
    console.error(`خطأ أثناء المعالجة: ${err.message}`);
    broadcast({ error: 'خطأ داخلي أثناء المعالجة', loading: false });
  }
});

// 🔍 استخراج معرف الفيديو من الرابط
function getVideoId(url) {
  const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  return match ? match[1] : null;
}

// 🗣️ تحويل الصوت إلى نص باستخدام OpenAI
async function transcribeAudio(audioPath) {
  try {
    const response = await openai.audio.transcriptions.create({
      file: fs.createReadStream(audioPath),
      model: 'whisper-1',
    });
    return response.text;
  } catch (err) {
    console.error(`خطأ في تحويل الصوت: ${err.message}`);
    return null;
  }
}

// 🌐 الترجمة باستخدام Google Translate API
async function translateText(text, target = 'ar') {
  try {
    const response = await axios.post(
      'https://translation.googleapis.com/language/translate/v2',
      {},
      {
        params: {
          q: text,
          target,
          key: process.env.GOOGLE_API_KEY,
        },
      }
    );
    return response.data.data.translations[0].translatedText;
  } catch (err) {
    console.error(`خطأ في الترجمة: ${err.message}`);
    return text;
  }
}

// 📡 إرسال بيانات لجميع المتصلين عبر WebSocket
function broadcast(data) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(data));
    }
  });
}

// 🚀 تشغيل الخادم
app.listen(port, () => {
  console.log(`✅ الخادم يعمل على http://localhost:${port}`);
});

wss.on('connection', ws => {
  console.log('🔌 تم الاتصال بـ WebSocket');
});
