import os
import glob
import json
import sqlite3
import time
import mimetypes

import google.generativeai as genai


# -----------------------
# Konfiguration
# -----------------------

IMAGE_DIR = "bilder"
DB_PATH = "taric_dataset.db"

SYSTEM_PROMPT = """
Du bist ein erfahrener EU-Zoll- und TARIC-Experte.
Deine Aufgabe ist es, anhand eines Produktfotos den wahrscheinlichsten TARIC-Code
für die Ware zu bestimmen.

Rahmenbedingungen:
- Verwende die Struktur der EU TARIC-Datenbank.
- Gehe schrittweise vor:
  1. Beschreibe kurz, was auf dem Bild zu sehen ist (Art der Ware, Material,
     Verwendungszweck, besondere Merkmale).
  2. Bestimme erst die wahrscheinliche HS-Position (4-stellig),
     dann die 6-stellige Unterposition, anschließend die 8-stellige KN-Position
     und zuletzt den 10-stelligen TARIC-Code.
  3. Prüfe, ob besondere zollrechtliche Regelungen greifen könnten
     (Medizinprodukt, Lebensmittel, Elektronik, Textil usw.).

Ausgabeformat (immer als gültiges JSON, ohne zusätzlichen Text):

{
  "taric_code": "XXXXXXXXXX",
  "cn_code": "XXXXXXXX",
  "hs_chapter": "XX",
  "confidence": 0.0,
  "short_reason": "kurze Begründung in 2–4 Sätzen",
  "possible_alternatives": [
    {
      "taric_code": "YYYYYYYYYY",
      "short_reason": "warum dieser Code ebenfalls in Frage kommt"
    }
  ]
}

Regeln:
- Antworte ausschließlich in diesem JSON-Format.
- Wenn du sehr unsicher bist, gib trotzdem den besten Schätzwert und senke 'confidence'.
- Verwende nur plausible TARIC-Codes, die formal zur beschriebenen Ware passen.
"""

USER_TEXT = "Bestimme für dieses Produktfoto den TARIC-Code und gib nur das JSON aus."


# -----------------------
# Hilfsfunktionen
# -----------------------

def configure_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Bitte Umgebungsvariable GEMINI_API_KEY setzen.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    return model


def create_db(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS taric_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            taric_code TEXT,
            cn_code TEXT,
            hs_chapter TEXT,
            confidence REAL,
            short_reason TEXT,
            alternatives_json TEXT,
            raw_response_json TEXT
        );
        """
    )
    conn.commit()


def guess_mime_type(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if mime is None:
        return "image/jpeg"
    return mime


def classify_image_with_gemini(model, image_path: str) -> dict:
    mime_type = guess_mime_type(image_path)
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    response = model.generate_content(
        [
            USER_TEXT,
            {
                "mime_type": mime_type,
                "data": img_bytes,
            },
        ],
        generation_config={
            "response_mime_type": "application/json",
        },
    )

    return json.loads(response.text)


def classify_and_store(conn, model, image_path: str):
    data = classify_image_with_gemini(model, image_path)
    content_json = json.dumps(data, ensure_ascii=False)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO taric_labels
        (filename, taric_code, cn_code, hs_chapter,
         confidence, short_reason, alternatives_json, raw_response_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            os.path.basename(image_path),
            data.get("taric_code"),
            data.get("cn_code"),
            data.get("hs_chapter"),
            float(data.get("confidence", 0.0)),
            data.get("short_reason"),
            json.dumps(data.get("possible_alternatives", []), ensure_ascii=False),
            content_json,
        ),
    )
    conn.commit()


# -----------------------
# Hauptprogramm
# -----------------------

def main():
    model = configure_gemini()

    conn = sqlite3.connect(DB_PATH)
    create_db(conn)

    image_paths = sorted(
        glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
        + glob.glob(os.path.join(IMAGE_DIR, "*.jpeg"))
        + glob.glob(os.path.join(IMAGE_DIR, "*.png"))
    )

    print(f"Insgesamt gefundene Bilder: {len(image_paths)}")

    # Zum Testen erst einmal wenige Bilder:
    # image_paths = image_paths[:5]

    for i, path in enumerate(image_paths, start=1):
        print(f"[{i}/{len(image_paths)}] Verarbeite {path} ...")
        try:
            classify_and_store(conn, model, path)
        except Exception as e:
            print(f"Fehler bei {path}: {e}")
        time.sleep(0.4)

    conn.close()
    print("Fertig. Datenbank liegt unter:", DB_PATH)


if __name__ == "__main__":
    main()
