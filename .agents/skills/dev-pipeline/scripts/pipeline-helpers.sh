#!/usr/bin/env bash
# pipeline-helpers.sh
# Shell helpers for dev-pipeline.
#
# Design invariants:
# 1) Claude headless review sessions always start from MONOREPO_ROOT so .claude/skills resolve.
# 2) gh commands always use explicit repo (-R owner/name), never implicit cwd.
# 3) Feature-branch git operations always run in the issue worktree.
# 4) Merge runs through a single helper that acquires and releases the lock in one shell process.
# 5) All transient artifacts are area-scoped to avoid client/server collisions.
# 6) Resolve runs directly in the pipeline session, not as a headless sub-agent.

_PIPELINE_HELPERS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
_PIPELINE_SEARCH_DIR="$_PIPELINE_HELPERS_DIR"
while [ "$_PIPELINE_SEARCH_DIR" != "/" ] && [ ! -f "$_PIPELINE_SEARCH_DIR/.agents/scripts/monorepo-helpers.sh" ]; do
  _PIPELINE_SEARCH_DIR="$(dirname -- "$_PIPELINE_SEARCH_DIR")"
done
if [ ! -f "$_PIPELINE_SEARCH_DIR/.agents/scripts/monorepo-helpers.sh" ]; then
  printf '%s\n' '[pipeline] failed to locate .agents/scripts/monorepo-helpers.sh' >&2
  return 1 2>/dev/null || exit 1
fi
# shellcheck disable=SC1090
source "$_PIPELINE_SEARCH_DIR/.agents/scripts/monorepo-helpers.sh"

PIPELINE_DIR="$MONOREPO_ROOT/.workspace/pipeline"
PIPELINE_LOG_DIR="$PIPELINE_DIR/logs"
PIPELINE_MESSAGE_DIR="$MONOREPO_ROOT/.workspace/messages"
WORKTREE_DIR="$MONOREPO_ROOT/.workspace/worktrees"

pipeline_skill_cwd() {
  printf '%s\n' "$MONOREPO_ROOT"
}

pipeline_repo_dir() {
  monorepo_area_dir "$1"
}

pipeline_repo_name() {
  monorepo_area_repo "$1"
}

pipeline_state_dir() {
  local area=$1
  printf '%s\n' "$PIPELINE_DIR/$area"
}

pipeline_log_dir() {
  local area=$1
  printf '%s\n' "$PIPELINE_LOG_DIR/$area"
}

pipeline_state_path() {
  local issue=$1
  local area=$2
  printf '%s\n' "$(pipeline_state_dir "$area")/issue-${issue}.state.json"
}

pipeline_log_path() {
  local issue=$1
  local area=$2
  local stage=$3
  printf '%s\n' "$(pipeline_log_dir "$area")/issue-${issue}-${stage}.log"
}

pipeline_err_path() {
  local issue=$1
  local area=$2
  local stage=$3
  printf '%s\n' "$(pipeline_log_dir "$area")/issue-${issue}-${stage}.err"
}

pipeline_headless_meta_path() {
  local issue=$1
  local area=$2
  local stage=$3
  printf '%s\n' "$(pipeline_state_dir "$area")/issue-${issue}-${stage}.job.json"
}

pipeline_message_path() {
  local area=$1
  local pr=$2
  local kind=$3
  printf '%s\n' "$PIPELINE_MESSAGE_DIR/${area}-pr-${pr}-${kind}.md"
}

pipeline_worktree_path() {
  local issue=$1
  local area=$2
  printf '%s\n' "$WORKTREE_DIR/$area/issue-${issue}"
}

pipeline_resolve_worktree_path() {
  # Canonical path:   .workspace/worktrees/<area>/issue-<N>
  # Legacy path #1:   .workspace/worktrees/issue-<N>
  # Legacy path #2:   <area>/.workspace/worktrees/issue-<N>
  local issue=$1
  local area=$2
  local canonical legacy_root legacy_area

  canonical="$(pipeline_worktree_path "$issue" "$area")"
  legacy_root="$WORKTREE_DIR/issue-${issue}"
  legacy_area="$MONOREPO_ROOT/$area/.workspace/worktrees/issue-${issue}"

  if [ -d "$canonical" ]; then
    printf '%s\n' "$canonical"
    return 0
  fi
  if [ -d "$legacy_root" ]; then
    printf '%s\n' "$legacy_root"
    return 0
  fi
  if [ -d "$legacy_area" ]; then
    printf '%s\n' "$legacy_area"
    return 0
  fi

  printf '%s\n' 'PATH_INVALID'
  return 3
}

pipeline_init() {
  local area=$1
  mkdir -p \
    "$(pipeline_state_dir "$area")" \
    "$(pipeline_log_dir "$area")" \
    "$PIPELINE_MESSAGE_DIR" \
    "$WORKTREE_DIR/$area"
}

pipeline_state_exists() {
  local issue=$1
  local area=$2
  [ -f "$(pipeline_state_path "$issue" "$area")" ]
}

pipeline_state_read() {
  local issue=$1
  local area=$2
  cat "$(pipeline_state_path "$issue" "$area")"
}

pipeline_state_write() {
  # Atomic write to prevent half-written JSON on crash.
  local issue=$1
  local area=$2
  local json=$3
  local path tmp

  path="$(pipeline_state_path "$issue" "$area")"
  mkdir -p "$(dirname -- "$path")" || return 1
  tmp="$(mktemp "${path}.tmp.XXXXXX")" || return 1
  printf '%s\n' "$json" > "$tmp" && mv "$tmp" "$path" || {
    rm -f "$tmp"
    return 1
  }
}

pipeline_state_update() {
  # Usage:
  #   pipeline_state_update <issue> <area> <jq_expr> [jq args...]
  # Example:
  #   pipeline_state_update 42 client '.step = "review"'
  #   pipeline_state_update 42 client '.recoveryLog = ((.recoveryLog // []) + [$entry])' --argjson entry "$json"
  local issue=$1
  local area=$2
  local jq_expr=$3
  shift 3

  local current updated
  current="$(pipeline_state_read "$issue" "$area")" || return 1

  if ! updated="$(printf '%s' "$current" | jq "$@" "$jq_expr | .updatedAt = (now | todate)")"; then
    printf '[pipeline] jq failed for expression: %s\n' "$jq_expr" >&2
    return 1
  fi

  if [ -z "$updated" ] || [ "$updated" = 'null' ]; then
    printf '[pipeline] jq produced empty/null output for: %s\n' "$jq_expr" >&2
    return 1
  fi

  pipeline_state_write "$issue" "$area" "$updated"
}

pipeline_state_delete() {
  local issue=$1
  local area=$2
  rm -f "$(pipeline_state_path "$issue" "$area")"
}

pipeline_review_prompt() {
  local issue=$1
  local area=$2
  local pr=$3
  local repo repo_dir

  repo="$(pipeline_repo_name "$area")" || return 1
  repo_dir="$(pipeline_repo_dir "$area")" || return 1

  cat <<PROMPT_REVIEW
/dev-review
Target issue: #$issue
Target PR: #$pr
Target area: $area
GitHub repo: $repo
Repo dir on disk: $repo_dir
Session skill root: $MONOREPO_ROOT

Rules:
- Skills must resolve from $MONOREPO_ROOT. Do not change that assumption.
- For GitHub commands, use either "gh ... -R $repo" or work from "$repo_dir" explicitly.
- Do not assume the process cwd is the repo checkout.
- Review only the PR diff and directly necessary context.
- After posting the review, exit immediately.
PROMPT_REVIEW
}

pipeline_fetch_review_comments() {
  # Fetch inline review comments for a specific review.
  # Returns JSON array of {path, line, side, body} objects.
  # Returns: 0 = success (JSON on stdout), 1 = error
  # Usage: pipeline_fetch_review_comments <area> <pr> <review_id>
  local area=$1
  local pr=$2
  local review_id=$3
  local repo _gh_err

  repo="$(pipeline_repo_name "$area")" || return 1
  _gh_err="$(mktemp)"
  (
    set -o pipefail
    gh api "repos/${repo}/pulls/${pr}/reviews/${review_id}/comments" --paginate 2>"$_gh_err" \
      | jq -s '[add // [] | .[] | {path: .path, line: (.original_line // .line), side: .side, body: .body}]'
  ) || {
    printf '[pipeline] gh api error fetching review comments for PR #%s review %s in %s: %s\n' \
      "$pr" "$review_id" "$repo" "$(cat "$_gh_err")" >&2
    rm -f "$_gh_err"
    return 1
  }
  rm -f "$_gh_err"
}

pipeline_run_headless_core() {
  # Synchronous low-level runner for headless review.
  # IMPORTANT: In Claude Code skills, the outer Bash tool call for this function
  # should use run_in_background: true for long-running review steps.
  #
  # Usage:
  #   pipeline_run_headless_core <skill_cwd> <prompt> <issue> <area> <stage> <repo_dir> <worktree_dir> <pr> [model]
  local skill_cwd=$1
  local prompt=$2
  local issue=$3
  local area=$4
  local stage=$5
  local repo_dir=$6
  local worktree_dir=$7
  local pr=$8
  local model=${9:-}

  local log err meta repo tools max_turns timeout_sec cmd rc status meta_tmp

  pipeline_init "$area" || return 1

  log="$(pipeline_log_path "$issue" "$area" "$stage")"
  err="$(pipeline_err_path "$issue" "$area" "$stage")"
  meta="$(pipeline_headless_meta_path "$issue" "$area" "$stage")"
  repo="$(pipeline_repo_name "$area")" || return 1

  case "$stage" in
    review)
      tools='Bash,Read,Skill'
      max_turns=15
      timeout_sec=900
      ;;
    *)
      printf "[pipeline] unknown headless stage: %s\n" "$stage" >&2
      return 2
      ;;
  esac

  meta_tmp="${meta}.tmp"
  jq -n \
    --arg status 'running' \
    --arg issue "$issue" \
    --arg area "$area" \
    --arg stage "$stage" \
    --arg pr "$pr" \
    --arg repo "$repo" \
    --arg repoDir "$repo_dir" \
    --arg worktreeDir "$worktree_dir" \
    --arg skillCwd "$skill_cwd" \
    --arg log "$log" \
    --arg err "$err" \
    --arg model "$model" \
    '{
      status: $status,
      issue: ($issue | tonumber),
      area: $area,
      stage: $stage,
      pr: ($pr | tonumber),
      repo: $repo,
      repoDir: $repoDir,
      worktreeDir: $worktreeDir,
      skillCwd: $skillCwd,
      log: $log,
      err: $err,
      model: $model,
      startedAt: (now | todate),
      finishedAt: null,
      exitCode: null
    }' > "$meta_tmp" && mv "$meta_tmp" "$meta"

  cmd=(timeout "$timeout_sec" claude -p)
  if [ -n "$model" ]; then
    cmd+=(--model "$model")
  fi
  cmd+=(
    --dangerously-skip-permissions
    --no-session-persistence
    --allowedTools "$tools"
    --max-turns "$max_turns"
    "$prompt"
  )

  (
    cd -- "$skill_cwd" || exit 3
    unset CLAUDECODE
    PIPELINE_MONOREPO_ROOT="$MONOREPO_ROOT" \
    PIPELINE_AREA="$area" \
    PIPELINE_REPO="$repo" \
    PIPELINE_REPO_DIR="$repo_dir" \
    PIPELINE_WORKTREE_DIR="$worktree_dir" \
    PIPELINE_STAGE="$stage" \
    PIPELINE_ISSUE="$issue" \
    PIPELINE_PR="$pr" \
    "${cmd[@]}" > "$log" 2> "$err"
  )
  rc=$?

  case "$rc" in
    0) status='success' ;;
    124) status='timeout' ;;
    *) status='error' ;;
  esac

  if [ -f "$meta" ]; then
    jq \
      --arg status "$status" \
      --argjson exitCode "$rc" \
      '.status = $status | .exitCode = $exitCode | .finishedAt = (now | todate)' \
      "$meta" > "$meta_tmp" && mv "$meta_tmp" "$meta" || \
      printf '[pipeline] meta update failed for issue=%s area=%s stage=%s\n' "$issue" "$area" "$stage" >&2
  else
    jq -n \
      --arg status "$status" \
      --argjson exitCode "$rc" \
      --arg issue "$issue" \
      --arg area "$area" \
      --arg stage "$stage" \
      --arg pr "$pr" \
      '{status: $status, exitCode: $exitCode, finishedAt: (now | todate),
        issue: ($issue | tonumber), area: $area, stage: $stage,
        pr: ($pr | tonumber)}' \
      > "$meta_tmp" && mv "$meta_tmp" "$meta"
  fi

  printf '%s\n' "$log"
  return "$rc"
}

pipeline_run_review() {
  local issue=$1
  local area=$2
  local pr=$3
  local model=${4:-}
  local repo_dir prompt

  repo_dir="$(pipeline_repo_dir "$area")" || return 1
  prompt="$(pipeline_review_prompt "$issue" "$area" "$pr")" || return 1
  pipeline_run_headless_core \
    "$(pipeline_skill_cwd)" \
    "$prompt" \
    "$issue" "$area" review \
    "$repo_dir" '' "$pr" "$model"
}

pipeline_check_review_exists() {
  # Returns: 0 = found (review_id on stdout), 1 = not found, 2 = gh error
  local area=$1
  local pr=$2
  local last_review_id=${3:-0}
  local repo review_id _gh_err

  repo="$(pipeline_repo_name "$area")" || return 1
  _gh_err="$(mktemp)"
  review_id="$(
    set -o pipefail
    gh api "repos/${repo}/pulls/${pr}/reviews" --paginate 2>"$_gh_err" \
      | jq -s -r --argjson lastId "${last_review_id:-0}" \
        '[add // [] | .[] | select(.id > $lastId) | select(.body | startswith("## Review Summary"))] | last | .id // empty'
  )" || {
    printf '[pipeline] gh api error checking reviews for PR #%s in %s: %s\n' "$pr" "$repo" "$(cat "$_gh_err")" >&2
    rm -f "$_gh_err"
    return 2
  }
  rm -f "$_gh_err"

  if [ -n "$review_id" ] && [ "$review_id" != 'null' ]; then
    printf '%s\n' "$review_id"
    return 0
  fi
  return 1
}

pipeline_fetch_review() {
  # Returns: 0 = success (JSON on stdout), 1 = error
  local area=$1
  local pr=$2
  local review_id=$3
  local repo _gh_err

  repo="$(pipeline_repo_name "$area")" || return 1
  _gh_err="$(mktemp)"
  gh api "repos/${repo}/pulls/${pr}/reviews/${review_id}" \
    --jq '{state: .state, body: .body}' 2>"$_gh_err" || {
    printf '[pipeline] gh api error fetching review %s for PR #%s in %s: %s\n' \
      "$review_id" "$pr" "$repo" "$(cat "$_gh_err")" >&2
    rm -f "$_gh_err"
    return 1
  }
  rm -f "$_gh_err"
}

pipeline_check_new_commits() {
  # Returns: 0 = found (new_sha on stdout), 1 = not found, 2 = gh error
  local area=$1
  local pr=$2
  local last_commit_sha=$3
  local repo latest_sha _gh_err

  repo="$(pipeline_repo_name "$area")" || return 1
  _gh_err="$(mktemp)"
  latest_sha="$(gh pr view "$pr" -R "$repo" --json headRefOid --jq '.headRefOid' 2>"$_gh_err")" || {
    printf '[pipeline] gh error checking head SHA for PR #%s in %s: %s\n' "$pr" "$repo" "$(cat "$_gh_err")" >&2
    rm -f "$_gh_err"
    return 2
  }
  rm -f "$_gh_err"

  if [ -n "$latest_sha" ] && [ "$latest_sha" != 'null' ] && [ "$latest_sha" != "$last_commit_sha" ]; then
    printf '%s\n' "$latest_sha"
    return 0
  fi
  return 1
}

pipeline_stage_retry() {
  # Increment stage retry counter, check against max.
  # Returns: 0 = can retry, 1 = max reached
  local issue=$1
  local area=$2
  local stage=$3
  local state retries max

  state="$(pipeline_state_read "$issue" "$area")" || return 1
  retries="$(printf '%s' "$state" | jq -r --arg s "$stage" '.stageRetries[$s] // 0')"
  max="$(printf '%s' "$state" | jq -r '.maxStageRetries // 3')"

  if [ "$retries" -ge "$max" ]; then
    return 1
  fi

  pipeline_state_update "$issue" "$area" '.stageRetries[$s] = $n' --arg s "$stage" --argjson n "$((retries + 1))"
}

pipeline_recovery_log() {
  # Append a recovery attempt to recoveryLog.
  local issue=$1
  local area=$2
  local stage=$3
  local error=$4
  local action=$5
  local result=$6
  local entry

  entry="$(jq -n \
    --arg s "$stage" \
    --arg e "$error" \
    --arg a "$action" \
    --arg r "$result" \
    '{stage:$s, error:$e, action:$a, result:$r, timestamp:(now|todate)}')" || return 1

  pipeline_state_update \
    "$issue" "$area" \
    '.recoveryLog = ((.recoveryLog // []) + [$entry])' \
    --argjson entry "$entry"
}

pipeline_format_escalation() {
  local issue=$1
  local area=$2
  local stage=$3
  local state

  state="$(pipeline_state_read "$issue" "$area")" || return 1
  printf '%s\n' "$state" | jq -r --arg stage "$stage" '
    [
      "[pipeline] Stage \($stage) failed after \(.maxStageRetries // 3) recovery attempts.",
      "Recovery log:",
      ((.recoveryLog // [])
        | map(select(.stage == $stage) | "  [\(.timestamp)] \(.error) -> \(.action) -> \(.result)")
        | .[]?),
      "",
      "Worktree: \(.paths.worktreeDir // "")",
      "Branch: \(.branch // "")",
      "PR: #\(.pr // 0)",
      "",
      "Action needed: fix manually, then resume with /dev-pipeline"
    ] | .[]'
}

pipeline_acquire_merge_lock() {
  # Area-level merge lock safe across separate shell invocations.
  # Stale lock policy is TTL-based, not PID-based.
  # Usage: pipeline_acquire_merge_lock <area> <issue> [max_wait_seconds] [stale_after_seconds]
  local area=$1
  local issue=$2
  local max_wait=${3:-300}
  local stale_after=${4:-1800}
  local interval=10
  local waited=0
  local lock_dir holder_issue acquired_ts acquired_epoch now_epoch

  lock_dir="$(pipeline_state_dir "$area")/merge.lock"
  mkdir -p "$(pipeline_state_dir "$area")" || return 1

  while ! mkdir "$lock_dir" 2>/dev/null; do
    holder_issue="$(cat "$lock_dir/issue" 2>/dev/null || true)"
    acquired_ts="$(cat "$lock_dir/acquired" 2>/dev/null || true)"
    acquired_epoch="$(date -u -d "$acquired_ts" +%s 2>/dev/null || printf '0')"
    now_epoch="$(date -u +%s)"

    if [ "$acquired_epoch" -gt 0 ] && [ $((now_epoch - acquired_epoch)) -ge "$stale_after" ]; then
      printf '[pipeline] stale merge lock detected for area=%s issue=%s; reclaiming\n' "$area" "${holder_issue:-unknown}" >&2
      rm -rf "$lock_dir"
      continue
    fi

    if [ "$waited" -ge "$max_wait" ]; then
      printf '[pipeline] merge lock timeout after %ss (held by issue #%s)\n' "$max_wait" "${holder_issue:-unknown}" >&2
      return 1
    fi

    printf '[pipeline] merge lock held for area=%s by issue #%s; waiting (%ss/%ss)\n' "$area" "${holder_issue:-unknown}" "$waited" "$max_wait" >&2
    sleep "$interval"
    waited=$((waited + interval))
  done

  printf '%s\n' "$issue" > "$lock_dir/issue"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$lock_dir/acquired"
  return 0
}

pipeline_release_merge_lock() {
  # Usage: pipeline_release_merge_lock <area> [expected_issue]
  local area=$1
  local expected_issue=${2:-}
  local lock_dir holder_issue

  lock_dir="$(pipeline_state_dir "$area")/merge.lock"
  [ -d "$lock_dir" ] || return 0

  if [ -n "$expected_issue" ]; then
    holder_issue="$(cat "$lock_dir/issue" 2>/dev/null || true)"
    if [ -n "$holder_issue" ] && [ "$holder_issue" != "$expected_issue" ]; then
      printf '[pipeline] refusing to release merge lock for area=%s; expected issue #%s but lock belongs to #%s\n' "$area" "$expected_issue" "$holder_issue" >&2
      return 1
    fi
  fi

  rm -rf "$lock_dir"
}

pipeline_push_branch_safely() {
  # Push normally when fast-forward; otherwise use --force-with-lease.
  local worktree_dir=$1

  if ! git -C "$worktree_dir" rev-parse --verify '@{upstream}' >/dev/null 2>&1; then
    git -C "$worktree_dir" push -u origin HEAD
    return $?
  fi

  if git -C "$worktree_dir" merge-base --is-ancestor '@{upstream}' HEAD >/dev/null 2>&1; then
    git -C "$worktree_dir" push
  else
    git -C "$worktree_dir" push --force-with-lease
  fi
}

pipeline_merge_pr() {
  # Acquire lock, sync feature branch from the issue worktree, then merge via gh.
  # Runs lock acquire + merge + release in one shell process.
  # Usage: pipeline_merge_pr <issue> <area> <pr> <branch>
  local issue=$1
  local area=$2
  local pr=$3
  local branch=$4  # unused inside this function; passed by callers for context
  local repo repo_dir worktree_dir pr_state

  repo="$(pipeline_repo_name "$area")" || return 1
  repo_dir="$(pipeline_repo_dir "$area")" || return 1
  worktree_dir="$(pipeline_resolve_worktree_path "$issue" "$area" 2>/dev/null || true)"

  pipeline_acquire_merge_lock "$area" "$issue" || return 1
  # Guard the short window between lock acquisition and subshell start.
  trap 'pipeline_release_merge_lock "$area" "$issue" >/dev/null 2>&1 || true' INT TERM

  local merge_rc
  (
    trap 'pipeline_release_merge_lock "$area" "$issue" >/dev/null 2>&1 || true' EXIT INT TERM

    if [ -n "$worktree_dir" ] && [ "$worktree_dir" != 'PATH_INVALID' ] && [ -d "$worktree_dir" ]; then
      git -C "$worktree_dir" fetch origin || exit 1

      if git -C "$worktree_dir" rebase origin/main; then
        pipeline_push_branch_safely "$worktree_dir" || exit 1
      else
        git -C "$worktree_dir" rebase --abort >/dev/null 2>&1 || true
        git -C "$worktree_dir" merge --no-edit origin/main || exit 1
        pipeline_push_branch_safely "$worktree_dir" || exit 1
      fi
    else
      printf '[pipeline] worktree missing for issue #%s area=%s; skipping branch sync and attempting merge directly\n' "$issue" "$area" >&2
    fi

    (
      cd -- "$repo_dir" || exit 1
      gh pr merge "$pr" -R "$repo" --squash --delete-branch
    ) || exit 1

    pr_state="$(gh pr view "$pr" -R "$repo" --json state --jq '.state')" || exit 1
    [ "$pr_state" = 'MERGED' ] || {
      printf '[pipeline] gh pr merge returned without MERGED state for PR #%s in %s\n' "$pr" "$repo" >&2
      exit 1
    }

    pipeline_release_merge_lock "$area" "$issue"
    trap - EXIT INT TERM
  )
  merge_rc=$?
  trap - INT TERM
  return "$merge_rc"
}

pipeline_cleanup() {
  local issue=$1
  local area=$2
  local branch=$3
  local pr=${4:-}
  local repo_dir wt

  repo_dir="$(pipeline_repo_dir "$area")" || return 1
  wt="$(pipeline_resolve_worktree_path "$issue" "$area" 2>/dev/null || true)"

  rm -f \
    "$(pipeline_log_path "$issue" "$area" review)" \
    "$(pipeline_err_path "$issue" "$area" review)" \
    "$(pipeline_headless_meta_path "$issue" "$area" review)"

  # Clean up stale message files from resolve step.
  if [ -n "$pr" ]; then
    rm -f "$(pipeline_message_path "$area" "$pr" response)"
  fi

  if [ -n "$wt" ] && [ "$wt" != 'PATH_INVALID' ] && [ -d "$wt" ]; then
    git -C "$repo_dir" worktree remove "$wt" --force || true
    git -C "$repo_dir" worktree prune || true
  fi

  git -C "$repo_dir" branch -D "$branch" 2>/dev/null || true
  pipeline_state_delete "$issue" "$area"
}

pipeline_list() {
  local found=0
  local f info

  if [ ! -d "$PIPELINE_DIR" ]; then
    printf '%s\n' 'No active pipelines'
    return 0
  fi

  for f in "$PIPELINE_DIR"/*/issue-*.state.json; do
    [ -f "$f" ] || continue
    found=1
    info="$(jq -r '"Issue #\(.issue) (\(.area)): step=\(.step) pr=#\(.pr // 0)"' "$f")"
    printf '%s\n' "$info"
  done

  [ "$found" -eq 0 ] && printf '%s\n' 'No active pipelines'
}
