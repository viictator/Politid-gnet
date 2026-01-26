import sys
import io
from scraper.scraper import scrape
from scraper.aiFunctions import getBestReport, createVideoPrompt
from scraper.main import DANISH_TODAY

# Fiks for emoji/Unicode fejl på Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


if __name__ == "__main__":
    resultater = scrape()
    
    if resultater:
        print(f"✅ Scraping færdig. {len(resultater)} rapporter klar til analyse.")
        scannede_rapporter = getBestReport(resultater)
        
        if scannede_rapporter:
            print("\n" + "="*60)
            print(f"TOP NYHEDER FRA DØGNRAPPORTEN (Dato: {DANISH_TODAY})")
            print("="*60)
            
            for i, r in enumerate(scannede_rapporter[:3]): # Vis de top 3
                print(f"{i+1}. [{r['nyhedsscore']}/10] - {r['titel']}")
                print(f"   Begrundelse: {r['begrundelse']}")
                print(f"   Link: {r['url']}\n")
                print(f"   Index: {r['index']}\n")

                #print(final_reports[r['index']])
                print()

            for i, r in enumerate(scannede_rapporter[:3]):
                video_prompt = createVideoPrompt(r['indhold'])
                print(f"🎬 Video prompt for nyhed {i+1} gemt")
                # add video prompten til det respektive rapport objekt
                scannede_rapporter[i]['video_prompt'] = video_prompt 

            # Udskriv de top 3 rapporter med video prompts pænt format
            print("\n" + "="*60)
            print("TOP 3 RAPPORTER MED VIDEO PROMPTS")
            print("="*60)
            for i, r in enumerate(scannede_rapporter[:3]):
                print(f"{i+1}. Titel: {r['titel']}")
                print(f"   Video Prompt: {r['video_prompt']}\n")
                print(f"   orginalIndex: {r['index']}\n")
                print()
        else:
            print("❌ Ingen rapporter blev scannet af Gemini.")
    else:
        print("❌ Ingen rapporter fundet for i dag.")
