# TARIC-Gemini – Release 2025-11-30

## Überblick
Dieses Release fokussiert sich auf die stabilere Nutzung über den Cloudflare-Tunnel, ein verbessertes Routing zum Backend und Optimierungen der UI für die Bildklassifikation und die Evaluation auf mobilen Geräten.

## Wichtige Änderungen

### Cloudflare & Backend-Routing
- Integration der Cloudflare-Tunnel-URL als Backend-Endpunkt.
- Implementierung einer flexiblen Auflösung des API-Basispfads (`resolveApiBase()`), abhängig vom Backend-Modus.
- Standard-Backendmodus jetzt **"cloudflare"** in allen relevanten HTML-Dateien (z. B. `index.html`, `evaluation.html`, `auswertung.html`), um externen Tester:innen die Nutzung zu erleichtern.

### Bild-Upload & Klassifikation
- Anpassung von `index.html`, damit Bild-Uploads korrekt an das Backend gesendet werden, auch wenn das Frontend über Cloudflare ausgeliefert wird.
- Bereinigung und Vereinheitlichung des Bildpfad-Handling für die Klassifikation.

### UI-/UX-Verbesserungen
- Optimierung der Button-Anordnung (z. B. „Zurück“, „Weiter“, „Speichern“, „Speichern & weiter“) in `evaluation.html` für bessere Bedienbarkeit auf Smartphones.
- Verbesserte Lesbarkeit und Struktur der Panels, insbesondere im Evaluations-Workflow.
- Kleinere Layout-Optimierungen für mobile Ansicht.

### Sonstiges
- Kleinere Bugfixes und interne Code-Aufräumarbeiten.
- Aktualisierung der Dokumentation für Setup und Nutzung über den Cloudflare-Tunnel.
