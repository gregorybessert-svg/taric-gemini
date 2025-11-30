#!/usr/bin/env python3
"""
Automatischer Watcher für TARIC Bulk-Evaluation.

Funktion:
- Beobachtet den Ordner data/taric_bulk_input
- Wenn neue Bilddateien auftauchen, wird automatisch bulk-evaluation.py gestartet
- Achtet darauf, dass nicht mehrere Bulk-Runs parallel laufen
- Prüft vor jedem Run den Health-Status des FastAPI-Backends (/health)

Voraussetzungen:
    pip install watchdog requests

Start:
    cd ~/projects/taric-gemini
    source .venv_taric/bin/activate   # falls du eine venv nutzt
    ./bulk_evaluation_watcher.py      # oder: python3 bulk_evaluation_watcher.py
"""

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Set
from urllib.parse import urlparse, urlunparse

import requests
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from watchdog.observers import Observer


# ---------------------------------------------------------------------------
# KONFIGURATION
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "taric_bulk_input"

# bulk-evaluation Script-Datei
BULK_SCRIPT = BASE_DIR / "bulk-evaluation.py"

# Log-Level (überschreibbar via ENV)
LOG_LEVEL = os.getenv("BULK_WATCHER_LOGLEVEL", "INFO").upper()

# Backend-URL wie in bulk-evaluation.py (Standardwert identisch halten!)
BACKEND_CLASSIFY_URL = os.getenv("TARIC_BACKEND_URL", "http://127.0.0.1:8000/classify")

# Erlaubte Dateiendungen – identisch zu bulk-evaluation.py
ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("bulk_watcher")


# ---------------------------------------------------------------------------
# HILFSFUNKTIONEN
# ---------------------------------------------------------------------------

def ensure_input_dir() -> None:
    """Stellt sicher, dass der INPUT_DIR existiert."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Watching input directory: %s", INPUT_DIR)


def build_health_url() -> str:
    """
    Baut aus der Classify-URL (…/classify) die Health-URL (…/health).
    Falls das nicht eindeutig möglich ist, wird einfach '/health' an die Base-URL gehängt.
    """
    parsed = urlparse(BACKEND_CLASSIFY_URL)
    path = parsed.path or ""
    if path.endswith("/classify"):
        new_path = path[: -len("/classify")] + "/health"
    else:
        new_path = "/health"
    parsed = parsed._replace(path=new_path, params="", query="", fragment="")
    return urlunparse(parsed)


def check_backend_health(timeout: float = 3.0) -> bool:
    """Prüft, ob das FastAPI-Backend über /health erreichbar ist."""
    url = build_health_url()
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.ok:
            data = resp.json()
            status = str(data.get("status", "")).lower()
            if status == "ok":
                logger.info("Backend-Health OK: %s", url)
                return True
            logger.warning("Backend-Health unerwartete Antwort: %s -> %s", url, data)
            return False
        logger.warning("Backend-Health HTTP-Fehler: %s -> %s", url, resp.status_code)
        return False
    except Exception as e:
        logger.warning("Backend-Health Anfrage fehlgeschlagen: %s (%s)", url, e)
        return False


@dataclass
class BulkRunnerState:
    """Einfache Statusverwaltung, um parallele Runs zu verhindern."""
    is_running: bool = False
    pending: bool = False


state = BulkRunnerState()


def trigger_bulk_run(reason: str) -> None:
    """
    Löst einen Bulk-Run aus, sofern nicht bereits einer läuft.
    Wenn aktuell ein Run läuft, wird lediglich ein 'pending'-Flag gesetzt.
    """
    global state
    logger.info("Trigger Bulk-Evaluation (%s)", reason)

    if state.is_running:
        logger.info("Bulk-Evaluation läuft bereits – merke pending Run.")
        state.pending = True
        return

    state.is_running = True
    state.pending = False

    # Backend-Health prüfen
    if not check_backend_health():
        logger.warning("Backend nicht gesund/erreichbar – überspringe diesen Run.")
        state.is_running = False
        return

    # Subprozess für bulk-evaluation.py starten
    cmd = [sys.executable, str(BULK_SCRIPT)]
    logger.info("Starte bulk-evaluation: %s", " ".join(cmd))

    try:
        proc = subprocess.run(cmd, cwd=str(BASE_DIR))
        if proc.returncode == 0:
            logger.info("bulk-evaluation erfolgreich beendet (Exit-Code 0).")
        else:
            logger.warning("bulk-evaluation beendet mit Exit-Code %s.", proc.returncode)
    except FileNotFoundError:
        logger.error("bulk-evaluation.py nicht gefunden unter: %s", BULK_SCRIPT)
    except Exception as e:
        logger.error("Fehler beim Start von bulk-evaluation.py: %s", e)

    # Run ist beendet
    state.is_running = False

    # Falls in der Zwischenzeit neue Dateien eingetroffen sind, direkt neuen Run starten
    if state.pending:
        logger.info("Pending Run erkannt – starte weiteren Bulk-Evaluation-Run.")
        trigger_bulk_run("pending")


class NewInputHandler(FileSystemEventHandler):
    """
    Handler für neue oder verschobene Dateien in INPUT_DIR.
    Reagiert nur auf Dateien mit erlaubter Endung.
    """

    def _handle_path(self, path: Path) -> None:
        if not path.is_file():
            return
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            logger.debug("Ignoriere %s (nicht unterstützte Endung)", path.name)
            return

        logger.info("Neue Input-Datei erkannt: %s", path.name)
        # Kleines Delay, damit Datei-Write sicher abgeschlossen ist
        time.sleep(0.2)
        trigger_bulk_run(f"neue Datei: {path.name}")

    def on_created(self, event: FileCreatedEvent) -> None:
        self._handle_path(Path(event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        self._handle_path(Path(event.dest_path))


def main() -> None:
    ensure_input_dir()

    if not BULK_SCRIPT.exists():
        logger.error("bulk-evaluation.py wurde nicht gefunden: %s", BULK_SCRIPT)
        sys.exit(1)

    logger.info("Backend Classify URL: %s", BACKEND_CLASSIFY_URL)
    logger.info("Health-Check URL     : %s", build_health_url())
    logger.info("Starte Bulk-Evaluation-Watcher auf Ordner: %s", INPUT_DIR)

    event_handler = NewInputHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INPUT_DIR), recursive=False)
    observer.start()

    try:
        # Initialer Run: falls schon Dateien im Ordner liegen
        trigger_bulk_run("Initialstart")

        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Stop-Signal empfangen, Watcher wird beendet ...")
        observer.stop()

    observer.join()
    logger.info("Watcher sauber beendet.")


if __name__ == "__main__":
    main()
