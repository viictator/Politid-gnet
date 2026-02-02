import sys
import io
from scraper.scraper import scrape, DANISH_TODAY
from scraper.aiFunctions import getBestReport
from video.video_generator import generate_news_video

# Fiks for emoji/Unicode fejl på Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    """
    Hovedworkflow:
    1. Scrape døgnrapporter fra politi.dk
    2. Analyser og find den bedste rapport med Gemini
    3. Generer voice script
    4. Generer billeder med Replicate
    5. Generer tale med ElevenLabs
    6. Sammensæt video med MoviePy
    """
    print("\n" + "="*60)
    print("🚔 POLITI DØGNRAPPORT VIDEO GENERATOR")
    print("="*60 + "\n")
    
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
    
    # Step 3: Generate video for the best report
    best_report = scannede_rapporter[0]
    print(f"\n🎯 Vælger bedste rapport til video: {best_report['titel']}")
    
    video_path = generate_news_video(best_report, video_index=0)
    
    if video_path:
        print("\n" + "="*60)
        print("✅ VIDEO GENERATION FÆRDIG!")
        print(f"📹 Video gemt: {video_path}")
        print("="*60)
    else:
        print("\n❌ Video generation fejlede.")


if __name__ == "__main__":
    main()
