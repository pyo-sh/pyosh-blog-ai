#!/usr/bin/env bash
# tools/agent-tracker/lib/util.sh
# Pure rendering helpers — no I/O, no side effects.

# ── Constants ──
STALE_THRESHOLD_SECS=30

# ── Colors (blue accent theme) ──
R='\033[0m'
BOLD='\033[1m'
GRAY='\033[38;5;245m'
DARK='\033[38;5;238m'
BLUE='\033[38;5;74m'     # Claude / accent
CYAN='\033[38;5;37m'     # Codex
GREEN='\033[38;5;71m'    # working
GOLD='\033[38;5;136m'    # plan / pipeline
ROSE='\033[38;5;132m'    # error / needs-input

# make_line <char> <n> — repeat unicode char n times
make_line() {
  local char="$1" n="$2" s="" i
  for ((i = 0; i < n; i++)); do s+="$char"; done
  printf '%s' "$s"
}

# display_width <string> — terminal display columns (CJK=2, ASCII=1)
# ASCII fast path avoids subshell for pure-ASCII strings
display_width() {
  local s="$1"
  if [[ "$s" != *[^[:ascii:]]* ]]; then
    printf '%d' "${#s}"
  else
    printf '%s' "$s" | wc -L
  fi
}

# trunc <string> <width> — truncate by display width; pad with spaces if shorter
trunc() {
  local s="$1" w="$2"
  local dw
  dw=$(display_width "$s")
  if (( dw <= w )); then
    printf '%s%*s' "$s" "$(( w - dw ))" ""
  else
    local lo=0 hi=${#s} mid best=0
    while (( lo <= hi )); do
      mid=$(( (lo + hi) / 2 ))
      if (( $(display_width "${s:0:$mid}") <= w - 1 )); then
        best=$mid; lo=$(( mid + 1 ))
      else
        hi=$(( mid - 1 ))
      fi
    done
    local prefix="${s:0:$best}"
    local pad=$(( w - $(display_width "$prefix") - 1 ))
    printf '%s…' "$prefix"
    (( pad > 0 )) && printf '%*s' "$pad" ""
  fi
}

# pad_right <string> <width> — display-width-aware right-padding
pad_right() {
  local s="$1" w="$2" dw
  dw=$(display_width "$s")
  if (( dw < w )); then
    printf '%s%*s' "$s" "$(( w - dw ))" ""
  else
    printf '%s' "$s"
  fi
}

# token_bar <pct> <color> — render 5 blocks
token_bar() {
  local pct="$1" color="$2" bar="" i
  for ((i = 0; i < 5; i++)); do
    (( i * 20 < pct )) && bar+="${color}▰${R}" || bar+="${DARK}▱${R}"
  done
  printf '%s' "$bar"
}

# status_badge <status> — 6 visible chars
status_badge() {
  case "$1" in
    working)      printf "${GREEN}● work${R}" ;;
    plan)         printf "${GOLD}◑ plan${R}" ;;
    needs-input)  printf "${ROSE}◉ wait${R}" ;;
    error)        printf "${ROSE}✖ err ${R}" ;;
    done)         printf "${BLUE}✓ done${R}" ;;
    stale)        printf "${GOLD}~ stal${R}" ;;
    fault)        printf "${ROSE}! flt ${R}" ;;
    unknown)      printf "${ROSE}? unkn${R}" ;;
    *)            printf "${GRAY}○ idle${R}" ;;
  esac
}

# format_tok_str <tok_source> <tok_fresh> <tok_k> — 4-char token display
# Returns: "   ?" (unknown), "NNN?" (stale), "NNNk" (fresh)
format_tok_str() {
  local src=$1 fresh=$2 tk=$3
  if [[ "$src" == "unknown" ]]; then
    printf '   ?'
  elif [[ "$fresh" == "false" ]]; then
    if (( tk > 999 )); then printf '999?'; else printf '%3d?' "$tk"; fi
  else
    if (( tk > 999 )); then printf '999+'; else printf '%3dk' "$tk"; fi
  fi
}

# _orch_elapsed <seconds> — compact elapsed time
_orch_elapsed() {
  local s=$1
  (( s < 0 )) && s=0
  if (( s >= 3600 )); then
    printf '%dh%02dm' $(( s / 3600 )) $(( (s % 3600) / 60 ))
  elif (( s >= 60 )); then
    printf '%dm%02ds' $(( s / 60 )) $(( s % 60 ))
  else
    printf '%ds' "$s"
  fi
}

# _orch_badge <type> — 6 visible chars, colored
_orch_badge() {
  case "$1" in
    run)   printf "${GREEN}● run ${R}" ;;
    done)  printf "${BLUE}✓ done${R}" ;;
    stop)  printf "${ROSE}✖ stop${R}" ;;
    *)     printf "${GRAY}○ --- ${R}" ;;
  esac
}
