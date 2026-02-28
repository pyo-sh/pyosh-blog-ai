#!/bin/bash
set -e

# 타임존 설정 (우선순위: TZ 환경변수 → /etc/localtime 마운트 → 기본값)
DEFAULT_TZ="Asia/Seoul"
if [ -n "$TZ" ]; then
  sudo ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime
  echo "$TZ" | sudo tee /etc/timezone > /dev/null
elif [ ! -f /etc/localtime ]; then
  sudo ln -snf "/usr/share/zoneinfo/$DEFAULT_TZ" /etc/localtime
  echo "$DEFAULT_TZ" | sudo tee /etc/timezone > /dev/null
  export TZ="$DEFAULT_TZ"
fi

# ── 인증 volume 심볼릭 링크 ──
# /home/dev/.auth (named volume) → 각 도구의 표준 경로로 연결
# named volume은 root 소유로 마운트되므로 최초 1회 소유권 변경
AUTH="/home/dev/.auth"
sudo chown dev:dev "$AUTH"
mkdir -p "$AUTH/gh" "$AUTH/claude" "$AUTH/codex" "$AUTH/ssh"

# gh CLI: ~/.config/gh
mkdir -p /home/dev/.config
ln -sfn "$AUTH/gh" /home/dev/.config/gh

# Claude Code: ~/.claude (설정+인증), ~/.claude.json (온보딩/계정)
# native installer가 실제 디렉터리를 생성했을 경우 제거 (ln -sfn은 실제 디렉터리를 교체 못함)
[ -d /home/dev/.claude ] && [ ! -L /home/dev/.claude ] && rm -rf /home/dev/.claude
ln -sfn "$AUTH/claude" /home/dev/.claude
[ -f "$AUTH/claude.json" ] || echo '{}' > "$AUTH/claude.json"
[ -f /home/dev/.claude.json ] && [ ! -L /home/dev/.claude.json ] && rm -f /home/dev/.claude.json
ln -sfn "$AUTH/claude.json" /home/dev/.claude.json

# Codex: ~/.codex
ln -sfn "$AUTH/codex" /home/dev/.codex

# Git: ~/.gitconfig
[ -f "$AUTH/gitconfig" ] || touch "$AUTH/gitconfig"
ln -sfn "$AUTH/gitconfig" /home/dev/.gitconfig

# SSH: ~/.ssh
ln -sfn "$AUTH/ssh" /home/dev/.ssh

# Claude Code status line 설정
# /workspace/scripts/context-bar.sh 를 직접 참조 (스크립트 복사 불필요, 항상 최신 유지)
STATUSLINE_CMD="/workspace/scripts/context-bar.sh"
claude_settings="$AUTH/claude/settings.json"
if [ ! -f "$claude_settings" ]; then
  cat > "$claude_settings" << SETTINGS
{
  "statusLine": {
    "type": "command",
    "command": "$STATUSLINE_CMD"
  }
}
SETTINGS
elif ! jq -e '.statusLine' "$claude_settings" > /dev/null 2>&1; then
  # statusLine 없음 → 추가
  jq --arg cmd "$STATUSLINE_CMD" \
    '. + {"statusLine": {"type": "command", "command": $cmd}}' \
    "$claude_settings" > "${claude_settings}.tmp" && mv "${claude_settings}.tmp" "$claude_settings"
elif [ "$(jq -r '.statusLine.command' "$claude_settings")" != "$STATUSLINE_CMD" ]; then
  # statusLine 있지만 다른 경로 → workspace 경로로 교정 (stale path 방지)
  jq --arg cmd "$STATUSLINE_CMD" \
    '.statusLine.command = $cmd' \
    "$claude_settings" > "${claude_settings}.tmp" && mv "${claude_settings}.tmp" "$claude_settings"
fi

# ── 설정 파일 심링크 (/workspace 디렉토리 마운트 경유) ──
# 단일 파일 bind mount는 에디터가 inode를 교체하면 깨지므로
# /workspace (디렉토리 마운트)를 경유하는 심링크로 연결
ln -sfn /workspace/tools/tmux/docker.tmux.conf /home/dev/.tmux.conf
ln -sfn /workspace/tools/docker/.bash_aliases /home/dev/.bash_aliases

# .bash_aliases 로드 (dev-update 함수 사용)
[ -f /home/dev/.bash_aliases ] && . /home/dev/.bash_aliases

# 도구 업데이트
dev-update

# 기존 명령 실행 (TPM 설치 → tmuxinator → tail)
exec "$@"
