"""Allow-listed website adapter."""
import json, os, re
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup
from .common import make_event
class WebsiteAdapter:
    source_type="website"; source_name="allowlisted_weather_web"
    def __init__(self):
        p=os.path.join(os.path.dirname(os.path.dirname(__file__)),"config","website_allowlist.json")
        self.urls=json.load(open(p,encoding="utf-8")).get("allowed_urls",[])
    def fetch_events(self):
        out=[]
        for url in self.urls:
            try:
                r=httpx.get(url,timeout=10,follow_redirects=True,headers={"User-Agent":"SIH26069-weather-platform/1.0"}); r.raise_for_status()
                text=BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True)
                if not re.search(r"rain|storm|flood|heat|wind|fog|hail|cyclone|lightning",text,re.I): continue
                out.append(make_event("website",self.source_name,url,text[:2000],datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),url))
            except Exception: continue
        return out
