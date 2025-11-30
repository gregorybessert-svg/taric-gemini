#!/bin/zsh
set -euo pipefail

# ─────────────────────────────────────────────
# ANSI Farben
# ─────────────────────────────────────────────
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
MAGENTA="\033[35m"
CYAN="\033[36m"
WHITE="\033[37m"
RESET="\033[0m"
BOLD="\033[1m"

PROJECT_DIR="/Users/qb/projects/taric-gemini"
cd "$PROJECT_DIR"

BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"
CF_FE_LOG="$PROJECT_DIR/cf_frontend.log"
CF_BE_LOG="$PROJECT_DIR/cf_backend.log"

echo ""
echo "${MAGENTA}${BOLD}─────────────────────────────────────────────${RESET}"
echo "${CYAN}${BOLD}   Live-Log-Monitor für TARIC-Gemini${RESET}"
echo "${MAGENTA}${BOLD}─────────────────────────────────────────────${RESET}"
echo ""
echo "${YELLOW}Logs:${RESET}"
echo "  ${CYAN}[BACKEND]${RESET}      → backend.log"
echo "  ${GREEN}[FRONTEND]${RESET}    → frontend.log"
echo "  ${BLUE}[CF-FE]${RESET}        → cf_frontend.log"
echo "  ${MAGENTA}[CF-BE]${RESET}     → cf_backend.log"
echo ""
echo "${YELLOW}Beenden mit: ${RED}Strg + C${RESET}"
echo ""

# Funktion zum Anhängen mit Prefix + Farbe
tail_file() {
  local file="$1"
  local label="$2"
  local color="$3"

  # -n 0 = nur neue Zeilen, -F = folgt Datei auch nach Log-Rotation
  tail -n 0 -F "$file" 2>/dev/null | while IFS= read -r line; do
    printf "%b[%s]%b %s\n" "$color" "$label" "$RESET" "$line"
  done
}

# ─────────────────────────────────────────────
# Tails parallel starten
# ─────────────────────────────────────────────

# Backend
tail_file "$BACKEND_LOG"  "BACKEND"  "$CYAN" &

# Frontend
tail_file "$FRONTEND_LOG" "FRONTEND" "$GREEN" &

# Cloudflare Frontend
tail_file "$CF_FE_LOG"    "CF-FE"    "$BLUE" &

# Cloudflare Backend
tail_file "$CF_BE_LOG"    "CF-BE"    "$MAGENTA" &

# Auf alle Hintergrund-Jobs warten, bis Ctrl+C
wait
