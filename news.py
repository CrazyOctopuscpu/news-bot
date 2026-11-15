import json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from google import genai
from google.genai import types

# Nur um 18 Uhr Wiener Zeit senden (außer bei manuellem Start)
jetzt = datetime.now(ZoneInfo("Europe/Vienna"))
if os.environ.get("FORCE") != "true" and jetzt.hour != 18:
    print("Nicht 18 Uhr, Abbruch.")
    sys.exit(0)

FEEDS = [
    "https://hnrss.org/frontpage",
    "https://www.derstandard.at/rss",
    "https://rss.orf.at/news.xml",
    "https://www.heise.de/rss/heise-atom.xml",
    "https://www.tagesschau.de/index~rss2.xml",
]
INTERESTS = "KI, Technik, Open Source, Datenschutz, Wissenschaft, Wirtschaft"

items = []
for url in FEEDS:
    try:
        for e in feedparser.parse(url).entries[:25]:
            items.append({"title": e.title, "link": e.link})
    except Exception as ex:
        print("Feed-Fehler:", url, ex)

prompt = f"""Meine Interessen: {INTERESTS}
Wähle aus der Liste die 10 relevantesten Artikel für mich.
Antworte nur mit JSON in diesem Format:
[{{"title": "...", "link": "...", "why": "ein kurzer Satz auf Deutsch"}}]
Liste: {json.dumps(items, ensure_ascii=False)}"""

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
r = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(response_mime_type="application/json"),
)
picks = json.loads(r.text)

text = "\n\n".join(f"{i+1}. {p['title']}\n{p['why']}\n{p['link']}" for i, p in enumerate(picks))

requests.post(
    f"https://ntfy.sh/{os.environ['NTFY_TOPIC']}",
    data=text[:3900].encode("utf-8"),
    headers={"Title": "Deine News fuer heute"},
)
print("Gesendet.")
