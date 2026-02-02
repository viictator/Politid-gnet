"""
Sub-Article TikTok Video Generator for Danish Police News Reports.

Generates vertical TikTok-style videos with:
- Sub-article segmentation using Gemini
- AI-generated 5-second videos (Replicate pixverse/pixverse-v4.5)
- Video slow-down and looping to match voice duration
- ElevenLabs TTS narration per sub-article
- Whisper word-level timing for subtitles
"""

import replicate
import requests
import os
import json
import math
import re
import shutil
import whisper
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from google import genai
from moviepy import (
    VideoFileClip, AudioFileClip, TextClip, 
    CompositeVideoClip, concatenate_videoclips
)

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
VIDEOS_DIR = OUTPUT_DIR / "videos"
CLIPS_DIR = OUTPUT_DIR / "clips"
AUDIO_DIR = OUTPUT_DIR / "audio"
FINAL_DIR = OUTPUT_DIR / "final"

# TikTok vertical format
TIKTOK_SIZE = (1080, 1920)

# Video model configurations
VIDEO_MODELS = {
    "pixverse": {
        "model": "pixverse/pixverse-v4.5",
        "params": {
            "aspect_ratio": "9:16",
            "duration": 5,
            "quality": "720p",
            "style": "3d_animation"
        },
        "negative_prompt": "realistic, photograph, photo, high detail, complex textures, noise, grain, text, watermark, blurry, ugly, deformed"
    },
    "minimax": {
        "model": "minimax/video-01",
        "params": {
            "prompt_optimizer": True
        },
        "negative_prompt": None  # Not supported
    },
    "luma": {
        "model": "luma/ray",
        "params": {
            "aspect_ratio": "9:16",
            "loop": False
        },
        "negative_prompt": None  # Not supported
    },
    "ltx-video": {
        "model": "lightricks/ltx-video",
        "params": {
            "aspect_ratio": "9:16",
            "num_frames": 97  # ~4 seconds at 24fps
        },
        "negative_prompt": "worst quality, inconsistent motion, blurry, jittery, distorted"
    },
    "hunyuan": {
        "model": "tencent/hunyuan-video",
        "params": {
            "width": 544,
            "height": 960,  # 9:16 ratio
            "video_length": 129  # frames
        },
        "negative_prompt": None  # Not supported
    }
}

# Default video model
CURRENT_VIDEO_MODEL = "pixverse"


def clear_output() -> None:
    """Clears all output directories before a new run."""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print("🗑️ Output mappe ryddet")
    
    # Recreate directories
    for dir_path in [VIDEOS_DIR, CLIPS_DIR, AUDIO_DIR, FINAL_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def _ensure_directories() -> None:
    """Ensure output directories exist."""
    for dir_path in [VIDEOS_DIR, CLIPS_DIR, AUDIO_DIR, FINAL_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


# Create directories on import
_ensure_directories()


def extract_subarticles(report: dict) -> Optional[list]:
    """
    Uses Gemini to break an article into 3-6 sub-articles.
    
    Each sub-article contains:
        - text: The narration text for this segment (Danish)
        - video_prompt: A low poly 3D video prompt (English)
    
    Returns:
        List of sub-article dicts, or None on failure.
    """
    prompt = f"""You are a professional news editor creating segments for a TikTok video.
Split this Danish police report into 3-6 separate news segments.

TITLE: {report['titel']}
SUMMARY: {report.get('manchet', '')}
CONTENT: {report['indhold']}

REQUIREMENTS:
1. Each segment should be 15-30 words in DANISH (for voice-over)
2. Each segment should focus on ONE specific part of the story
3. Segments must flow naturally together as a narrative
4. Video prompts must be in ENGLISH describing LOW POLY 3D animated scenes
5. Match the MOOD of each scene to the content (dark for crimes, tense for chases, etc.)

RESPOND ONLY WITH THIS JSON FORMAT:
{{
    "subarticles": [
        {{
            "text": "Danish narration text for voice-over",
            "video_prompt": "Low poly 3D render: [scene description], [mood/atmosphere]"
        }}
    ]
}}

LOW POLY VIDEO PROMPT EXAMPLES (use this style):
- Crime/robbery: "Low poly 3D render: dark city alley at night with geometric buildings, shadowy figure moving, cold blue and purple lighting, noir atmosphere, triangular shapes"
- Car chase: "Low poly 3D render: police car with flashing lights driving through geometric city streets, motion blur, tense atmosphere, angular buildings"
- Search/rescue: "Low poly 3D render: helicopter with searchlight over triangular pine forest at dusk, foggy, suspenseful mood, soft colors"
- Arrest: "Low poly 3D render: police officers near geometric police station, blue flashing lights reflecting off surfaces, serious mood, flat shaded"
- Fire: "Low poly 3D render: geometric building with stylized orange flames and smoke, fire truck nearby, dramatic lighting, warm colors"
- Hospital: "Low poly 3D render: ambulance driving to geometric hospital building, emergency lights, urgent atmosphere, clean shapes"

STYLE KEYWORDS TO ALWAYS INCLUDE: low poly, 3D render, geometric shapes, flat shading, triangular, stylized, soft lighting
"""
    
    try:
        response = gemini_client.models.generate_content(model=MODEL_NAME, contents=prompt)
        if response.text is None:
            print("❌ Gemini returnerede ingen tekst")
            return None
            
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)
        subarticles = result.get("subarticles", [])
        print(f"✅ Ekstraheret {len(subarticles)} sub-artikler")
        return subarticles
    except Exception as e:
        print(f"❌ Fejl ved sub-artikel ekstraktion: {e}")
        return None


def generate_subarticle_speech(text: str, index: int) -> tuple[Optional[str], float]:
    """
    Generates speech for a single sub-article using ElevenLabs API.
    
    Returns:
        Tuple of (audio_path, duration) or (None, 0) on failure.
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
        
        audio_path = AUDIO_DIR / f"subarticle_{index}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        # Get audio duration
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration
        audio_clip.close()
        
        print(f"✅ Audio {index} genereret: {duration:.2f}s")
        return str(audio_path), duration
    
    except Exception as e:
        print(f"❌ Fejl ved generering af tale {index}: {e}")
        return None, 0


def generate_video_clip(prompt: str, index: int, model_name: str = None) -> Optional[str]:
    """
    Generates a 5-second video clip using a Replicate video model.
    
    Args:
        prompt: Motion-focused video prompt
        index: Index for the output filename
        model_name: Which model to use (pixverse, minimax, luma, ltx-video, hunyuan)
    
    Returns:
        Local file path of the downloaded video, or None on failure.
    """
    global CURRENT_VIDEO_MODEL
    model_key = model_name or CURRENT_VIDEO_MODEL
    
    if model_key not in VIDEO_MODELS:
        print(f"❌ Ukendt video model: {model_key}. Bruger pixverse.")
        model_key = "pixverse"
    
    model_config = VIDEO_MODELS[model_key]
    
    try:
        # Enhance prompt with low poly style keywords
        style_suffix = "flat shaded, geometric triangular shapes, clean edges, stylized 3D, pastel colors, soft ambient lighting, Blender low poly style"
        full_prompt = f"{prompt}, {style_suffix}"
        
        print(f"🎬 Genererer video {index} med {model_key}...")
        
        # Build input params
        input_params = {"prompt": full_prompt, **model_config["params"]}
        
        # Add negative prompt if supported
        if model_config["negative_prompt"]:
            input_params["negative_prompt"] = model_config["negative_prompt"]
        
        output = replicate.run(
            model_config["model"],
            input=input_params
        )
        
        # Handle different output formats
        if isinstance(output, str):
            video_url = output
        elif hasattr(output, '__iter__'):
            # Some models return a list or iterator
            output_list = list(output)
            video_url = str(output_list[0]) if output_list else None
        else:
            video_url = str(output)
        
        if not video_url:
            print(f"❌ Ingen video URL returneret for video {index}")
            return None
        
        # Download video
        video_path = VIDEOS_DIR / f"clip_{index}.mp4"
        response = http_session.get(video_url)
        with open(video_path, "wb") as f:
            f.write(response.content)
        
        print(f"✅ Video {index} genereret: {video_path}")
        return str(video_path)
    
    except Exception as e:
        print(f"❌ Fejl ved generering af video {index}: {e}")
        import traceback
        traceback.print_exc()
        return None


def set_video_model(model_name: str) -> bool:
    """
    Set the current video model to use.
    
    Args:
        model_name: One of: pixverse, minimax, luma, ltx-video, hunyuan
    
    Returns:
        True if model was set successfully, False otherwise.
    """
    global CURRENT_VIDEO_MODEL
    if model_name in VIDEO_MODELS:
        CURRENT_VIDEO_MODEL = model_name
        print(f"🎬 Video model sat til: {model_name}")
        return True
    else:
        print(f"❌ Ukendt model: {model_name}. Tilgængelige: {', '.join(VIDEO_MODELS.keys())}")
        return False


def slow_and_loop_video(video_path: str, target_duration: float, index: int) -> Optional[str]:
    """
    Slows down a 5-second video and loops it to match the target duration.
    
    Strategy:
    1. Slow the video to 0.5x-0.7x speed
    2. If still shorter than target, loop seamlessly
    3. Trim to exact target duration
    
    Args:
        video_path: Path to the original 5-second video
        target_duration: Target duration in seconds (from voice-over)
        index: Index for output filename
    
    Returns:
        Path to the processed video, or None on failure.
    """
    try:
        clip = VideoFileClip(video_path)
        original_duration = clip.duration
        
        # Calculate slow factor (aim for 0.5x to 0.7x speed)
        # If target is 10s and video is 5s, we need 2x the content
        # Slow to 0.5x makes 5s -> 10s, which is perfect
        slow_factor = max(0.4, min(0.8, original_duration / target_duration))
        
        # Apply slow motion
        slowed = clip.with_speed_scaled(slow_factor)
        slowed_duration = slowed.duration
        
        print(f"   Video {index}: {original_duration:.1f}s → {slowed_duration:.1f}s (target: {target_duration:.1f}s)")
        
        # Loop if needed
        did_loop = False
        if slowed_duration < target_duration:
            loops_needed = math.ceil(target_duration / slowed_duration)
            looped = concatenate_videoclips([slowed] * loops_needed)
            did_loop = True
        else:
            looped = slowed
        
        # Trim to exact duration
        final = looped.subclipped(0, target_duration)
        
        # Export processed clip
        output_path = CLIPS_DIR / f"processed_{index}.mp4"
        final.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio=False,  # No audio yet - we'll add it later
            preset="fast",
            logger=None  # Suppress progress output
        )
        
        # Cleanup - close in reverse order, avoid comparing clips
        final.close()
        if did_loop:
            looped.close()
        slowed.close()
        clip.close()
        
        print(f"✅ Video {index} bearbejdet: {target_duration:.1f}s")
        return str(output_path)
    
    except Exception as e:
        print(f"❌ Fejl ved video bearbejdning {index}: {e}")
        import traceback
        traceback.print_exc()
        return None


def transcribe_with_whisper(audio_path: str) -> list:
    """
    Transcribes audio using Whisper and returns word-level timestamps.
    
    Returns:
        List of word dicts with 'text', 'start', 'end' keys.
    """
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True, language="da")
        
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
        
        return words
    except Exception as e:
        print(f"⚠️ Whisper fejl: {e}")
        return []


def group_words_for_subtitles(words: list, max_words: int = 4) -> list:
    """
    Groups words into subtitle segments.
    
    Returns:
        List of subtitle dicts with 'text', 'start', 'end' keys.
    """
    subtitles = []
    current_group = []
    
    for word in words:
        current_group.append(word)
        
        if len(current_group) >= max_words or word["text"].endswith((".", "!", "?")):
            if current_group:
                text = " ".join(w["text"] for w in current_group)
                subtitles.append({
                    "text": text,
                    "start": current_group[0]["start"],
                    "end": current_group[-1]["end"]
                })
                current_group = []
    
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
        TextClip positioned in safe zone.
    """
    display_text = text.upper().strip()
    
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
    
    # Calculate y position to prevent clipping
    text_height = text_clip.h
    stroke_padding = 4 * 2 + 10
    y_position = TIKTOK_SIZE[1] - 400 - text_height - stroke_padding
    
    return text_clip.with_duration(duration).with_start(start_time).with_position(("center", y_position))


def assemble_subarticle_video(
    processed_videos: list,
    audio_paths: list,
    subarticle_texts: list,
    output_name: str
) -> Optional[str]:
    """
    Assembles the final TikTok video from processed sub-article clips.
    
    Args:
        processed_videos: List of processed video paths (one per sub-article)
        audio_paths: List of audio paths (one per sub-article)
        subarticle_texts: List of text strings for subtitle generation
        output_name: Output filename (without extension)
    
    Returns:
        Path to the final video, or None on failure.
    """
    try:
        print("\n🎥 Sammensætter final video...")
        
        video_clips = []
        all_subtitles = []
        current_time = 0.0
        
        for i, (video_path, audio_path, text) in enumerate(zip(processed_videos, audio_paths, subarticle_texts)):
            if video_path is None or audio_path is None:
                continue
            
            # Load video and audio
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(audio_path)
            
            # Resize video to fill TikTok frame (scale up and crop if needed)
            video_w, video_h = video_clip.size
            target_w, target_h = TIKTOK_SIZE
            
            # Calculate scale to fill frame (cover, not contain)
            scale_w = target_w / video_w
            scale_h = target_h / video_h
            scale = max(scale_w, scale_h)  # Use max to ensure full coverage
            
            # Resize to fill
            video_clip = video_clip.resized(scale)
            
            # Center crop to exact TikTok size
            new_w, new_h = video_clip.size
            x_center = (new_w - target_w) // 2
            y_center = (new_h - target_h) // 2
            video_clip = video_clip.cropped(x1=x_center, y1=y_center, x2=x_center + target_w, y2=y_center + target_h)
            
            # Attach audio to video
            video_with_audio = video_clip.with_audio(audio_clip)
            
            # Add a brief white flash at the start of each segment (except first)
            if i > 0:
                # Create a short black frame transition (0.1s)
                from moviepy import ColorClip
                transition = ColorClip(size=TIKTOK_SIZE, color=(0, 0, 0), duration=0.1)
                video_clips.append(transition)
                current_time += 0.1
            
            # Generate subtitles for this segment
            words = transcribe_with_whisper(audio_path)
            if words:
                subtitles = group_words_for_subtitles(words, max_words=4)
                # Offset subtitle times by current position in final video
                for sub in subtitles:
                    all_subtitles.append({
                        "text": sub["text"],
                        "start": sub["start"] + current_time,
                        "end": sub["end"] + current_time
                    })
            
            video_clips.append(video_with_audio)
            current_time += video_clip.duration
        
        if not video_clips:
            print("❌ Ingen video clips at sammensætte")
            return None
        
        # Concatenate all video clips
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # Create subtitle clips
        subtitle_clips = []
        for sub in all_subtitles:
            duration = sub["end"] - sub["start"]
            if duration > 0:
                clip = create_tiktok_subtitle(sub["text"], duration, sub["start"])
                subtitle_clips.append(clip)
        
        # Overlay subtitles on video
        if subtitle_clips:
            final_with_subs = CompositeVideoClip([final_video] + subtitle_clips, size=TIKTOK_SIZE)
        else:
            final_with_subs = final_video
        
        # Export final video
        output_path = FINAL_DIR / f"{output_name}.mp4"
        final_with_subs.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="fast"
        )
        
        # Cleanup
        for clip in video_clips:
            clip.close()
        final_video.close()
        final_with_subs.close()
        
        print(f"✅ Final TikTok video: {output_path}")
        return str(output_path)
    
    except Exception as e:
        print(f"❌ Fejl ved video sammensætning: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_subarticle_news_video(report: dict, video_index: int = 0, reuse_existing: bool = False) -> Optional[str]:
    """
    Main function to generate a TikTok-style news video using sub-article flow.
    
    Steps:
        1. Extract sub-articles from the report
        2. For each sub-article:
           - Generate TTS audio
           - Generate 5s pixverse video
           - Slow down and loop video to match audio duration
        3. Assemble final video with subtitles
    
    Args:
        report: Dict with 'titel', 'manchet', 'indhold' keys
        video_index: Index for output filename
        reuse_existing: If True, skip regenerating videos/audio that already exist
    
    Returns:
        Path to the final video, or None on failure.
    """
    # Clear old output before starting (unless reusing)
    if not reuse_existing:
        clear_output()
    else:
        print("♻️ Reuse mode: Genbruger eksisterende filer...")
        _ensure_directories()
    
    print(f"\n{'='*60}")
    print(f"🎬 GENERERER SUB-ARTIKEL TIKTOK VIDEO FOR: {report['titel']}")
    print(f"{'='*60}\n")
    
    # Step 1: Extract sub-articles (or load from cache)
    subarticles_cache = OUTPUT_DIR / "subarticles_cache.json"
    subarticles = None
    
    if reuse_existing and subarticles_cache.exists():
        try:
            with open(subarticles_cache, "r", encoding="utf-8") as f:
                subarticles = json.load(f)
            print(f"♻️ Genbruger cached sub-artikler: {len(subarticles)} segmenter")
        except Exception:
            pass
    
    if subarticles is None:
        print("📝 Ekstraherer sub-artikler med Gemini...")
        subarticles = extract_subarticles(report)
        if not subarticles:
            return None
        # Save to cache
        with open(subarticles_cache, "w", encoding="utf-8") as f:
            json.dump(subarticles, f, ensure_ascii=False, indent=2)
        print(f"💾 Sub-artikler gemt til cache")
    
    # Step 2: Generate audio for all sub-articles
    print("\n🔊 Genererer tale for hvert segment...")
    audio_results = []
    for i, sub in enumerate(subarticles):
        audio_path = AUDIO_DIR / f"subarticle_{i}.mp3"
        
        # Check if audio already exists
        if reuse_existing and audio_path.exists():
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration
            audio_clip.close()
            print(f"♻️ Genbruger audio {i}: {duration:.2f}s")
            audio_results.append((str(audio_path), duration))
        else:
            result = generate_subarticle_speech(sub["text"], i)
            audio_results.append(result)
    
    # Step 3: Generate videos for all sub-articles
    print("\n🎬 Genererer AI videoer med pixverse...")
    
    # Check which videos need to be generated
    videos_to_generate = []
    existing_videos = {}
    
    for i, sub in enumerate(subarticles):
        video_path = VIDEOS_DIR / f"clip_{i}.mp4"
        if reuse_existing and video_path.exists():
            print(f"♻️ Genbruger video {i}: {video_path}")
            existing_videos[i] = str(video_path)
        else:
            videos_to_generate.append((i, sub["video_prompt"]))
    
    # Generate only missing videos
    video_results = dict(existing_videos)
    if videos_to_generate:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(generate_video_clip, prompt, idx): idx
                for idx, prompt in videos_to_generate
            }
            for future in as_completed(futures):
                idx = futures[future]
                video_results[idx] = future.result()
    
    # Sort by index
    video_paths = [video_results.get(i) for i in range(len(subarticles))]
    
    # Step 4: Slow down and loop videos to match audio duration
    print("\n🐢 Bearbejder videoer (slow motion + loop)...")
    processed_videos = []
    for i, (video_path, (audio_path, duration)) in enumerate(zip(video_paths, audio_results)):
        if video_path and duration > 0:
            # Check if processed video already exists
            processed_path = CLIPS_DIR / f"processed_{i}.mp4"
            if reuse_existing and processed_path.exists():
                print(f"♻️ Genbruger bearbejdet video {i}")
                processed_videos.append(str(processed_path))
            else:
                processed = slow_and_loop_video(video_path, duration, i)
                processed_videos.append(processed)
        else:
            processed_videos.append(None)
    
    # Step 5: Assemble final video
    audio_paths = [r[0] for r in audio_results]
    subarticle_texts = [sub["text"] for sub in subarticles]
    
    safe_title = "".join(
        c for c in report["titel"][:30] 
        if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    output_name = f"tiktok_subarticle_{video_index}_{safe_title}"
    
    video_path = assemble_subarticle_video(
        processed_videos, audio_paths, subarticle_texts, output_name
    )
    
    return video_path
