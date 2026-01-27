from google import genai
from utility.util import DANISH_TODAY
import json
from dotenv import load_dotenv
import os
import requests

# Indlæs miljøvariabler fra .env filen
load_dotenv()
MY_API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=MY_API_KEY)
MODEL_NAME = 'gemini-2.5-flash-lite'



def getBestReport(reports_list):
    """Bruger Gemini til at score alle rapporter og returnere dem samlet."""
    if not reports_list:
        return None

    # Vi sender titler og resuméer ind for at spare på tokens/tid
    oversigt = ""
    for i, r in enumerate(reports_list):
        oversigt += f"ID: {i}\nTitel: {r['titel']}\nResumé: {r['manchet']}\n\n"

    prompt = f"""
    Her er en liste over politiets døgnrapporter fra d. {DANISH_TODAY}.
    Vurder hver enkelt rapport og giv den en nyhedsscore fra 1-10 (hvor 10 er højeste nyhedsværdi som f.eks. drab, store røverier eller usædvanlige hændelser).
    
    Data:
    {oversigt}
    
    Svar KUN med et JSON-objekt der indeholder en liste kaldet 'analyseret_data'. 
    Hvert element i listen skal indeholde:
    - "index": (det ID jeg gav dig)
    - "nyhedsscore": (tal fra 1-10)
    - "begrundelse": (en kort dansk forklaring)

    Format:
    {{
      "analyseret_data": [
        {{"index": 0, "nyhedsscore": 8, "begrundelse": "..."}},
        ...
      ]
    }}
    """

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        if response.text is None:
            print("⚠️ Gemini returnerede ingen tekst")
            return None
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        analysis_result = json.loads(clean_text)
        
        # Nu fletter vi Gemini's scores ind i dine originale data
        scored_reports = []
        for item in analysis_result["analyseret_data"]:
            original_idx = item["index"]
            original_report = reports_list[original_idx]
            
            # Tilføj Gemini's vurdering til rapport-objektet
            original_report["nyhedsscore"] = item["nyhedsscore"]
            original_report["begrundelse"] = item["begrundelse"]
            original_report["index"] = item["index"]
            
            scored_reports.append(original_report)

        # Sorter listen så den med højeste score ligger øverst
        scored_reports.sort(key=lambda x: x["nyhedsscore"], reverse=True)
        
        return scored_reports

    except Exception as e:
        print(f"⚠️ Kunne ikke analysere med Gemini: {e}")
        return None
    
def createVideoPrompt(data: str):
    """Opretter et prompt til video generering baseret på de bedste rapporter."""

    
    prompt = "Create a prompt for a ai generated video based on the following data:\n\n" \
    f"{data}\n\n"

    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text


def createVoiceScript(reports_list):
    """
    Omdanner op til 3 rapporter til ét samlet, sammenhængende voice-over script.
    """
    if not reports_list:
        return "Ingen historier fundet."

    news_context = ""
    for i, r in enumerate(reports_list):
        news_context += f"HISTORIE {i+1}:\nTITEL: {r['titel']}\nINDHOLD: {r['indhold']}\n\n"

    prompt = f"""
    Du er en True Crime-vært på TikTok. Lav ét sammenhængende script baseret på disse {len(reports_list)} politirapporter:
    
    {news_context}
    
    STRUKTUR PÅ SCRIPTET:
    1. **HOOK**: En overordnet start der samler hændelserne (f.eks. "Politiets døgnrapport er landet, og der er især tre ting, du skal høre i dag...")
    2. **BROER**: Lav glidende overgange mellem historierne (f.eks. "Men det var ikke det eneste... for i Randers skete der noget helt andet.")
    3. **STIL**: Ingen politi-sprog. Gør det intenst, brug pauser (...) og hold et højt tempo.
    4. **OUTRO**: En samlet afslutning (f.eks. "Hvilken af de her tre sager synes du er mest vanvittig? Skriv det i kommentarerne!")

    SVAR KUN MED SELVE SCRIPTET.
    """

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Script fejl: {e}")
        return None
    

def generate_audio(voicescript, output_filename="voiceover.mp3"):
    """
    Sender scriptet til ElevenLabs og gemmer som MP3.
    """
    API_KEY = os.getenv("ELEVENLABS_API_KEY")
    # Her kan du vælge en fed stemme. 'Erik' eller 'Charlie' er gode til dansk.
    # Du finder VOICE_ID inde på deres hjemmeside.
    VOICE_ID = "pNInz6obpgDQGcFmaJgB" # Eksempel på en stemme-ID

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": API_KEY
    }

    data = {
        "text": voicescript,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }

    print(f"🔊 Sender script til ElevenLabs...")
    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        with open(output_filename, "wb") as f:
            f.write(response.content)
        print(f"✅ Lydfil gemt som {output_filename}")
        return output_filename
    else:
        print(f"❌ ElevenLabs fejl: {response.text}")
        return None
    

def get_pexels_video(query, filename):
    """Søger efter en video på Pexels og downloader den første vertikale video."""
    api_key = os.getenv("PEXELS_API_KEY")
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
    
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("videos"):
            # Vi tager den første video og finder dens download link
            video_files = data["videos"][0]["video_files"]
            # Vi leder efter en fil med god kvalitet (HD)
            download_url = video_files[0]["link"]
            
            print(f"📥 Downloader video for '{query}'...")
            v_res = requests.get(download_url)
            with open(filename, "wb") as f:
                f.write(v_res.content)
            return filename
        else:
            print(f"⚠️ Ingen video fundet for: {query}")
            return None
    except Exception as e:
        print(f"❌ Pexels fejl: {e}")
        return None