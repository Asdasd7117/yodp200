const express = require('express');
const ytdl = require('ytdl-core');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegStatic = require('@ffmpeg-installer/ffmpeg').path;
const { OpenAI } = require('openai');
const WebSocket = require('ws');
const path = require('path');
const fs = require('fs');

const app = express();
const port = process.env.PORT || 3000;

// إعداد OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

ffmpeg.setFfmpegPath(ffmpegStatic);

// إعداد WebSocket
const wss = new WebSocket.Server({ port: 8080 });

ffmpeg.setFmpegPath(ffmpegStatic);

app.use(express.static('public'));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/', (req, res) => {
  res.send(`
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
      <form id="videoForm">
        <label>رابط فيديو يوتيوب:</label><br>
        <input type="text" name="url" required placeholder="https://www.youtube.com/watch?v=..." />
        <label>لغة الترجمة:</label><br>
        <select name="target_lang">
          <option value="ar">العربية</option>
          <option value="en">الإنجليزية</option>
        </select>
        <input type="submit" value="تحميل وترجمة" />
      </form>
      <div id="video-container" class="video-container"></div>
      <div id="result" class="result" style="display:none;">
        <h3>النص المستخرج:</h3>
        <textarea id="original-text" readonly></textarea>
        <h3>الترجمة:</h3>
        <textarea id="translated-text" readonly></textarea>
      </div>
      <div id="error" class="error" style="display:none;"></div>
      <div id="loading" class="loading" style="display:none;">جارٍ معالجة الطلب...</div>
      <script>
        const ws = new WebSocket('ws://localhost:8080');
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.videoId) {
            document.getElementById('video-container').innerHTML = 
              '<h3>الفيديو:</h3><iframe width="560" height="315" src="https://www.youtube.com/embed/' + data.videoId + '" frameborder="0" allowfullscreen></iframe>';
          }
          if (data.originalText) {
            document.getElementById('original-text').value += data.originalText + '\n';
            document.getElementById('result').style.display = 'block';
          }
          if (data.translatedText) {
            document.getElementById('translated-text').value += data.translatedText + '\n';
          }
          if (data.error) {
            document.getElementById('error').innerText = data.error;
            document.getElementById('error').style.display = 'block';
          }
          if (data.loading) {
            document.getElementById('loading').style.display = 'block';
          } else {
            document.getElementById('loading').style.display = 'none';
          }
        };

        document.getElementById('videoForm').addEventListener('submit', (e) => {
          e.preventDefault();
          const formData = new FormData(e.target);
          fetch('/translate', {
            method: 'POST',
            body: new URLSearchParams(formData),
          }).catch(err => ws.send(JSON.stringify({ error: 'فشل الاتصال بالخادم' })));
        });
      </script>
    </body>
    </html>
  `);
});

app.post('/translate', async (req, res) => {
  const { url, target_lang } = req.body;
  res.json({ loading: true });

  if (!url || !url.startsWith('http')) {
    return res.json({ error: 'رابط غير صالح', loading: false });
  }

  const videoId = getVideoId(url);
  if (!videoId) {
    return res.json({ error: 'رابط يوتيوب غير صالح', loading: false });
  }

  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({ videoId, loading: true }));
    }
  });

  try {
    const audioStream = ytdl(url, { filter: 'audioonly' });
    const chunks = [];
    audioStream.on('data', (chunk) => chunks.push(chunk));
    audioStream.on('end', async () => {
      const audioBuffer = Buffer.concat(chunks);
      const audioPath = path.join(__dirname, `audio_${uuid.v4()}.mp3`);
      fs.writeFileSync(audioPath, audioBuffer);

      const transcription = await transcribeAudio(audioPath);
      let translation = '';
      if (transcription) {
        translation = await translateText(transcription, target_lang);
      }

      fs.unlinkSync(audioPath);
      wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify({ originalText: transcription, translatedText: translation, loading: false }));
        }
      });
    });
  } catch (error) {
    console.error(`[خطأ] ${error.message}`);
    wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({ error: 'خطأ داخلي أثناء المعالجة', loading: false }));
      }
    });
  }
});

function getVideoId(url) {
  const videoIdMatch = url.match(/(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|$)/);
  return videoIdMatch ? videoIdMatch[1] : null;
}

async function transcribeAudio(audioPath) {
  try {
    const response = await openai.audio.transcriptions.create({
      file: fs.createReadStream(audioPath),
      model: 'whisper-1',
      language: 'tr',
    });
    return response.text;
  } catch (error) {
    console.error(`[تحويل نصي] خطأ: ${error.message}`);
    return null;
  }
}

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
  } catch (error) {
    console.error(`[ترجمة] خطأ: ${error.message}`);
    return text; // إرجاع النص الأصلي إذا فشلت الترجمة
  }
}

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
  wss.on('connection', ws => {
    console.log('Client connected');
  });
});
