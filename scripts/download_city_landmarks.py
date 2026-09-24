"""
Download Authentic City Landmark Photography
Fetches exact iconic monument & landmark photos for all Indian cities from Wikimedia Commons / Wikipedia API
and writes them directly to both `services/frontend/public/cities/` and `services/frontend/dist/cities/`.
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_CITIES_DIR = BASE_DIR / "services" / "frontend" / "public" / "cities"
DIST_CITIES_DIR = BASE_DIR / "services" / "frontend" / "dist" / "cities"

PUBLIC_CITIES_DIR.mkdir(parents=True, exist_ok=True)
DIST_CITIES_DIR.mkdir(parents=True, exist_ok=True)

CITY_LANDMARKS = {
    "delhi": ("India_Gate", "India Gate"),
    "mumbai": ("Gateway_of_India", "Gateway of India"),
    "agra": ("Taj_Mahal", "Taj Mahal"),
    "nagpur": ("Deekshabhoomi", "Deekshabhoomi Stupa"),
    "nashik": ("Trimbakeshwar_Shiva_Temple", "Trimbakeshwar Shiva Temple"),
    "pune": ("Shaniwar_Wada", "Shaniwar Wada Palace"),
    "bengaluru": ("Vidhana_Soudha", "Vidhana Soudha"),
    "chennai": ("Kapaleeshwarar_Temple", "Kapaleeshwarar Temple"),
    "kolkata": ("Victoria_Memorial,_Kolkata", "Victoria Memorial"),
    "hyderabad": ("Charminar", "Charminar Monument"),
    "ahmedabad": ("Sabarmati_Ashram", "Sabarmati Ashram"),
    "surat": ("Surat_Castle", "Surat Old Fort Castle"),
    "jaipur": ("Hawa_Mahal", "Hawa Mahal Palace"),
    "lucknow": ("Rumi_Darwaza", "Rumi Darwaza Gate"),
    "varanasi": ("Dashashwamedh_Ghat", "Ganga Dashashwamedh Ghat"),
    "kanpur": ("JK_Temple", "JK Temple"),
    "chandigarh": ("Rock_Garden_of_Chandigarh", "Nek Chand Rock Garden"),
    "amritsar": ("Golden_Temple", "Harmandir Sahib Golden Temple"),
    "shimla": ("The_Ridge,_Shimla", "The Ridge & Christ Church"),
    "dehradun": ("Forest_Research_Institute_(India)", "Forest Research Institute"),
    "srinagar": ("Dal_Lake", "Dal Lake Shikaras"),
    "bhopal": ("Taj-ul-Masajid", "Taj-ul-Masajid"),
    "indore": ("Rajwada", "Rajwada Palace"),
    "patna": ("Golghar", "Golghar Stupa"),
    "ranchi": ("Jagannath_Temple,_Ranchi", "Jagannath Temple Ranchi"),
    "bhubaneswar": ("Lingaraja_Temple", "Lingaraja Temple"),
    "puri": ("Jagannath_Temple,_Puri", "Jagannath Temple Puri"),
    "raipur": ("Raipur", "Raipur Capital City"),
    "kochi": ("Chinese_fishing_nets", "Chinese Fishing Nets Fort Kochi"),
    "thiruvananthapuram": ("Padmanabhaswamy_Temple", "Padmanabhaswamy Temple"),
    "visakhapatnam": ("INS_Kursura_(S20)", "INS Kursura Submarine Museum"),
    "vijayawada": ("Kanaka_Durga_Temple", "Kanaka Durga Temple"),
    "coimbatore": ("Adiyogi_Shiva_statue", "Adiyogi Shiva Statue"),
    "madurai": ("Meenakshi_Temple", "Meenakshi Amman Temple"),
    "guwahati": ("Kamakhya_Temple", "Kamakhya Temple"),
    "shillong": ("Umiam_Lake", "Umiam Lake & Hills"),
    "agartala": ("Ujjayanta_Palace", "Ujjayanta Palace"),
    "imphal": ("Kangla_Fort", "Kangla Fort"),
    "panaji": ("Our_Lady_of_the_Immaculate_Conception_Church,_Goa", "Church of Our Lady of Immaculate Conception")
}

HEADERS = {
    "User-Agent": "NationalWeatherPortal/2.0 (contact@weather.gov.in; Python-urllib)"
}

def download_landmark_image(city_key: str, page_title: str, landmark_name: str) -> bool:
    api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}"
    try:
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        # Prefer originalimage, fallback to thumbnail or srcset
        img_url = (
            data.get("originalimage", {}).get("source") or
            data.get("thumbnail", {}).get("source")
        )
        
        if not img_url:
            print(f"[-] No image source found for {city_key} ({landmark_name})")
            return False
            
        img_req = urllib.request.Request(img_url, headers=HEADERS)
        with urllib.request.urlopen(img_req, timeout=20) as img_resp:
            content = img_resp.read()
            
        pub_file = PUBLIC_CITIES_DIR / f"{city_key}.jpg"
        dist_file = DIST_CITIES_DIR / f"{city_key}.jpg"
        
        pub_file.write_bytes(content)
        dist_file.write_bytes(content)
        
        print(f"[+] Downloaded {city_key:15} -> {landmark_name:35} ({len(content) // 1024} KB)")
        return True
    except Exception as e:
        print(f"[!] Error downloading {city_key} ({page_title}): {e}")
        return False

def main():
    print(f"Downloading authentic landmark photos for {len(CITY_LANDMARKS)} Indian cities...")
    success_count = 0
    for city_key, (page_title, landmark_name) in CITY_LANDMARKS.items():
        if download_landmark_image(city_key, page_title, landmark_name):
            success_count += 1
            
    print(f"\nCompleted! Successfully saved {success_count}/{len(CITY_LANDMARKS)} authentic landmark photos.")
    print(f"Public target: {PUBLIC_CITIES_DIR}")
    print(f"Dist target:   {DIST_CITIES_DIR}")

if __name__ == "__main__":
    main()

