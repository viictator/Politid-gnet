"""
Sub-Article TikTok Video Generator - Main Entry Point

This script runs the new sub-article video flow:
1. Scrapes police reports from politi.dk
2. Scores and selects the best report using Gemini
3. Breaks the report into sub-articles
4. For each sub-article:
   - Generates voice audio with ElevenLabs
   - Generates a 5-second AI video with selected model
   - Slows down and loops the video to match audio duration
5. Assembles the final TikTok video with subtitles

Usage:
    python subarticle_main.py                    # Normal run (regenerates everything)
    python subarticle_main.py --reuse            # Reuse existing files to save money
    python subarticle_main.py --model minimax    # Use different video model
    
Available models: pixverse (default), minimax, luma, ltx-video, hunyuan
"""

import sys
import io
import json
import argparse
from pathlib import Path
from scraper.scraper import scrape, DANISH_TODAY
from scraper.aiFunctions import getBestReport
from video.subarticle_video_generator import generate_subarticle_news_video, set_video_model, VIDEO_MODELS

# Fix for emoji/Unicode errors on Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Cache file for report data
CACHE_FILE = Path("output/report_cache.json")


def save_report_cache(report: dict) -> None:
    """Save report data to cache file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"💾 Rapport gemt til cache: {CACHE_FILE}")


def load_report_cache() -> dict | None:
    """Load report data from cache file if it exists."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            report = json.load(f)
        print(f"♻️ Genbruger cached rapport: {report.get('titel', 'Ukendt')}")
        return report
    return None


def main():
    """
    Main workflow for sub-article video generation.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Sub-Article TikTok Video Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available video models:
  pixverse   - PixVerse v4.5 (default, fast, good quality)
  minimax    - MiniMax Video-01 (high quality, slower)
  luma       - Luma Ray (cinematic style)
  ltx-video  - LTX Video (Lightricks, fast)
  hunyuan    - Tencent HunyuanVideo (high quality, slow)
        """
    )
    parser.add_argument("--reuse", action="store_true", 
                        help="Reuse existing videos/audio/data files to save money")
    parser.add_argument("--model", type=str, default="pixverse",
                        choices=list(VIDEO_MODELS.keys()),
                        help="Video generation model to use (default: pixverse)")
    args = parser.parse_args()
    
    # Set the video model
    set_video_model(args.model)
    
    print("\n" + "="*60)
    print("🚔 POLITI DØGNRAPPORT - SUB-ARTIKEL VIDEO GENERATOR")
    print(f"🎬 Video model: {args.model}")
    if args.reuse:
        print("♻️  REUSE MODE: Genbruger eksisterende filer")
    print("="*60 + "\n")
    
    best_report = None
    
    # Check for cached report data if reusing
    if args.reuse:
        best_report = load_report_cache()
    
    # If no cached report, scrape and analyze
    if best_report is None:
        # Step 1: Scrape reports
        print("📡 Scraper døgnrapporter...")
        resultater = scrape()
        
        if not resultater:
            print("❌ Ingen rapporter fundet for i dag.")
            return
        
        print(f"✅ Scraping færdig. {len(resultater)} rapporter fundet.")
        
        # Step 2: Analyze and rank reports
        print("\n🤖 Analyserer rapporter med Gemini...")
        scannede_rapporter = getBestReport(resultater)
        
        if not scannede_rapporter:
            print("❌ Ingen rapporter blev scannet af Gemini.")
            return
        
        # Show top reports
        print("\n" + "="*60)
        print(f"TOP NYHEDER FRA DØGNRAPPORTEN (Dato: {DANISH_TODAY})")
        print("="*60)
        
        for i, r in enumerate(scannede_rapporter[:3]):
            print(f"{i+1}. [{r['nyhedsscore']}/10] - {r['titel']}")
            print(f"   Begrundelse: {r['begrundelse']}")
            print(f"   Link: {r['url']}\n")
        
        best_report = scannede_rapporter[0]
        
        # Save to cache for future --reuse runs
        save_report_cache(best_report)
    
    # Step 3: Generate sub-article video for the best report
    print(f"\n🎯 Vælger bedste rapport til video: {best_report['titel']}")
    print("🎬 Starter SUB-ARTIKEL video generation...")
    
    video_path = generate_subarticle_news_video(
        best_report, 
        video_index=0, 
        reuse_existing=args.reuse
    )
    
    if video_path:
        print("\n" + "="*60)
        print("✅ SUB-ARTIKEL VIDEO GENERATION FÆRDIG!")
        print(f"📹 Video gemt: {video_path}")
        print("="*60)
    else:
        print("\n❌ Video generation fejlede.")


if __name__ == "__main__":
    main()
