# High-End Bildkonverter für TARIC-Bulk-Pipeline

Dieses Modul konvertiert Bildbestände (AVIF, JPG, JPEG, PNG) aus einem Quellordner automatisiert in das Webformat **WEBP**.  
Es ist optimiert für den Einsatz in der **TARIC-Bulk-Pipeline**, insbesondere als Vorverarbeitung vor der Modell-Evaluierung (z. B. mit `bulk-evaluation.py`).

---

## Features

- Durchsucht einen definierten Quellordner nach Bildern
- Unterstützte Formate: **AVIF, JPG, JPEG, PNG**
- Konvertiert alle Bilder nach **WEBP**
- Nutzung mehrerer CPU-Kerne via `ProcessPoolExecutor`
- Optionales Archivieren der Originalbilder in einem separaten Ordner
- Erkennung bereits vorhandener WEBP-Dateien (Duplikate werden übersprungen)
- Fortschrittsanzeige mit `tqdm` (falls installiert)
- Kompakte Statistik am Ende des Laufs
- Optionale Logging-Variante (INFO/WARN/ERROR)
- Optionale Watcher-Variante (automatische Konvertierung bei neuen Dateien)

---

## Verzeichnisstruktur und Konfiguration

Standardpfade (relativ zum Skript):

- `SOURCE_DIR = data/taric_bulk_source`  
  Quellordner mit Originalbildern (AVIF/JPG/PNG).

- `TARGET_DIR = data/taric_bulk_input`  
  Zielordner für konvertierte WEBP-Dateien.  
  Dieser Ordner wird später von der **Bulk-Evaluation** verwendet.

- `ARCHIVE_DIR = data/taric_bulk_originals`  
  Optionales Archiv für Originalbilder nach erfolgreicher Konvertierung.

Wichtige Konfigurationskonstanten im Skript:

- `ALLOWED_EXTENSIONS = {".avif", ".jpg", ".jpeg", ".png"}`
- `WEBP_QUALITY = 85` (für lossy-Formate, 0–100)
- `LOSSLESS_FOR_PNG = True` (PNG → lossless WEBP)
- `ARCHIVE_ORIGINALS = True` (Originale werden nach `ARCHIVE_DIR` verschoben)
- `MAX_WORKERS = None` (Anzahl Prozesse, `None` = Anzahl CPU-Kerne)

Diese Werte können im Python-Skript bei Bedarf angepasst werden.

---

## Installation

Voraussetzungen:

- Python 3.10+
- Virtuelle Umgebung empfohlen

Abhängigkeiten installieren:

```bash
cd /pfad/zu/deinem/projekt

# venv (optional, aber empfohlen)
python3 -m venv .venv_taric
source .venv_taric/bin/activate  # macOS / Linux
# Windows: .venv_taric\Scripts\activate

##pip install pillow tqdm watchdog
##watchdog wird nur für die Watcher-Variante benötigt, kann aber generell mitinstalliert werden.

#Verwendung: Basis-Konvertierung
- Einfacher Lauf über alle Dateien in SOURCE_DIR:
- python3 highend_bildconverter_taric.py
- Ablauf:
- SOURCE_DIR wird durchsucht.
- Alle Dateien mit erlaubten Endungen werden in eine Liste übernommen.
- Die Konvertierung läuft parallel über mehrere Prozesse.
- Für jede Datei wird eine WEBP-Datei in TARGET_DIR erzeugt.
- Optional werden Originale nach ARCHIVE_DIR verschoben.
- Zum Schluss wird eine Statistik ausgegeben.