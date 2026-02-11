# Politidøgnet 🚨🎬 

[![Status](https://img.shields.io/badge/status-under--construction-orange)](https://github.com/viictator/Politid-gnet)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

> **⚠️ WORK IN PROGRESS:** This project is currently under active development. Features are being added, and the codebase is subject to frequent changes. Not all components are production-ready yet.

**Politidøgnet** (Danish for "The Police Journal") is an automated content creation pipeline designed to transform dry, text-based police reports into engaging "Short-form" video content for TikTok, Reels, and YouTube Shorts. 

The system leverages AI to curate the most "viral-worthy" stories, generate dramatic scripts, synthesize professional voiceovers, and assemble fully subtitled videos with contextually relevant footage.

## 🚀 Key Features

- **Automated Scraping:** Periodically fetches the latest daily reports from official Danish police sources (`politi.dk`).
- **AI Intelligence (Gemini 2.0):** Analyzes report data to score and select stories based on engagement potential.
- **Dynamic Scripting:** Generates high-retention scripts featuring hooks, storytelling, and Calls to Action (CTA).
- **Pro Voiceovers:** Integration with **ElevenLabs** for high-quality, natural-sounding Danish narration.
- **Stock Footage Automation:** Calculates audio duration and fetches matching vertical video clips via the **Pexels API**.
- **Synchronized Subtitles:** Uses **OpenAI Whisper** with script-alignment prompts to generate frame-perfect, word-by-word captions.
- **Automated Editing:** Powered by **MoviePy (v2.0)** to handle complex video composition, text rendering, and audio mixing.

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **AI/LLM:** Google Gemini (via `google-genai` SDK)
- **Audio:** ElevenLabs API & OpenAI Whisper
- **Video Processing:** MoviePy (v2.0.0+)
- **Environment:** Decoupled config via `python-dotenv`

## 📂 Project Structure

- `main.py`: The central orchestrator managing the workflow logic.
- `scraper/`:
    - `reportscraper.py`: Logic for crawling and parsing police reports.
    - `aiFunctions.py`: AI-driven logic for scripting, Pexels integration, and video composition.
- `utility/`: General helper functions (date formatting, file I/O).
- `output/`: Storage for generated voiceovers, video clips, and final rendered videos.

## ⚙️ Configuration

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/viictator/Politid-gnet.git](https://github.com/viictator/Politid-gnet.git)
   cd Politid-gnet

2. **Install requirements*
   pip install -r requirements.txt

3. **Set up Environment Variables: Create a .env file in the root directory:**
  API_KEY=your_gemini_api_key
  ELEVENLABS_API_KEY=your_elevenlabs_key
  PEXELS_API_KEY=your_pexels_key
  IMAGEMAGICK_BINARY=C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe

   
