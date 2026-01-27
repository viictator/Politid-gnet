from google import genai
from utility.util import DANISH_TODAY
import json
from dotenv import load_dotenv
import os
import math
import requests
import whisper
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

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

    SVAR KUN MED SELVE SCRIPTET. OG FORESTIL DIG AT DETTE LÆSES OP AF EN NYHEDSVÆRT PÅ TIKTOK, HVOR OPLÆSNINGEN MÅ MAX VARE 1 MINUT.
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
    

def get_video_search_params(audio_duration, final_script):
    # Beregn hvor mange klip vi skal bruge (et hver 4. sekund)
    param_count = math.ceil(audio_duration / 4)
    
    print(f"🔍 Beder AI om {param_count} søgeord til stock-video...")

    prompt = f"""
    Her er et manuskript til en video om politidøgnets hændelser:
    "{final_script}"
    
    Videoen varer {audio_duration:.2f} sekunder. Jeg skal bruge præcis {param_count} korte søgeord på ENGELSK til at finde relevante stock-videoer på Pexels.
    
    Søgeordene skal:
    1. Være relevante for indholdet (f.eks. 'police car', 'handcuffs', 'night city', 'blue lights').
    2. Være varierede.
    3. Returneres som en kommasepareret liste uden numre.
    """

    # RETTELSE: Brug client.models.generate_content med MODEL_NAME
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    
    # RETTELSE: Hent teksten korrekt ud fra den nye response-struktur
    # Vi bruger .text og fjerner eventuelle linjeskift, før vi splitter ved komma
    raw_text = response.text
    search_terms = [term.strip() for term in raw_text.replace('\n', '').split(',')]
    
    # Sikr os at vi har det rigtige antal og fjern tomme strenge hvis de findes
    search_terms = [t for t in search_terms if t][:param_count]
    
    return search_terms

import requests
import os

def get_multiple_pexels_videos(queries):
    # Hent API nøglen og fjern eventuelle usynlige mellemrum/tegn
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    
    if not api_key:
        print("❌ FEJL: PEXELS_API_KEY er tom! Tjek din .env fil.")
        return []

    headers = {"Authorization": api_key}
    video_paths = []

    for i, q in enumerate(queries):
        # Lav et sikkert filnavn
        clean_q = q.replace(' ', '_').lower()
        filename = f"clip_{i}_{clean_q}.mp4"
        
        if os.path.exists(filename):
            print(f"✅ Bruger eksisterende: {filename}")
            video_paths.append(filename)
            continue

        # Pexels API URL
        url = "https://api.pexels.com/videos/search"
        params = {
            "query": q,
            "per_page": 1,
            "orientation": "portrait"
        }

        try:
            print(f"🔍 Søger på Pexels efter: '{q}'...")
            response = requests.get(url, headers=headers, params=params)
            
            # DEBUG: Hvis noget går galt, vil vi vide hvorfor
            if response.status_code != 200:
                print(f"⚠️ Pexels fejlede! Status: {response.status_code}")
                print(f"💬 Svar fra Pexels: {response.text}")
                continue

            data = response.json()
            videos = data.get("videos", [])

            if videos:
                # Find det bedste link (vi leder efter HD/1080p eller 720p)
                video_files = videos[0].get("video_files", [])
                
                # Sorter så vi får en fornuftig størrelse (ikke 4K, men ikke for lille)
                # Vi prøver at finde et link med 'hd' eller den første ledige
                download_url = None
                for vf in video_files:
                    if vf.get("width") == 1080 or vf.get("width") == 720:
                        download_url = vf["link"]
                        break
                
                if not download_url:
                    download_url = video_files[0]["link"]

                print(f"📥 Downloader: {q}...")
                res = requests.get(download_url, stream=True)
                
                if res.status_code == 200:
                    with open(filename, "wb") as f:
                        for chunk in res.iter_content(chunk_size=1024*1024):
                            f.write(chunk)
                    video_paths.append(filename)
                else:
                    print(f"❌ Kunne ikke hente selve filen for '{q}'")
            else:
                print(f"🔍 Ingen videoer fundet for søgeordet: '{q}'")

        except Exception as e:
            print(f"❌ Netværksfejl ved '{q}': {e}")

    return video_paths
    
def get_transcription_timestamps(audio_path, original_script):
    print("🧠 Whisper analyserer lyden med manuskript-hjælp...")
    model = whisper.load_model("base")
    
    # Vi giver Whisper manuskriptet som 'prompt'. 
    # Det gør at den staver ordene præcis som i dit manuskript!
    result = model.transcribe(
        audio_path, 
        language="da", 
        word_timestamps=True,
        initial_prompt=original_script
    )

    word_data = []
    for segment in result['segments']:
        for word in segment['words']:
            word_data.append({
                "word": word['word'],
                "start": word['start'],
                "end": word['end']
            })
            
    return word_data  

def create_captions(word_data, video_width=1080, video_height=1920):
    clips = []
    font_path = r"C:\Windows\Fonts\arialbd.ttf" 
    
    for item in word_data:
        word_clip = (TextClip(
            text=item['word'].upper(), 
            font_size=110,           # Lidt større font
            color='yellow', 
            stroke_color='black', 
            stroke_width=3,          # Tykkere kant for TikTok-look
            font=font_path,
            method='label',
            size=(video_width, 200)   # <--- FORCE STØRRE BOKS så intet klippes
        ).with_start(item['start'])
         .with_end(item['end'])
         .with_position(('center', 'center'))) # Centrerer både X og Y
        
        clips.append(word_clip)
    return clips

def compose_video_with_subs(video_files, audio_path, word_data, output_path="final_video_subs.mp4"):
    print("🎬 Samler video med undertekster...")
    
    audio = AudioFileClip(audio_path)
    video_clips = []
    duration_per_clip = audio.duration / len(video_files)
    
    # 1. Forbered baggrundsvideoerne
    for file in video_files:
        clip = (VideoFileClip(file)
                .subclipped(0, duration_per_clip)
                .without_audio()
                .resized(width=1080))
        video_clips.append(clip)
    
    bg_video = concatenate_videoclips(video_clips, method="compose")
    
    # 2. Generer undertekster
    caption_clips = create_captions(word_data)
    
    # 3. Læg det hele sammen (Video nederst, alle tekst-klip øverst)
    final_video = CompositeVideoClip([bg_video] + caption_clips)
    final_video = final_video.with_audio(audio)
    
    # 4. Eksport
    final_video.write_videofile(output_path, fps=24, codec="libx264")
    return output_path