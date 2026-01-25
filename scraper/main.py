import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import date
import time

# Global variabel til at holde resultaterne
reports = []

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
DANISH_TODAY = "23. januar 2026"
""" get_danish_date() """

def scrape():
    global reports  # Fortæl funktionen at vi bruger den globale liste
    options = uc.ChromeOptions()
    driver = PatchedChrome(options=options)
    
    try:
        driver.get(BASE_URL)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "newsResult")))
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        reports = soup.select("div.newsResult")
        
        links_to_visit = []
        for report in reports:
            date_tag = report.select_one("span.newsDate")
            if date_tag and DANISH_TODAY in " ".join(date_tag.get_text().split()):
                link_tag = report.select_one("a.newsResultLink")
                if link_tag:
                    url = link_tag['href']
                    if not url.startswith("http"):
                        url = "https://politi.dk" + url
                    links_to_visit.append(url)

        print(f"🔎 Fandt {len(links_to_visit)} rapporter fra i dag. Går i gang med at indsamle tekst...")

        for link in links_to_visit:
            print(f"✅ Henter indhold fra: {link}")
            driver.get(link)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "rich-text"))
            )
            time.sleep(2)
            
            report_soup = BeautifulSoup(driver.page_source, 'html.parser')
            article_section = report_soup.select_one("#mid-section-div")
            
            if article_section:
                title = article_section.select_one("h1").get_text(strip=True) if article_section.select_one("h1") else "Ingen titel"
                manchet = article_section.select_one(".news-manchet").get_text(strip=True) if article_section.select_one(".news-manchet") else ""
                content_div = article_section.select_one(".rich-text")
                
                full_text = ""
                if content_div:
                    full_text = content_div.get_text(separator='\n', strip=True)

                # Tilføj data til vores globale liste som en dictionary
                reports.append({
                    "dato": DANISH_TODAY,
                    "titel": title,
                    "manchet": manchet,
                    "indhold": full_text,
                    "url": link
                })
            
            driver.back()
            time.sleep(2)

    except Exception as e:
        print(f"❌ Fejl: {e}")
    finally:
        driver.quit()
    
    return reports

if __name__ == "__main__":
    resultat = scrape()
    
    print("\n" + "="*30)
    print(f"SCRAPING FÆRDIG: Indsamlet {len(resultat)} rapporter.")
    print("="*30)

    # Her kan du nu tilgå dataene samlet
    for r in resultat:
        print(f"\nOverskrift: {r['titel']}")
        print(f"Længde på tekst: {len(r['indhold'])} tegn.")


def getBestReport():
    """implement gemini here to go through all the reports from the reports array. Gemini should answer back a simple integer for the index
    of which report it thinks has the best news value"""