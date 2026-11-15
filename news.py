import json, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from google import genai
from google.genai import types

# Nur um 6 Uhr früh Wiener Zeit senden (außer bei manuellem Start)
jetzt = datetime.now(ZoneInfo("Europe/Vienna"))
if os.environ.get("FORCE") != "true" and jetzt.hour != 6:
    print("Nicht 6 Uhr, Abbruch.")
    sys.exit(0)

FEEDS = [
    "https://www.derstandard.at/rss",
    "https://rss.orf.at/news.xml",
    "https://rss.orf.at/sport.xml",
    "https://www.tagesschau.de/index~rss2.xml",
    "https://www.spiegel.de/schlagzeilen/index.rss",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.derstandard.at/rss/wirtschaft",
    "https://www.finanzen.net/rss/news",
    "https://www.reddit.com/r/todayilearned/top/.rss?t=day",
    "https://www.reddit.com/r/geography/top/.rss?t=day",
    "https://www.reddit.com/r/nottheonion/top/.rss?t=day",
]

INTERESTS = """
- Sport (Fußball, Skifahren, Formel 1, große Turniere und Ergebnisse)
- Aktien, Börse und Finanzmärkte
- Weltgeschehen und internationale Nachrichten
- Lustige und kuriose Fakten, skurrile Meldungen
- Politik (Österreich, Europa, international)
- Geografie, Länder, Reisen, Naturphänomene
"""

NICHT_INTERESSANT = """
- Promi-Klatsch und Horoskope
"""

items = []
for url in FEEDS:
    try:
        for e in feedparser.parse(url).entries[:25]:
            items.append({"title": e.title, "link": e.link})
    except Exception as ex:
        print("Feed-Fehler:", url, ex)

prompt = f"""Du bist mein persönlicher Nachrichten-Redakteur.

Meine Interessen:
{INTERESTS}

Das interessiert mich NICHT:
{NICHT_INTERESSANT}

Wähle aus der Liste die 10 besten Artikel für mich aus. Bevorzuge Neues,
Wichtiges und Überraschendes.
Nimm aus jedem meiner Interessensgebiete mindestens einen Artikel,
sofern die Liste dazu etwas hergibt.

Regeln:
- ALLES auf Deutsch. Übersetze englische Titel ins Deutsche.
- "why" ist ein kurzer Satz, warum der Artikel für mich relevant ist.
- Den Link unverändert übernehmen.

Antworte nur mit JSON in diesem Format:
[{{"title": "deutscher Titel", "link": "...", "why": "..."}}]

Liste: {json.dumps(items, ensure_ascii=False)}"""

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
r = client.models.generate_content(
    model="gemini-3.5-flash-lite",
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
