import os
import re
import sys
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CF_FE_LOG = PROJECT_DIR / "cf_frontend.log"
DEFAULT_CF_BE_LOG = PROJECT_DIR / "cf_backend.log"
RECIPIENTS_FILE = PROJECT_DIR / "recipients.txt"
EMAIL_ENV_FILE = PROJECT_DIR / "email_config.env"
BACKEND_URL_JSON = PROJECT_DIR / "backend_url.json"

URL_PATTERN = re.compile(r"https://[0-9a-zA-Z.-]+\.trycloudflare\.com")

def load_env(path: Path) -> dict:
    """Einfache .env-Parser: KEY=VALUE."""
    env = {}
    if not path.exists():
        print(f"[send_link] HINWEIS: {path} nicht gefunden – E-Mail-Versand wird übersprungen.")
        return env

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env

def find_tunnel_url(log_path: Path) -> str:
    if not log_path.exists():
        raise FileNotFoundError(f"Logdatei {log_path} nicht gefunden.")
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    match = URL_PATTERN.search(text)
    if not match:
        raise RuntimeError(f"Keine Cloudflare-URL in {log_path} gefunden.")
    return match.group(0)

def load_recipients(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Empfängerliste {path} nicht gefunden.")
    recipients: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        addr = line.strip()
        if not addr or addr.startswith("#"):
            continue
        recipients.append(addr)
    if not recipients:
        raise RuntimeError("Empfängerliste ist leer.")
    return recipients

def write_backend_url_json(backend_url: str) -> None:
    data = '{ "backend_url": "' + backend_url + '" }\n'
    BACKEND_URL_JSON.write_text(data, encoding="utf-8")
    print(f"[send_link] backend_url.json geschrieben mit URL: {backend_url}")

def maybe_send_email(frontend_url: str, backend_url: str | None) -> None:
    """Versucht optional eine E-Mail zu senden. Kein Fatal-Error, wenn Config fehlt."""
    env = load_env(EMAIL_ENV_FILE)
    if not env:
        print("[send_link] INFO: Keine gültige email_config.env – E-Mail-Versand wird übersprungen.")
        return

    try:
        recipients = load_recipients(RECIPIENTS_FILE)
    except Exception as e:
        print(f"[send_link] WARNUNG: Empfänger konnten nicht geladen werden ({e}) – E-Mail wird übersprungen.")
        return

    smtp_host = env.get("SMTP_HOST")
    smtp_port = int(env.get("SMTP_PORT", "587"))
    smtp_user = env.get("SMTP_USER")
    smtp_password = env.get("SMTP_PASSWORD")
    smtp_from = env.get("SMTP_FROM", smtp_user)
    use_tls = env.get("SMTP_USE_TLS", "1")  # "1" = TLS/STARTTLS

    if not all([smtp_host, smtp_user, smtp_password, smtp_from]):
        print("[send_link] WARNUNG: SMTP_* Variablen unvollständig – E-Mail-Versand wird übersprungen.")
        return

    body_lines = [
        "Hallo,\n",
        "hier ist der aktuelle Testlink zur TARIC-Bildklassifikation über Cloudflare Quick Tunnel:\n",
        f"Frontend: {frontend_url}\n",
    ]
    if backend_url:
        body_lines.append(f"Backend (Info): {backend_url}\n")
    body_lines.append(
        "\nHinweis:\n"
        "- Frontend läuft über den obigen Link.\n"
        "- Das Frontend spricht das Backend über die in backend_url.json konfigurierte URL an.\n"
        "\nViele Grüße\nTARIC-Gemini Automation\n"
    )

    subject = "TARIC-Gemini – Testlink (Cloudflare Tunnel)"
    body = "".join(body_lines)

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)

    try:
        print(f"[send_link] Verbinde zu SMTP-Server {smtp_host}:{smtp_port} ...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        if use_tls == "1":
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, recipients, msg.as_string())
        server.quit()
        print(f"[send_link] E-Mail erfolgreich an {len(recipients)} Empfänger gesendet.")
    except Exception as e:
        print(f"[send_link] WARNUNG: E-Mail-Versand fehlgeschlagen ({e}).")
        # kein sys.exit – nur Hinweis

def main():
    # Argumente: 1 = FE-Log, 2 = BE-Log (optional)
    fe_log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CF_FE_LOG
    be_log_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CF_BE_LOG

    # URLs aus Logs lesen
    try:
        frontend_url = find_tunnel_url(fe_log_path)
        print(f"[send_link] Frontend-URL: {frontend_url}")
    except Exception as e:
        print(f"[send_link] FEHLER beim Lesen der Frontend-URL: {e}")
        sys.exit(1)

    backend_url = None
    try:
        backend_url = find_tunnel_url(be_log_path)
        print(f"[send_link] Backend-URL: {backend_url}")
    except Exception as e:
        print(f"[send_link] WARNUNG: Backend-URL konnte nicht gelesen werden: {e}")

    # backend_url.json schreiben (falls BE-URL vorhanden)
    if backend_url:
        write_backend_url_json(backend_url)
    else:
        print("[send_link] WARNUNG: Keine Backend-URL – backend_url.json wird nicht geschrieben.")

    # E-Mail nur „optional“
    maybe_send_email(frontend_url, backend_url)

if __name__ == "__main__":
    main()
