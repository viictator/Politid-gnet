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
""" TEST_REPORTS = [
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
] """

TEST_REPORTS = [
    {
        "titel": "Nordsjælland Politi: uddrag af døgnrapporten 26. - 27. januar 2026",
        "manchet": "Brand, indbrud og flere færdelsuheld grundet glat føre. Her er et uddrag af døgnrapporten.",
        "indhold": "Færdselsuheld, Helsingørmotorvejen. På Helsingørmotorvejen i sydgående retning klokken 7.23 måtte en 53-årig kvinde bremse brat op på grund kødannelse. En bagvedkørende 26-årig mandlig billist påkørte på grund af den bratte opbremsning den forankørende bil. Brandvæsenet blev tilkaldt og fik ryddet op efter uheldet. Der var ingen personskade. Billister anbefales at køre efter forholdene og holde ekstra god afstand. Brand, Gentofte. Politiet modtog klokken 7.43 en anmeldelse om røgudvikling i et rækkehus. I huset befandt ejeren af huset sig i stuen, en kvindelig beboer, der var kørestolsbruger. Branden forårsagede brandskade i stue og gang og røg- og sodskader i hele resten af huset. Branden havde ikke spredt sig til naborækkehuse. En forbipassende havde hørt et højt brag fra huset og havde af den grund kigget ind i huset og set flammer. Vidnet åbnede herefter hoveddøren og fik sammen med et andet vidne reddet husets ejer ud af huset. Kvinden blev kørt til hospitalet og er trods omstændighederne uskadt. Brandårsagen efterforskes. Indbrud, Skovshovedhavn Der har i løbet af kort tid været mange indbrud i både - på Skovshoved Havn. Vi opfordrer bådejere og andre på havnen til at sikre sine ejendele og holde godt øje med evt. mistænkelige personer/adfærd på havnen. Overholdt ikke vigepligt, Gentofte. Klokken 18.27 kom en 64-årig mand fra Herlev kørende ad Jægersborgvej. I krydset ved Motorring 3 skulle han dreje til højre, hvorved han påkørte en 34-årig mand fra København, som kom cyklende ligeud. Den 34-årige blev tilset af ambulancepersonale, men der var umiddelbart ingen alvorlig personskade. Glat føre, Kgs. Lyngby. Klokken 21.33 kom en 20-årig mand fra Brønshøj kørende ad tilkørslen til Helsingørmotorvejen i sydgående retning. Bilen gled på grund af sne på vejbanen og kom til at holde skråt på kørebanen. To efterfølgende biler nåede ikke at bremse i tide, hvilket medførte et sammenstød. Ingen personer kom alvorligt til skade. Kørte ind i autoværn, Farum. Klokken 05.27 kom en 45-årig kvinde fra Kastrup kørende ad Hillerødmotorvejen. I forbindelse med et vognbaneskift mistede hun herredømmet over bilen på grund af is på vejbanen og påkørte motorvejens autoværn, hvorefter bilen endte i grøften. Kvinden kom ikke alvorligt til skade.",
        "url": "https://politi.dk/test1",
        "index": 0
    },
    {
        "titel": "Østjyllands Politi: uddrag af døgnrapporten 27. januar 2026",
        "manchet": "Mange klip til mobilsnakkende bilister i Aarhus Alt for mange bilister har for travlt med at bruge deres telefon i stedet for at koncentrere sig om at køre bil. Det viste en færdselskontrol, som Østjyllands Politi foretog mandag i Aarhus Midtby. Færdselsbetjentene stod mandag morgen omkring kl. 07.30 klar ved Skolebakken, Spanien, Thorvaldsensgade og på Silkeborgvej i Åbyhøj. Under den cirka halvanden time lange indsats blev i alt 48 bilister taget i at køre med mobilen i hånden. Det koster hver af dem en bøde på 1500 kroner plus 500 kroner til Offerfonden - og derudover får de et klip i kørekortet. Klippene blev uddelt både til førere af personbiler, busser og lastbiler. Enkelte gange var bilisternes uopmærksomhed så stor, at de var tæt på at køre ind i færdselsbetjentene, som ellers stod i tydelig uniformering og vinkede trafikanterne ind til siden. To bilister skal nu op til ny køreprøve, da deres seneste klip var det tredje i kørekortet. Vi ved, at uopmærksomhed er en af de hyppigste årsager til, at der sker færdselsuheld i trafikken, og det kan være ekstremt farligt for både dig selv og andre, hvis du ikke er fuldt koncentreret om din kørsel. Derfor er det nedslående at se, hvor mange bilister, der bruger håndholdt mobil og i den forbindelse er alt for ufokuserede i trafikken. Kør bil, når du kører bil og læg mobilen i handskerummet, siger politikommissær Amrik Singh Chadha fra Østjyllands Politis Færdselssektion. Under indsatsen blev der skrevet i alt 69 sager fordelt på 64 forskellige trafikanter. Sagerne fordelte sig på følgende vis: 48 x brug af håndholdt mobiltelefon (klip) 6 x manglende medbringelse af kørekort 2 x manglende anvendelse af sikkerhedssele 1 x køretøj med fejl og mangler 7 x cyklister uden lovpligtigt lys 4 x førere af el-løbehjul uden lovpligtig cykelhjelm 1 x sag vedrørende registreringsbekendtgørelsen. Opmærksom borger hjalp med at få standset spritbilist Det var blandt andet takket været god hjælp fra en opmærksom borger, at Østjyllands Politi mandag kunne standse en særdeles påvirket bilist på Nordjyske Motorvej ved Randers C-afkørslen. Borgeren ringede til politiet mandag eftermiddag kl. 15.32 og fortalte, at han kørte bag ved en bil, der slingrede og blev kørt meget usikkert på motorvejen i sydgående retning.Anmelderen blev sat i direkte kontakt med en patrulje, som han kunne guide til rette sted, og kort tid efter kunne betjentene dirigere den slingrende bilist ind på en rasteplads. Den 45-årige mand, der kørte bilen, var tydeligt påvirket og lugtede kraftigt af alkohol - og da han pustede i alkometer, viste det en promille meget tæt på 2,0. Da den dog lige akkurat holdt sig under, slap manden for en beslaglæggelse og konfiskation af bilen, der i øvrigt var en firmabil. Til gengæld kan den 45-årige mand nu vinke farvel til sit kørekort, og han står til at få en større bøde. Bilisten blev anholdt og fik foretaget en blodprøve, der skal fastslå den præcise promille. Indbru. Der er det seneste døgn anmeldt seks indbrud i privat beboelse i Østjyllands politikreds. På Emiliedalen i Højbjerg begået mandag d. 26/1 kl. 10.55 På Hørhavevej i Højbjerg begået mandag d. 26/1 mellem kl. 11.00 og kl. 13.30 På P.S. Krøyers Vej i Højbjerg begået mellem fredag d. 23/1 kl. 12.00 og mandag d. 26/1 kl. 14.00 På Ladefogedvej i Aarhus begået mandag d. 26/1 kl. 15.03 På Sletvej i Tranbjerg begået mandag d. 26/1 mellem kl. 12.00 og kl. 18.00 På Markedspladsen i Randers C begået tirsdag d. 27/1 kl. 02.15",
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
    USE_MOCK_SCRIPT = False # True: Brug TEST_VOICE_SCRIPT | False: Spørg Gemini AI
    USE_MOCK_AUDIO = False   # True: Bruger test mp3 fil.
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