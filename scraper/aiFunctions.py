from google import genai
from scraper.main import DANISH_TODAY, MODEL_NAME, client
import json

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

