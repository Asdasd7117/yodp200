const express = require('express');
const ytdl = require('ytdl-core');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;
const { OpenAI } = require('openai');
const WebSocket = require('ws');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = process.env.PORT || 3000;
const wsPort = 3001;

// إعداد ffmpeg
ffmpeg.setFfmpegPath(ffmpegPath);

// إعداد OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// إعداد WebSocket
const wss = new WebSocket.Server({ port: wsPort });
wss.on('connection', (ws) => {
  console.log('📡 WebSocket متصل');
});

// بث البيانات لجميع العملاء
function broadcast(data) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(data));
    }
  });
}

// إعداد Express
app.use(express.static('public'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// الصفحة الرئيسية
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// نقطة الترجمة
app.post('/translate', async (req, res) => {
  const { url, target_lang } = req.body;

  if (!url || !url.startsWith('http')) {
    return res.status(400).json({ error: 'رابط غير صالح', loading: false });
  }

  const videoId = getVideoId(url);
  if (!videoId) {
    return res.status(400).json({ error: 'رابط يوتيوب غير صالح', loading: false });
  }

  res.json({ loading: true });
  broadcast({ videoId, loading: true });

  try {
    const audioPath = await downloadYouTubeAudio(url);
    const transcription = await transcribeAudio(audioPath);
    const translation = transcription ? await translateText(transcription, target_lang) : '';

    fs.unlinkSync(audioPath); // حذف الملف المؤقت

    broadcast({
      originalText: transcription,
      translatedText: translation,
      loading: false,
    });

  } catch (error) {
    console.error('❌ خطأ أثناء المعالجة:', error.message);
    broadcast({ error: 'فشل المعالجة', loading: false });
  }
});

// استخراج معرف الفيديو
function getVideoId(url) {
  const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  return match ? match[1] : null;
}

// تحميل الصوت فقط من YouTube
function downloadYouTubeAudio(url) {
  return new Promise((resolve, reject) => {
    const tempFile = path.join(__dirname, `audio_${uuidv4()}.mp3`);
    const stream = ytdl(url, { filter: 'audioonly' });

    ffmpeg(stream)
      .audioBitrate(128)
      .save(tempFile)
      .on('end', () => resolve(tempFile))
      .on('error', (err) => {
        console.error('❌ خطأ تحميل ffmpeg:', err.message);
        reject(err);
      });
  });
}

// تحويل الصوت إلى نص
async function transcribeAudio(audioPath) {
  try {
    const response = await openai.audio.transcriptions.create({
      file: fs.createReadStream(audioPath),
      model: 'whisper-1',
    });
    return response.text;
  } catch (err) {
    console.error('❌ خطأ تحويل الصوت:', err.message);
    return null;
  }
}

// الترجمة عبر Google Translate
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
    console.error('❌ خطأ الترجمة:', err.message);
    return text;
  }
}

// بدء السيرفر
app.listen(port, () => {
  console.log(`✅ السيرفر يعمل على http://localhost:${port}`);
  console.log(`📡 WebSocket يعمل على ws://localhost:${wsPort}`);
});
