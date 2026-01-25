import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import date
import time

# Global variabel til at holde de færdige data-objekter
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
                    url = link_tag['href']
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
                title = article_section.select_one("h1").get_text(strip=True) if article_section.select_one("h1") else "N/A"
                manchet = article_section.select_one(".news-manchet").get_text(strip=True) if article_section.select_one(".news-manchet") else ""
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

if __name__ == "__main__":
    resultat = scrape()
    
    print("\n" + "="*30)
    print(f"SCRAPING FÆRDIG: Indsamlet {len(resultat)} rapporter.")
    print("="*30)

    for r in resultat:
        print(f"\nOverskrift: {r['titel']}")
        print(f"Længde: {len(r['indhold'])} tegn.")

# --- HER KAN VI IMPLEMENTERE GEMINI SENERE ---
def getBestReport(reports_list):
    """Her kan du sende reports_list til Gemini API'en"""
    pass