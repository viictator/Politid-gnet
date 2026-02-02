"""
TikTok Video Generator for Danish Police News Reports.

Generates vertical TikTok-style videos with:
- Low poly 3D images (Replicate SDXL)
- ElevenLabs TTS narration
- Whisper word-level timing for subtitles
- Ken Burns zoom/pan effects
"""

import replicate
import requests
import os
import json
import math
import re
import shutil
import whisper
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from google import genai
from moviepy import ImageClip, AudioFileClip, TextClip, CompositeVideoClip
from PIL import Image

# Load environment variables
load_dotenv()

# Reusable HTTP session for connection pooling
http_session = requests.Session()

# API Keys
os.environ["REPLICATE_API_TOKEN"] = os.getenv("REPL_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVEN_LABS_KEY", "")
GEMINI_API_KEY = os.getenv("API_KEY", "")

# Gemini client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash-lite"

# Output directories
OUTPUT_DIR = Path("output")
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
VIDEO_DIR = OUTPUT_DIR / "videos"

# TikTok vertical format
TIKTOK_SIZE = (1080, 1920)
IMAGE_INTERVAL = 4  # New image every 4 seconds


def clear_output() -> None:
    """Clears all output directories before a new run."""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print("🗑️ Output mappe ryddet")
    
    # Recreate directories
    for dir_path in [IMAGES_DIR, AUDIO_DIR, VIDEO_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def _ensure_directories() -> None:
    """Ensure output directories exist."""
    for dir_path in [IMAGES_DIR, AUDIO_DIR, VIDEO_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


# Create directories on import
_ensure_directories()


def create_voice_script(report: dict) -> Optional[dict]:
    """
    Creates a voice script for the video based on a news report.
    
    Returns:
        Dict with 'full_script' and 'segments' (with text and image prompts),
        or None on failure.
    """
    prompt = f"""Du er en professionel dansk nyhedsreporter fra TV2 Nyhederne. 
Skriv en kort nyhedsrapport til en TikTok video baseret på denne politirapport.

TITEL: {report['titel']}
MANCHET: {report.get('manchet', '')}
INDHOLD: {report['indhold']}

KRAV TIL MANUSKRIPTET:
1. LÆNGDE: Præcis 80-100 ord (30-40 sekunder når det læses op)
2. STRUKTUR - FØLG ALTID DETTE FORMAT:
   - INTRO (1 sætning): Start med "I dag" eller "I går" + lokation + hvad der skete
   - DETALJER (2-3 sætninger): Hvad skete der præcist?
   - KONSEKVENS (1-2 sætninger): Hvad blev resultatet? Anholdelse? Skader?
   - AFSLUTNING (1 sætning): Politiet efterforsker / søger vidner

3. TONE: Seriøs, faktuel, professionel - som en rigtig nyhedsudsendelse
4. UNDGÅ: Dramatiske udtryk, clickbait, overdrivelser
5. SEGMENTER: Del op i 6-8 segmenter (1-2 sætninger hver)

SVAR KUN MED DETTE JSON FORMAT:
{{
    "full_script": "Det fulde manuskript som én sammenhængende tekst",
    "segments": [
        {{"text": "Intro segment", "image_prompt": "Low poly 3D: [scene description in English]"}},
        {{"text": "Næste segment", "image_prompt": "Low poly 3D: [scene description in English]"}}
    ]
}}

VIGTIGT: Billedprompts skal være på ENGELSK og beskrive low poly 3D scener.
"""
    
    try:
        response = gemini_client.models.generate_content(model=MODEL_NAME, contents=prompt)
        if response.text is None:
            print("❌ Gemini returnerede ingen tekst")
            return None
            
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)
        num_segments = len(result.get("segments", []))
        print(f"✅ Voice script oprettet med {num_segments} segmenter")
        return result
    except Exception as e:
        print(f"❌ Fejl ved oprettelse af voice script: {e}")
        return None


def generate_image(prompt: str, index: int) -> Optional[str]:
    """
    Generates a vertical TikTok image in low poly 3D style using Replicate SDXL.
    
    Returns:
        Local file path of the downloaded image, or None on failure.
    """
    try:
        full_prompt = (
            f"Low poly 3D render, stylized geometric shapes, {prompt}, "
            "isometric view, soft pastel lighting, minimal details, clean aesthetic, "
            "blender style, polygon art, vertical composition, 4k"
        )
        
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": full_prompt,
                "negative_prompt": "realistic, photograph, photo, text, watermark, blurry, high detail, complex textures, noise, grain",
                "width": TIKTOK_SIZE[0],
                "height": TIKTOK_SIZE[1],
                "refine": "expert_ensemble_refiner"  # Faster generation (~40% speedup)
            }
        )
        
        output_list = list(output)
        image_url = output_list[0]
        
        # Download image with connection pooling
        image_path = IMAGES_DIR / f"scene_{index}.png"
        response = http_session.get(image_url)
        with open(image_path, "wb") as f:
            f.write(response.content)
        
        print(f"✅ Billede {index} genereret: {image_path}")
        return str(image_path)
    
    except Exception as e:
        print(f"❌ Fejl ved generering af billede {index}: {e}")
        return None


def generate_speech(text: str, output_filename: str) -> Optional[str]:
    """
    Generates speech using ElevenLabs API with news reporter style.
    
    Returns:
        Local file path of the audio file, or None on failure.
    """
    # Daniel voice - professional, clear, news anchor style
    url = "https://api.elevenlabs.io/v1/text-to-speech/onwK4e9ZLuTAKqWW03F9"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.80,
            "similarity_boost": 0.70,
            "style": 0.15,
            "use_speaker_boost": True
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        audio_path = AUDIO_DIR / output_filename
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        print(f"✅ Audio genereret: {audio_path}")
        return str(audio_path)
    
    except Exception as e:
        print(f"❌ Fejl ved generering af tale: {e}")
        return None


def transcribe_with_whisper(audio_path: str) -> list:
    """
    Transcribes audio using Whisper and returns word-level timestamps.
    
    Returns:
        List of word dicts with 'text', 'start', 'end' keys.
    """
    print("🎤 Transkriberer med Whisper...")
    
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True, language="da")
        
        # Extract word-level timing
        words = []
        segments = result.get("segments", [])
        
        for segment in segments:
            segment_words = segment.get("words", [])  # type: ignore
            for word_data in segment_words:
                words.append({
                    "text": str(word_data.get("word", "")).strip(),
                    "start": float(word_data.get("start", 0)),
                    "end": float(word_data.get("end", 0))
                })
        
        print(f"✅ Whisper fandt {len(words)} ord")
        return words
    
    except Exception as e:
        print(f"❌ Whisper fejl: {e}")
        return []


def align_script_with_timing(script_text: str, whisper_words: list) -> list:
    """
    Aligns the original script text with Whisper timing.
    Uses Whisper for timing but keeps original spelling from script.
    
    Returns:
        List of aligned word dicts with original spelling and Whisper timing.
    """
    # Split script into words
    script_words = re.findall(r"\S+", script_text)
    
    if len(whisper_words) == 0:
        return []
    
    # Create aligned words using script text but Whisper timing
    aligned_words = []
    whisper_idx = 0
    
    for script_word in script_words:
        if whisper_idx < len(whisper_words):
            aligned_words.append({
                "text": script_word,
                "start": whisper_words[whisper_idx]["start"],
                "end": whisper_words[whisper_idx]["end"]
            })
            whisper_idx += 1
        else:
            # If we run out of Whisper words, estimate timing
            if aligned_words:
                last_end = aligned_words[-1]["end"]
                aligned_words.append({
                    "text": script_word,
                    "start": last_end,
                    "end": last_end + 0.3
                })
    
    return aligned_words


def group_words_for_subtitles(words: list, max_words: int = 4) -> list:
    """
    Groups words into subtitle segments.
    Slightly slower pacing for better readability.
    
    Returns:
        List of subtitle dicts with 'text', 'start', 'end' keys.
    """
    subtitles = []
    current_group = []
    
    for word in words:
        current_group.append(word)
        
        # Create subtitle every max_words or at sentence end (not comma)
        if len(current_group) >= max_words or word["text"].endswith((".", "!", "?")):
            if current_group:
                text = " ".join(w["text"] for w in current_group)
                subtitles.append({
                    "text": text,
                    "start": current_group[0]["start"],
                    "end": current_group[-1]["end"]
                })
                current_group = []
    
    # Add remaining words
    if current_group:
        text = " ".join(w["text"] for w in current_group)
        subtitles.append({
            "text": text,
            "start": current_group[0]["start"],
            "end": current_group[-1]["end"]
        })
    
    return subtitles


def create_tiktok_subtitle(text: str, duration: float, start_time: float) -> TextClip:
    """
    Creates a TikTok-style subtitle - bold, centered, punchy.
    
    Returns:
        TextClip positioned in safe zone (500px from bottom).
    """
    display_text = text.upper().strip()
    
    # Limit text length to prevent clipping
    # if len(display_text) > 25:
    #     display_text = display_text[:25]
    
    text_clip = TextClip(
        text=display_text,
        font_size=45,
        color="yellow",
        stroke_color="black",
        stroke_width=4,
        size=(TIKTOK_SIZE[0] - 300, None),
        method="caption",
        text_align="center",
        font="/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    )
    
    # Calculate y position based on actual text height to prevent clipping
    # Place text so bottom edge is 400px from video bottom
    # Add extra padding for stroke width (4px on each side) plus safety margin
    text_height = text_clip.h
    stroke_padding = 4 * 2 + 10  # stroke_width * 2 + safety margin
    y_position = TIKTOK_SIZE[1] - 400 - text_height - stroke_padding
    
    return text_clip.with_duration(duration).with_start(start_time).with_position(("center", y_position))


def create_animated_image_clip(image_path: str, duration: float, start_time: float, index: int) -> ImageClip:
    """
    Creates an animated image clip with zoom/pan effects (Ken Burns effect).
    Alternates between different effects for variety.
    
    Returns:
        ImageClip with animation applied.
    """
    # Load image to get dimensions
    with Image.open(image_path) as img:
        img_width, img_height = img.size
    
    # Calculate scale to fill TikTok frame with extra room for movement
    scale_x = TIKTOK_SIZE[0] / img_width
    scale_y = TIKTOK_SIZE[1] / img_height
    base_scale = max(scale_x, scale_y) * 1.3
    
    # Different effect types
    effect_type = index % 4
    
    if effect_type == 0:
        # Slow zoom in
        start_zoom = base_scale
        end_zoom = base_scale * 1.15
    elif effect_type == 1:
        # Slow zoom out
        start_zoom = base_scale * 1.15
        end_zoom = base_scale
    else:
        # Pan effects with slight zoom
        start_zoom = base_scale * 1.1
        end_zoom = base_scale * 1.1
    
    # Create base clip with average zoom
    avg_zoom = (start_zoom + end_zoom) / 2
    zoomed_width = int(img_width * avg_zoom * 1.1)
    zoomed_height = int(img_height * avg_zoom * 1.1)
    
    clip = ImageClip(image_path).resized((zoomed_width, zoomed_height))
    
    # Create position function for panning
    def position_func(t):
        progress = t / duration if duration > 0 else 0
        progress = progress * progress * (3 - 2 * progress)  # Smoothstep
        
        if effect_type in [0, 1]:
            # Zoom effects - subtle drift
            x_offset = int((progress - 0.5) * 20)
            y_offset = int((progress - 0.5) * 10)
        elif effect_type == 2:
            # Pan left to right
            x_offset = int(-100 + progress * 200)
            y_offset = 0
        else:
            # Pan right to left
            x_offset = int(100 - progress * 200)
            y_offset = 0
        
        x = (TIKTOK_SIZE[0] - zoomed_width) // 2 + x_offset
        y = (TIKTOK_SIZE[1] - zoomed_height) // 2 + y_offset
        return (x, y)
    
    return clip.with_position(position_func).with_duration(duration).with_start(start_time)  # type: ignore


def assemble_tiktok_video(
    image_paths: list,
    segment_timings: list,
    audio_path: str,
    subtitles: list,
    output_name: str
) -> Optional[str]:
    """
    Assembles a TikTok-style vertical video with images synced to speech segments.
    
    Args:
        image_paths: List of image file paths
        segment_timings: List of dicts with 'start' and 'duration' for each image
        audio_path: Path to audio file
        subtitles: List of subtitle dicts with 'text', 'start', 'end'
        output_name: Output filename (without extension)
    
    Returns:
        Path to the final video, or None on failure.
    """
    try:
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        
        # Create image clips synced to segment timings
        image_clips = []
        for i, (image_path, timing) in enumerate(zip(image_paths, segment_timings)):
            if image_path is None:
                continue
            
            start_time = timing["start"]
            duration = timing["duration"]
            
            if duration <= 0:
                continue
            
            img_clip = create_animated_image_clip(image_path, duration, start_time, i)
            image_clips.append(img_clip)
        
        # Combine all image clips
        video_base = CompositeVideoClip(image_clips, size=TIKTOK_SIZE)
        
        # Create subtitle clips
        subtitle_clips = []
        for sub in subtitles:
            duration = sub["end"] - sub["start"]
            if duration > 0:
                clip = create_tiktok_subtitle(sub["text"], duration, sub["start"])
                subtitle_clips.append(clip)
        
        # Combine video with subtitles
        all_clips = [video_base] + subtitle_clips
        final_video = CompositeVideoClip(all_clips, size=TIKTOK_SIZE)
        final_video = final_video.with_duration(total_duration).with_audio(audio)
        
        # Export
        output_path = VIDEO_DIR / f"{output_name}.mp4"
        final_video.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="fast"  # Faster encoding
        )
        
        # Clean up
        audio.close()
        final_video.close()
        for clip in image_clips:
            clip.close()
        
        print(f"✅ TikTok video oprettet: {output_path}")
        return str(output_path)
    
    except Exception as e:
        print(f"❌ Fejl ved sammensætning af video: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_news_video(report: dict, video_index: int = 0) -> Optional[str]:
    """
    Main function to generate a TikTok-style news video from a report.
    
    Steps:
        1. Create voice script with image prompts
        2. Generate TTS audio with ElevenLabs
        3. Transcribe with Whisper for word timing
        4. Generate images synced to speech segments
        5. Assemble TikTok video with fast subtitles
    
    Args:
        report: Dict with 'titel', 'manchet', 'indhold' keys
        video_index: Index for output filename
    
    Returns:
        Path to the final video, or None on failure.
    """
    # Clear old output before starting
    clear_output()
    
    print(f"\n{'='*60}")
    print(f"🎬 GENERERER TIKTOK VIDEO FOR: {report['titel']}")
    print(f"{'='*60}\n")
    
    # Step 1: Create voice script
    print("📝 Opretter voice script...")
    voice_script = create_voice_script(report)
    if not voice_script:
        return None
    
    # Step 2: Generate speech
    print("\n🔊 Genererer tale med ElevenLabs...")
    audio_path = generate_speech(
        voice_script["full_script"],
        f"narration_{video_index}.mp3"
    )
    if not audio_path:
        return None
    
    # Step 3: Transcribe with Whisper for timing
    words = transcribe_with_whisper(audio_path)
    
    if not words:
        print("⚠️ Whisper kunne ikke transkribere, bruger fallback timing")
        audio = AudioFileClip(audio_path)
        subtitles = [{
            "text": voice_script["full_script"],
            "start": 0,
            "end": audio.duration
        }]
        audio.close()
    else:
        # Align original script text with Whisper timing (fixes spelling errors)
        aligned_words = align_script_with_timing(voice_script["full_script"], words)
        if aligned_words:
            subtitles = group_words_for_subtitles(aligned_words, max_words=4)
        else:
            subtitles = group_words_for_subtitles(words, max_words=4)
    
    print(f"✅ {len(subtitles)} undertekst-segmenter oprettet")
    
    # Step 4: Get segments from voice script for image timing
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration
    audio.close()
    
    segments = voice_script.get("segments", [])
    
    if segments:
        # Calculate timing for each segment based on text length
        total_chars = sum(len(seg.get("text", "")) for seg in segments)
        
        # Assign timing to each segment proportionally
        current_time = 0.0
        for seg in segments:
            seg_chars = len(seg.get("text", ""))
            seg_duration = (seg_chars / total_chars) * total_duration if total_chars > 0 else total_duration / len(segments)
            seg["start_time"] = current_time
            seg["duration"] = seg_duration
            current_time += seg_duration
        
        print(f"\n🖼️ Genererer {len(segments)} billeder parallelt...")
        
        # Parallel image generation
        image_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(generate_image, seg.get("image_prompt", "Low poly 3D scene"), i): i
                for i, seg in enumerate(segments)
            }
            for future in as_completed(futures):
                idx = futures[future]
                image_results[idx] = future.result()
        
        # Sort results by index
        image_paths = [image_results[i] for i in range(len(segments))]
        segment_timings = [
            {"start": seg["start_time"], "duration": seg["duration"]}
            for seg in segments
        ]
    else:
        # Fallback to interval-based method if no segments
        num_images = math.ceil(total_duration / IMAGE_INTERVAL)
        print(f"\n🖼️ Genererer {num_images} billeder parallelt...")
        
        image_prompts = voice_script.get("image_prompts", [])
        
        # Build prompt list
        prompts_to_generate = []
        for i in range(num_images):
            prompt_idx = i % len(image_prompts) if image_prompts else 0
            prompt = image_prompts[prompt_idx] if image_prompts else "Low poly 3D news scene"
            prompts_to_generate.append((prompt, i))
        
        # Parallel generation
        image_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(generate_image, prompt, idx): idx
                for prompt, idx in prompts_to_generate
            }
            for future in as_completed(futures):
                idx = futures[future]
                image_results[idx] = future.result()
        
        image_paths = [image_results[i] for i in range(num_images)]
        segment_timings = [
            {
                "start": i * IMAGE_INTERVAL,
                "duration": min(IMAGE_INTERVAL, total_duration - i * IMAGE_INTERVAL)
            }
            for i in range(num_images)
        ]
    
    # Step 5: Assemble TikTok video
    print("\n🎥 Sammensætter TikTok video...")
    safe_title = "".join(
        c for c in report["titel"][:30] 
        if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    output_name = f"tiktok_{video_index}_{safe_title}"
    
    video_path = assemble_tiktok_video(
        image_paths, segment_timings, audio_path, subtitles, output_name
    )
    
    return video_path
