#!/usr/bin/env bash
# tools/agent-tracker/lib/render.sh
# Dashboard renderer — consumes normalized export JSON from the Python backend (#114).
#
# No direct tmux/ps/jq-from-source calls. All data comes from the snapshot.
# Uses @tsv extraction from JSON for safe field parsing.

# Cached border strings — recalculated on terminal resize
_PREV_COLS=-1
_CACHE_eqline=""

# ─────────────────────────────────────────────────────────────────────────────
# Main render function
# ─────────────────────────────────────────────────────────────────────────────

render_dashboard() {
  local snapshot=$1 session=$2

  local COLS
  COLS=$(tput cols 2>/dev/null || echo 100)
  (( COLS < 86 )) && COLS=86
  local INNER=$(( COLS - 2 ))

  local now
  now=$(date '+%Y-%m-%d %H:%M:%S')

  # ── Column widths ──
  local W_PANE=11 W_ENGINE=12 W_STATUS=6 W_TOKENS_MIN=10 W_ACTIVITY_MIN=10
  local W_TOKENS=$W_TOKENS_MIN W_ACTIVITY=$W_ACTIVITY_MIN

  # ── Extract agent data from snapshot (single jq call for all rows) ──
  local -a agent_rows=()
  local n_working=0 n_plan=0 n_idle=0 n_stale=0 n_fault=0 n_unknown=0 n_total=0

  local agents_tsv
  agents_tsv=$(printf '%s' "$snapshot" | jq -r '
    .agents[] |
    [.pane_addr, .pane_id, .engine, .model, .status,
     (.tokens.pct | tostring), ((.tokens.used / 1000 | floor) | tostring),
     (.tokens.fresh | tostring), (.tokens.source // "unknown"),
     .task, (.activity // "")] | @tsv
  ' 2>/dev/null)

  if [[ -n "$agents_tsv" ]]; then
    while IFS=$'\t' read -r pane_addr pane_id engine model status pct tok_k tok_fresh tok_source task activity; do
      [[ -z "$pane_addr" ]] && continue
      (( n_total++ ))

      case "$status" in
        working|needs-input) (( n_working++ )) ;;
        plan)                (( n_plan++ ))    ;;
        stale)               (( n_stale++ ))   ;;
        fault)               (( n_fault++ ))   ;;
        unknown)             (( n_unknown++ )) ;;
        *)                   (( n_idle++ ))    ;;
      esac

      # Track token column width — stale uses "?" suffix, unknown shows "   ?" (#74)
      local _tok_str _tok_w
      _tok_str=$(format_tok_str "$tok_source" "$tok_fresh" "$tok_k")
      _tok_w=$(( 5 + 1 + ${#_tok_str} ))
      (( _tok_w > W_TOKENS )) && W_TOKENS=$_tok_w

      # Track activity column width
      local _act_disp _act_dw
      if [[ -z "$activity" || "$activity" == "null" ]]; then
        [[ "$status" == "idle" ]] && _act_disp="— (idle)" || _act_disp="—"
      else
        _act_disp="$activity"
      fi
      _act_dw=$(display_width "$_act_disp")
      (( _act_dw > W_ACTIVITY )) && W_ACTIVITY=$_act_dw

      # Store raw row for rendering (tab-separated, values already single-line)
      agent_rows+=("$(printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' \
        "$pane_addr" "$pane_id" "$engine" "$model" "$status" "$pct" "$tok_k" \
        "$tok_fresh" "$tok_source" "$task" "$activity")")
    done <<< "$agents_tsv"
  fi

  # Cap W_ACTIVITY so W_TASK always has room for at least 15 chars
  local W_ACTIVITY_MAX=$(( INNER - W_PANE - W_ENGINE - W_STATUS - W_TOKENS - 9 - 15 ))
  (( W_ACTIVITY_MAX < W_ACTIVITY_MIN )) && W_ACTIVITY_MAX=$W_ACTIVITY_MIN
  (( W_ACTIVITY > W_ACTIVITY_MAX )) && W_ACTIVITY=$W_ACTIVITY_MAX

  local W_TASK=$(( INNER - W_PANE - W_ACTIVITY - W_ENGINE - W_STATUS - W_TOKENS - 9 ))
  (( W_TASK < 15 )) && W_TASK=15

  # ── Recalculate borders on resize ──
  if (( COLS != _PREV_COLS )); then
    _PREV_COLS=$COLS
    _CACHE_eqline=$(make_line '═' "$INNER")
  fi

  # ── Draw header ──
  tput cup 0 0

  printf "${GRAY}╔%s╗${R}" "$_CACHE_eqline"; tput el; echo

  local title_len=13
  local gap=$(( INNER - 2 - title_len - ${#now} - 1 ))
  (( gap < 1 )) && gap=1
  printf "${GRAY}║${R}  ${BOLD}${BLUE}Agent Tracker${R}${GRAY}%*s%s ${GRAY}║${R}" \
    "$gap" "" "$now"
  tput el; echo

  printf "${GRAY}╠%s╣${R}" "$_CACHE_eqline"; tput el; echo
  printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

  # Column headers
  local h_pane h_task h_activity h_engine h_status h_tokens
  h_pane=$(pad_right "PANE" $W_PANE)
  h_task=$(pad_right "TASK" $W_TASK)
  h_activity=$(pad_right "ACTIVITY" $W_ACTIVITY)
  h_engine=$(pad_right "ENGINE" $W_ENGINE)
  h_status=$(pad_right "STATUS" $W_STATUS)
  h_tokens=$(pad_right "TOKENS" $W_TOKENS)

  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$h_pane" "$h_task" "$h_activity" "$h_engine" "$h_status" "$h_tokens"
  tput el; echo

  local d_pane d_task d_activity d_engine d_status d_tokens
  d_pane=$(make_line '─' $W_PANE)
  d_task=$(make_line '─' $W_TASK)
  d_activity=$(make_line '─' $W_ACTIVITY)
  d_engine=$(make_line '─' $W_ENGINE)
  d_status=$(make_line '─' $W_STATUS)
  d_tokens=$(make_line '─' $W_TOKENS)

  printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s %s${R}  ${GRAY}║${R}" \
    "$d_pane" "$d_task" "$d_activity" "$d_engine" "$d_status" "$d_tokens"
  tput el; echo

  # ── Agent rows ──
  if (( n_total == 0 )); then
    local no_msg
    no_msg=$(printf "  No active agents in session '%s'" "$session")
    printf "${GRAY}║${R}%-*s${GRAY}║${R}" "$INNER" "$no_msg"; tput el; echo
  else
    for row in "${agent_rows[@]}"; do
      IFS=$'\t' read -r pane_addr pane_id engine model status pct tok_k \
        tok_fresh tok_source task activity <<< "$row"

      local ecol
      [[ "$engine" == "claude" ]] && ecol="$BLUE" || ecol="$CYAN"

      local act_display
      if [[ -z "$activity" || "$activity" == "null" ]]; then
        [[ "$status" == "idle" ]] && act_display="— (idle)" || act_display="—"
      else
        act_display="$activity"
      fi

      local col_pane col_task col_activity col_engine tok_bar_str badge
      col_pane=$(trunc "$pane_addr" $W_PANE)
      col_task=$(trunc "$task" $W_TASK)
      col_activity=$(trunc "$act_display" $W_ACTIVITY)
      col_engine=$(printf "${ecol}%s${R}" "$(trunc "$model" $W_ENGINE)")
      badge=$(status_badge "$status")

      # Token display: stale uses dimmed bars + "?", unknown shows empty bars + "?" (#74)
      local tok_str
      tok_str=$(format_tok_str "$tok_source" "$tok_fresh" "$tok_k")
      if [[ "$tok_source" == "unknown" ]]; then
        tok_bar_str=$(token_bar 0 "$DARK")
      elif [[ "$tok_fresh" == "false" ]]; then
        tok_bar_str=$(token_bar "$pct" "$DARK")
      else
        tok_bar_str=$(token_bar "$pct" "$ecol")
      fi

      printf "${GRAY}║${R}  "
      printf "${GRAY}%s${R} " "$col_pane"
      printf "%s "            "$col_task"
      printf "%s "            "$col_activity"
      printf "%b "            "$col_engine"
      printf "%b "            "$badge"
      printf "%b %s  "       "$tok_bar_str" "$tok_str"
      printf "${GRAY}║${R}"
      tput el; echo
    done
  fi

  printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo
  printf "${GRAY}╠%s╣${R}" "$_CACHE_eqline"; tput el; echo

  # ── Footer ──
  # Count dead orchestrators for the footer summary (#114).
  local n_dead_orch=0
  local dead_tsv
  dead_tsv=$(printf '%s' "$snapshot" | jq -r '
    (.orchestrators // .orchestrator // [])[] |
    select(.batch_status == "dead" and (.area | type == "string") and .area != "") | .area
  ' 2>/dev/null)
  [[ -n "$dead_tsv" ]] && n_dead_orch=$(printf '%s\n' "$dead_tsv" | grep -c .)

  local n_stat="(${n_working} working"
  (( n_plan > 0 ))    && n_stat+=", ${n_plan} plan"
  (( n_stale > 0 ))   && n_stat+=", ${n_stale} stale"
  (( n_fault > 0 ))   && n_stat+=", ${n_fault} fault"
  (( n_unknown > 0 )) && n_stat+=", ${n_unknown} unknown"
  n_stat+=", ${n_idle} idle)"
  (( n_dead_orch > 0 )) && n_stat+=" ● ${n_dead_orch} dead orch"

  local left_colored="${GREEN}●${R} ${GRAY}Active: ${n_total} agents ${n_stat}${R}"
  local left_plain="● Active: ${n_total} agents ${n_stat}"

  local footer_len=$(( 2 + $(display_width "$left_plain") ))
  local fpad=$(( INNER - footer_len - 1 ))
  (( fpad < 0 )) && fpad=0

  printf "${GRAY}║${R}  %b%*s ${GRAY}║${R}" \
    "$left_colored" "$fpad" ""
  tput el; echo

  # ── Orchestrator sections ──
  _render_orchestrator "$snapshot" "$INNER"

  printf "${GRAY}╚%s╝${R}" "$_CACHE_eqline"; tput el; echo
  tput ed
}

# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator batch rendering
# ─────────────────────────────────────────────────────────────────────────────

_render_orchestrator() {
  local snapshot=$1 INNER=$2

  local orch_count
  # Support both .orchestrators (Python backend export) and .orchestrator (legacy) (#114).
  orch_count=$(printf '%s' "$snapshot" | jq '(.orchestrators // .orchestrator // []) | length' 2>/dev/null)
  [[ -z "$orch_count" || "$orch_count" == "0" ]] && return

  # Column widths: ISSUE(7) STEP(13) STATUS(6) TIME(7) INFO(rest)
  local W_ISS=7 W_STEP=13 W_STAT=6 W_TIME=7
  local W_INFO=$(( INNER - W_ISS - W_STEP - W_STAT - W_TIME - 8 ))
  (( W_INFO < 10 )) && W_INFO=10

  # Extract all batch summaries (single jq call)
  local batches_tsv
  batches_tsv=$(printf '%s' "$snapshot" | jq -r '
    (.orchestrators // .orchestrator // [])[] |
    [.area, .batch_id, .batch_status,
     (.n_done | tostring), (.n_total | tostring), (.n_failed | tostring),
     .elapsed, (.dispatched | length | tostring)] | @tsv
  ' 2>/dev/null)

  [[ -z "$batches_tsv" ]] && return

  local batch_idx=0
  while IFS=$'\t' read -r area batch_id batch_status n_done n_total n_failed elapsed n_dispatched; do
    [[ -z "$area" ]] && continue

    # ── Section separator ──
    printf "${GRAY}╠%s╣${R}" "$_CACHE_eqline"; tput el; echo

    # ── Header ──
    local h_left h_right hgap h_color
    h_left="⚙ Orchestrator: ${area}"
    h_right="${n_done}/${n_total} done  ${batch_id}"
    hgap=$(( INNER - 4 - $(display_width "$h_left") - ${#h_right} ))
    (( hgap < 1 )) && hgap=1

    h_color="$GOLD"
    [[ "$batch_status" == "done" ]] && h_color="$BLUE"
    [[ "$batch_status" == "dead" ]] && h_color="$ROSE"

    printf "${GRAY}║${R}  ${BOLD}${h_color}%s${R}%*s${GRAY}%s${R}  ${GRAY}║${R}" \
      "$h_left" "$hgap" "" "$h_right"
    tput el; echo
    printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

    # ── Dispatched issues ──
    if (( n_dispatched > 0 )); then
      # Column headers
      printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s${R}  ${GRAY}║${R}" \
        "$(pad_right "ISSUE" $W_ISS)" "$(pad_right "STEP" $W_STEP)" \
        "$(pad_right "STATUS" $W_STAT)" "$(pad_right "TIME" $W_TIME)" \
        "$(pad_right "INFO" $W_INFO)"
      tput el; echo

      printf "${GRAY}║${R}  ${DARK}%s %s %s %s %s${R}  ${GRAY}║${R}" \
        "$(make_line '─' $W_ISS)" "$(make_line '─' $W_STEP)" \
        "$(make_line '─' $W_STAT)" "$(make_line '─' $W_TIME)" \
        "$(make_line '─' $W_INFO)"
      tput el; echo

      # Extract dispatched rows for this batch (single jq call per batch)
      local disp_tsv
      disp_tsv=$(printf '%s' "$snapshot" | jq -r --argjson idx "$batch_idx" '
        (.orchestrators // .orchestrator // [])[$idx].dispatched[] |
        [.issue, .step, (if .alive then "run" else "stop" end),
         .elapsed, (.pr_num | tostring),
         (.sub | if . == null then "" else .type end),
         (.sub | if . == null then "false" else (.alive | tostring) end),
         (.sub | if . == null then "" else .elapsed end),
         (.sub | if . == null then "0" else (.pid | tostring) end)] | @tsv
      ' 2>/dev/null)

      if [[ -n "$disp_tsv" ]]; then
        while IFS=$'\t' read -r issue step alive_str etime pr_num sub_type sub_alive sub_etime sub_pid; do
          [[ -z "$issue" ]] && continue

          local pr_display="-"
          [[ -n "$pr_num" && "$pr_num" != "0" ]] && pr_display="PR #${pr_num}"

          printf "${GRAY}║${R}  "
          printf "%s " "$(pad_right "#${issue}" $W_ISS)"
          printf "%s " "$(trunc "$step" $W_STEP)"
          printf "%b " "$(_orch_badge "$alive_str")"
          printf "%s " "$(pad_right "${etime:--}" $W_TIME)"
          printf "%s  " "$(trunc "$pr_display" $W_INFO)"
          printf "${GRAY}║${R}"
          tput el; echo

          # Subprocess row (review/resolve)
          if [[ -n "$sub_type" && "$sub_type" != "" ]]; then
            local sub_badge
            [[ "$sub_alive" == "true" ]] && sub_badge=$(_orch_badge run) || sub_badge=$(_orch_badge stop)

            printf "${GRAY}║${R}  "
            printf "${DARK}%s${R} " "$(pad_right "  └─" $W_ISS)"
            printf "%s " "$(trunc "/dev-${sub_type}" $W_STEP)"
            printf "%b " "$sub_badge"
            printf "%s " "$(pad_right "${sub_etime:--}" $W_TIME)"
            printf "%s  " "$(trunc "PID ${sub_pid}" $W_INFO)"
            printf "${GRAY}║${R}"
            tput el; echo
          fi
        done <<< "$disp_tsv"
      fi
    else
      local no_msg="  No dispatched issues"
      printf "${GRAY}║${R}%-*s${GRAY}║${R}" "$INNER" "$no_msg"
      tput el; echo
    fi

    printf "${GRAY}║${R}%*s${GRAY}║${R}" "$INNER" ""; tput el; echo

    # ── Orchestrator footer: elapsed + failed + [DONE] ──
    local of="" of_plain=""
    if [[ -n "$elapsed" ]]; then
      of="${GRAY}⏱ ${elapsed} elapsed${R}"
      of_plain="⏱ ${elapsed} elapsed"
    fi
    if (( n_failed > 0 )); then
      [[ -n "$of_plain" ]] && { of+="  "; of_plain+="  "; }
      of+="${ROSE}${n_failed} failed${R}"
      of_plain+="${n_failed} failed"
    fi

    local batch_label="" batch_label_plain=""
    if [[ "$batch_status" == "done" ]]; then
      batch_label="${BLUE}[DONE]${R}"
      batch_label_plain="[DONE]"
    elif [[ "$batch_status" == "dead" ]]; then
      batch_label="${ROSE}[DEAD]${R}"
      batch_label_plain="[DEAD]"
    fi

    local of_dw bl_dw bl_extra fp
    of_dw=$(display_width "$of_plain")
    bl_dw=$(display_width "$batch_label_plain")
    (( bl_dw > 0 )) && bl_extra=$(( bl_dw + 2 )) || bl_extra=0
    fp=$(( INNER - 4 - of_dw - bl_extra ))
    (( fp < 0 )) && fp=0
    if [[ -n "$batch_label" ]]; then
      printf "${GRAY}║${R}  %b%*s%b  ${GRAY}║${R}" "$of" "$fp" "" "$batch_label"
    else
      printf "${GRAY}║${R}  %b%*s  ${GRAY}║${R}" "$of" "$fp" ""
    fi
    tput el; echo

    (( batch_idx++ ))
  done <<< "$batches_tsv"
}
