import sys
import io
import os
from moviepy import AudioFileClip
from scraper.reportscraper import scrape
from utility.util import DANISH_TODAY
from scraper.aiFunctions import (
    getBestReport, createVideoPrompt, createVoiceScript, 
    generate_audio, get_multiple_pexels_videos, 
    get_transcription_timestamps, compose_video_with_subs,
    get_video_search_params
)

# Fiks for emoji/Unicode fejl på Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# --- TEST DATA ---
TEST_REPORTS = [
    {
        "titel": "Massiv biljagt gennem Odense",
        "manchet": "En stjålet Audi satte kurs mod gågaden i nat.",
        "indhold": "Politiet måtte bruge sømmåtter for at stoppe en vanvidsbilist, der kørte over 140 km/t i byzonen. Føreren blev anholdt på stedet.",
        "url": "https://politi.dk/test1",
        "index": 0
    },
    {
        "titel": "Butikstyv med hang til luksuschokolade",
        "manchet": "En 45-årig mand blev taget på fersk gerning.",
        "indhold": "Manden forsøgte at smugle 40 plader marabou ud under jakken i en lokal Netto. Han er nu sigtet for butikstyveri.",
        "url": "https://politi.dk/test2",
        "index": 1
    }
]

TEST_VOICE_SCRIPT = """
Det her er ikke noget man ser hver dag... i Odense blev en vanvidsbilist stoppet efter en vild jagt gennem gågaden i nat. 
Men det var ikke det eneste mærkelige der skete... for i en lokal Netto forsøgte en mand at smugle fyrre plader chokolade ud under jakken. 
Hvad synes du? Er chokolade-tyven eller bilisten dagens dummeste? Skriv det i kommentarerne!
"""

if __name__ == "__main__":
    # --- AUTOMATION SWITCHES ---
    USE_MOCK_DATA = True    # True: Brug TEST_REPORTS | False: Kør browser-scraper
    USE_MOCK_SCRIPT = True  # True: Brug TEST_VOICE_SCRIPT | False: Spørg Gemini AI
    USE_MOCK_AUDIO = True   # True: Bruger test mp3 fil.
    USE_MOCK_PEXELS = False # False: AI finder selv klip og downloader dem!

    # 1. INDHENT DATA
    if USE_MOCK_DATA:
        print("💡 Mode: Bruger TEST DATA (Scraper deaktiveret)")
        resultater = TEST_REPORTS
    else:
        print("🌐 Mode: Kører LIVE Scraper...")
        resultater = scrape()
    
    if resultater:
        # 2. ANALYSE (Gemini scoring)
        scannede_rapporter = resultater if USE_MOCK_DATA else getBestReport(resultater)
        
        if scannede_rapporter:
            # 3. VOICE SCRIPT GENERERING
            if USE_MOCK_SCRIPT:
                print("💡 Mode: Bruger TEST SCRIPT")
                final_script = TEST_VOICE_SCRIPT
            else:
                print("🎙️ Mode: Genererer nyt script via Gemini...")
                final_script = createVoiceScript(scannede_rapporter[:3])
            
            # 4. LYD GENERERING
            if USE_MOCK_AUDIO:
                print("💡 Mode: Bruger 'mock_audio.mp3'")
                audio_file = "mock_audio.mp3"
            else:
                audio_file = generate_audio(final_script, "output_voiceover.mp3")
            
            if os.path.exists(audio_file):
                print(f"✅ Lyd klar: {audio_file}")
                
                # --- NY AUTOMATISK VIDEO LOGIK ---
                
                # A. Find varighed og få søgeord fra Gemini
                audio_info = AudioFileClip(audio_file)
                duration = audio_info.duration
                
                if USE_MOCK_PEXELS:
                    print("💡 Mode: Bruger lokale test-klip")
                    video_files = ["video_clip_0.mp4", "video_clip_1.mp4"]
                else:
                    print(f"🧠 Analyserer varighed ({duration:.2f}s) for at finde optimale søgeord...")
                    search_terms = get_video_search_params(duration, final_script)
                    print(f"🔎 AI foreslår klip: {', '.join(search_terms)}")
                    
                    # B. Download klip fra Pexels baseret på AI-søgeord
                    video_files = get_multiple_pexels_videos(search_terms)
                
                # 5. TRANSKRIPTERING & SAMMENSÆTNING
                if video_files and all(os.path.exists(f) for f in video_files):
                    print("📝 Whisper genererer tidsstempler...")
                    timestamps = get_transcription_timestamps(audio_file, final_script)
                    
                    print("🎬 Sammensætter final video med undertekster...")
                    output = compose_video_with_subs(video_files, audio_file, timestamps)
                    print(f"\n🔥 BOOM! Videoen er klar: {output}")
                else:
                    print("❌ Fejl: Kunne ikke skaffe de nødvendige videofiler.")
            
        else:
            print("❌ Ingen rapporter blev scannet.")
    else:
        print("❌ Ingen rapporter fundet.")