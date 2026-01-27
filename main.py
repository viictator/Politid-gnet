import sys
import io
import os
from scraper.reportscraper import scrape
from utility.util import DANISH_TODAY
from scraper.aiFunctions import getBestReport, createVideoPrompt, createVoiceScript, generate_audio, get_pexels_video

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

    # 1. INDHENT DATA
    if USE_MOCK_DATA:
        print("💡 Mode: Bruger TEST DATA (Scraper deaktiveret)")
        resultater = TEST_REPORTS
    else:
        print("🌐 Mode: Kører LIVE Scraper...")
        resultater = scrape()
    
    if resultater:
        # 2. ANALYSE (Gemini scoring)
        # Vi kører kun analysen hvis vi ikke bruger mock data, 
        # eller hvis vi specifikt vil se scoring på vores test data.
        scannede_rapporter = resultater if USE_MOCK_DATA else getBestReport(resultater)
        
        if scannede_rapporter:
            # 3. VOICE SCRIPT GENERERING
            if USE_MOCK_SCRIPT:
                print("💡 Mode: Bruger TEST SCRIPT (Gemini Script deaktiveret)")
                final_script = TEST_VOICE_SCRIPT
            else:
                print("🎙️ Mode: Genererer nyt script via Gemini...")
                final_script = createVoiceScript(scannede_rapporter[:3])
            
            print("\n" + "="*60)
            print("AKTUELT VOICE SCRIPT:")
            print(final_script)
            print("="*60)

            # 4. LYD GENERERING
            if USE_MOCK_AUDIO:
                print("💡 Mode: ElevenLabs deaktiveret (Sparer penge/tokens)")
                audio_file = "mock_audio.mp3" # Vi lader som om den er lavet
            else:
                audio_file = generate_audio(final_script, "output_voiceover.mp3")
            
            if audio_file:
                print(f"\n✅ SUCCESS: Lydfil genereret: {audio_file}")


            # TEST AF VIDEO DOWNLOAD
            if resultater:
                video_files = []
                # Vi laver en hurtig liste af søgeord baseret på vores test-historier
                # I en live-version ville vi bede Gemini om disse keywords
                queries = ["police car chase", "chocolate candy"] 
                
                for i, q in enumerate(queries):
                    file_path = f"video_clip_{i}.mp4"
                    if not os.path.exists(file_path): # Spar båndbredde ved test
                        get_pexels_video(q, file_path)
                    video_files.append(file_path)
                    
                print(f"🎬 Vi har nu {len(video_files)} videoklip klar til sammensætning.")

            # 5. VIDEO PROMPTS (Kun hvis vi kører fuld pipeline)
            """ if not USE_MOCK_SCRIPT:
                for i, r in enumerate(scannede_rapporter[:3]):
                    r['video_prompt'] = createVideoPrompt(r['indhold'])
                    print(f"🎬 Video prompt {i+1} klar.") """
        else:
            print("❌ Ingen rapporter blev scannet.")
    else:
        print("❌ Ingen rapporter fundet.")