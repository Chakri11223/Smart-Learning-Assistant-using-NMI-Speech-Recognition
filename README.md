# Smart Learning Assistant using GPT & Speech Recognition

## Overview
An AI-powered assistant for digital education with voice Q&A, video summarization, PDF quiz generation, and personalized learning paths.

## Tech Stack
- **Frontend:** React.js
- **Backend:** Flask (Python)
- **AI APIs:** OpenAI GPT, Whisper
- **Text-to-Speech:** gTTS/pyttsx3
- **Audio Extraction:** FFMPEG
- **PDF Extraction:** PDFPlumber

## Setup Instructions

### Backend
1. `cd backend`
2. Create and activate a Python virtual environment.
3. `pip install -r requirements.txt`
4. Set up your API key:
   - Create a `.env` file in the `backend` folder
   - Add: `NVIDIA_API_KEY=your_api_key_here` (recommended)
   - Or add: `OPENAI_API_KEY=your_openai_api_key_here`
5. `python app.py`

### Frontend
1. `cd frontend`
2. `npm install`
3. `npm start`

---

## Features
- Voice-based Q&A
- Lecture video summarization
- PDF-based quiz generator
- Personalized learning path recommendations 

## API Usage

### Text-to-Speech

POST `/api/tts`

JSON body:

```json
{ "text": "Hello world", "lang": "en", "slow": false }
```

Returns: MP3 audio stream (`audio/mpeg`).

Form-data alternative: send fields `text`, `lang`, `slow`.

### Voice Q&A with optional TTS

POST `/api/voice-qa`

- JSON (text question):

```json
{ "question": "What is AI?", "tts": true }
```

Response:

```json
{
  "status": "success",
  "question": "What is AI?",
  "answer": "...",
  "audioBase64": "<base64-mp3>",
  "audioMime": "audio/mpeg"
}
```

- multipart/form-data (audio question upload): fields `audio` (file), optional `tts=true`.

### Video summarization (file upload)

POST `/api/summarize-video` (multipart/form-data)
- Fields: `video` (file), optional `maxWords`.

### URL summarization (YouTube limited)

POST `/api/summarize-url`
- JSON: `{ "url": "https://...", "maxWords": 250 }`
- Note: Direct YouTube download requires additional setup (yt-dlp).

### Quiz generation

POST `/api/generate-quiz`
- JSON: `{ "text": "...", "numQuestions": 5 }`
- Or multipart/form-data with `pdf` file.

### Personalized Learning Paths (simple rules)

- Submit quiz with topics (frontend should include a `topic` per question if available). Topics default to `general` if omitted.

GET `/api/analytics/overall` → overall counters

GET `/api/analytics/user/<session_id>` → per-user stats

GET `/api/recommendations/<session_id>` → strengths, weaknesses, and recommended next steps