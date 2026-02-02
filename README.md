# 🚔 Politi Døgnrapport - TikTok Video Generator

Automatically generates TikTok-style news videos from Danish police daily reports (døgnrapporter).

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- **📡 Auto-scraping** - Scrapes police reports from [politi.dk](https://politi.dk)
- **🤖 AI Ranking** - Uses Gemini AI to score and select the most newsworthy reports
- **📝 Sub-article Segmentation** - Breaks stories into 3-6 segments for better engagement
- **🎬 AI Video Generation** - Creates low-poly 3D style videos for each segment
- **🔊 Voice-over** - Professional Danish TTS via ElevenLabs
- **📺 TikTok Format** - Vertical 9:16 format with animated subtitles
- **♻️ Caching** - Reuse mode to save API costs during development

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/Politid-gnet.git
cd Politid-gnet

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the generator
python subarticle_main.py
```

## 📋 Requirements

- Python 3.12+
- Chrome browser (for scraping)
- API keys for:
  - Google Gemini (AI analysis)
  - Replicate (video generation)
  - ElevenLabs (text-to-speech)

## ⚙️ Environment Variables

Create a `.env` file with the following:

```env
API_KEY=your_gemini_api_key
REPL_KEY=your_replicate_api_key
ELEVEN_LABS_KEY=your_elevenlabs_api_key
```

## 📖 Usage

### Basic Usage

```bash
# Full run - scrapes, analyzes, and generates video
python subarticle_main.py

# Reuse existing data (saves money during testing)
python subarticle_main.py --reuse

# Use a different video model
python subarticle_main.py --model minimax

# Combine flags
python subarticle_main.py --reuse --model luma
```

### Command Line Options

| Flag | Description |
|------|-------------|
| `--reuse` | Reuse cached report data, audio, and videos |
| `--model MODEL` | Choose video generation model (default: pixverse) |
| `--help` | Show help message |

---

## 💰 Pricing Guide

### Video Generation Models (via Replicate)

| Model | Cost per Video | Quality | Speed | Best For |
|-------|---------------|---------|-------|----------|
| **pixverse** | ~$0.30 (5s 720p) | ⭐⭐⭐ | Fast | Default, balanced |
| **minimax** | ~$0.20-0.50 | ⭐⭐⭐⭐ | Medium | High quality |
| **luma** | ~$0.25-0.40 | ⭐⭐⭐⭐ | Medium | Cinematic style |
| **ltx-video** | ~$0.04-0.06/sec | ⭐⭐⭐ | Fast | Budget option |
| **hunyuan** | ~$0.10 (4s) | ⭐⭐⭐⭐ | Slow | Open source quality |

> 💡 **Tip**: A typical video with 6 sub-articles costs ~$1.50-3.00 in video generation.

### Text-to-Speech (ElevenLabs)

| Plan | Monthly Cost | Characters | Cost per 1k chars |
|------|-------------|------------|-------------------|
| Free | $0 | 10,000 | N/A (non-commercial) |
| Starter | $5 | 30,000 | ~$0.17 |
| Creator | $22 | 100,000 | ~$0.22 |
| Pro | $99 | 500,000 | ~$0.20 |

> 💡 **Estimate**: Each sub-article is ~20-30 words (~150 chars). A 6-segment video uses ~900 characters.

### AI Analysis (Google Gemini)

| Model | Input Cost | Output Cost |
|-------|-----------|-------------|
| gemini-2.5-flash-lite | $0.07 / 1M tokens | $0.30 / 1M tokens |

> 💡 **Estimate**: Analyzing reports + generating sub-articles costs < $0.01 per run.

### Total Cost Estimate (per video)

| Component | Estimated Cost |
|-----------|---------------|
| Gemini AI (analysis) | < $0.01 |
| ElevenLabs (6 segments) | ~$0.05-0.20 |
| Video Generation (6 clips) | ~$1.50-3.00 |
| **Total** | **~$1.60-3.20** |

---

## 📁 Project Structure

```
Politid-gnet/
├── main.py                    # Original single-image video flow
├── subarticle_main.py         # Sub-article video flow (recommended)
├── scraper/
│   ├── scraper.py            # Politi.dk web scraper
│   └── aiFunctions.py        # Gemini AI analysis
├── video/
│   ├── video_generator.py    # Original video generator
│   └── subarticle_video_generator.py  # Sub-article video generator
├── output/
│   ├── audio/                # Generated audio files
│   ├── videos/               # Raw AI-generated clips
│   ├── clips/                # Processed video clips
│   ├── final/                # Final TikTok videos
│   ├── report_cache.json     # Cached report data
│   └── subarticles_cache.json # Cached sub-articles
├── requirements.txt
├── .env                      # API keys (not in git)
└── README.md
```

## 🎥 Output

The generator creates:
- **Final video**: `output/final/tiktok_subarticle_X_[title].mp4`
- Format: 1080x1920 (9:16 vertical)
- Duration: ~50-90 seconds depending on content
- Features: Low-poly 3D style, animated subtitles, professional voice-over

## 🔧 How It Works

1. **Scraping**: Fetches today's police reports from politi.dk
2. **AI Analysis**: Gemini ranks reports by news value (1-10)
3. **Segmentation**: Best report is split into 3-6 sub-articles
4. **Audio Generation**: Each segment gets TTS voice-over
5. **Video Generation**: AI creates 5-second low-poly videos per segment
6. **Video Processing**: Videos are slowed down and looped to match audio
7. **Assembly**: All clips are combined with subtitles into final TikTok video

## 🛠️ Development

### Saving Money During Development

Use the `--reuse` flag to avoid regenerating expensive assets:

```bash
# First run - generates everything
python subarticle_main.py

# Subsequent runs - reuses cached data
python subarticle_main.py --reuse
```

This reuses:
- Scraped report data
- Sub-article extraction
- Generated audio files
- Generated video clips

### Clearing Cache

To regenerate specific components:

```bash
# Regenerate videos only
rm output/videos/*.mp4 output/clips/*.mp4
python subarticle_main.py --reuse

# Regenerate audio only
rm output/audio/*.mp3
python subarticle_main.py --reuse

# Full regeneration
rm -rf output/
python subarticle_main.py
```

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

Made with ❤️ for automated Danish news content
