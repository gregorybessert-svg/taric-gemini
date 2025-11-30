#!/usr/bin/env python3
"""Automatischer Watcher für den High-End-Bildkonverter.

Beobachtet das SOURCE_DIR aus highend_bildconverter_taric und
konvertiert neue AVIF/JPG/PNG-Dateien automatisch nach WEBP, sobald
sie im Quellordner erscheinen.

Voraussetzungen:
    pip install watchdog pillow tqdm

Start:
    python3 highend_bildconverter_watcher.py
"""

import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from watchdog.observers import Observer

from highend_bildconverter_taric import (
    SOURCE_DIR,
    ALLOWED_EXTENSIONS,
    ensure_directories,
    convert_single_image,
)

LOG_LEVEL = "INFO"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("bildkonverter_watcher")


class NewImageHandler(FileSystemEventHandler):
    """Reagiert auf neu angelegte oder verschobene Dateien im SOURCE_DIR."""

    def _handle_path(self, path: Path) -> None:
        if not path.is_file():
            return
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            logger.debug("Ignoriere %s (nicht unterstützte Endung)", path.name)
            return

        logger.info("Neue Bilddatei erkannt: %s", path.name)
        result = convert_single_image(path)

        if result.status == "converted":
            logger.info("Konvertiert: %s", path.src_path.name)
        elif result.status == "skipped_exists":
            logger.info("Bereits vorhanden, übersprungen: %s", path.src_path.name)
        elif result.status == "skipped_unsupported":
            logger.warning("Nicht unterstützte Endung: %s", path.src_path.name)
        elif result.status == "error":
            logger.error("Fehler bei %s: %s", path.src_path.name, result.error_message)
        else:
            logger.info("Status %s für %s", result.status, path.src_path.name)

    def on_created(self, event: FileCreatedEvent) -> None:
        self._handle_path(Path(event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        self._handle_path(Path(event.dest_path))


def main() -> None:
    ensure_directories()

    if not SOURCE_DIR.exists():
        logger.info("SOURCE_DIR existiert noch nicht, wird angelegt: %s", SOURCE_DIR)
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Starte Watcher auf Ordner: %s", SOURCE_DIR)

    event_handler = NewImageHandler()
    observer = Observer()
    observer.schedule(event_handler, str(SOURCE_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Stop-Signal empfangen, Watcher wird beendet ...")
        observer.stop()

    observer.join()
    logger.info("Watcher sauber beendet.")


if __name__ == "__main__":
    main()
