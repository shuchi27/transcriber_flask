# 📝 Transcript Generator

Extracts clean transcripts from city meeting videos (YouTube, Granicus, VieBit) using subtitle files or Whisper AI fallback.

---

## 🚀 Features

- Auto-downloads subtitles with `yt-dlp`
- Falls back to Whisper AI if no subtitles
- Supports `.vtt` extraction from HTML pages
- Flask API + Standalone script options

---

## 🔧 Requirements

- Python 3.8+
- yt-dlp
- ffmpeg
- Python packages:
  - `requests`
  - `openai-whisper`
  - `flask` (for API)

Install dependencies:
```bash
pip install -r requirements.txt