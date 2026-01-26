import sys
import io
import os
import json
import time
from datetime import date
from dotenv import load_dotenv
from google import genai
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


# Fiks for emoji/Unicode fejl på Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Indlæs miljøvariabler fra .env filen
load_dotenv()
MY_API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=MY_API_KEY)
MODEL_NAME = 'gemini-2.5-flash-lite'



final_reports = [] 

def get_danish_date():
    today = date.today()
    months = ["januar", "februar", "marts", "april", "maj", "juni", 
              "juli", "august", "september", "oktober", "november", "december"]
    return f"{today.day}. {months[today.month-1]} {today.year}"

class PatchedChrome(uc.Chrome):
    def __del__(self):
        try:
            self.quit()
        except:
            pass

BASE_URL = "https://politi.dk/doegnrapporter"
DANISH_TODAY = "23. januar 2026" # Test dato

def scrape():
    global final_reports
    options = uc.ChromeOptions()
    driver = PatchedChrome(options=options)
    
    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "newsResult")))
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # OMDØBT HER: fra reports til report_cards
        report_cards = soup.select("div.newsResult")
        
        links_to_visit = []
        for card in report_cards:
            date_tag = card.select_one("span.newsDate")
            if date_tag and DANISH_TODAY in " ".join(date_tag.get_text().split()):
                link_tag = card.select_one("a.newsResultLink")
                if link_tag:
                    url = str(link_tag['href'])
                    if not url.startswith("http"):
                        url = "https://politi.dk" + url
                    links_to_visit.append(url)

        print(f"🔎 Fandt {len(links_to_visit)} links. Indhenter tekst...")

        for link in links_to_visit:
            print(f"✅ Henter: {link}")
            driver.get(link)
            
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "rich-text")))
            time.sleep(2)
            
            report_soup = BeautifulSoup(driver.page_source, 'html.parser')
            article_section = report_soup.select_one("#mid-section-div")
            
            if article_section:
                h1_tag = article_section.select_one("h1")
                title = h1_tag.get_text(strip=True) if h1_tag else "N/A"
                manchet_tag = article_section.select_one(".news-manchet")
                manchet = manchet_tag.get_text(strip=True) if manchet_tag else ""
                content_div = article_section.select_one(".rich-text")
                
                full_text = content_div.get_text(separator='\n', strip=True) if content_div else ""

                final_reports.append({
                    "dato": DANISH_TODAY,
                    "titel": title,
                    "manchet": manchet,
                    "indhold": full_text,
                    "url": link
                })
            
            driver.back()
            time.sleep(1)

    except Exception as e:
        print(f"❌ Fejl: {e}")
    finally:
        driver.quit()
    
    return final_reports


# --- HER KAN VI IMPLEMENTERE GEMINI SENERE ---
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

                print(final_reports[r['index']])
                print()


