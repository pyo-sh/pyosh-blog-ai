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

# Claude Code status line 설정
claude_settings="/home/dev/.claude/settings.json"
if [ ! -f "$claude_settings" ]; then
  mkdir -p /home/dev/.claude
  cat > "$claude_settings" << 'SETTINGS'
{
  "statusLine": {
    "type": "command",
    "command": "/workspace/scripts/context-bar.sh"
  }
}
SETTINGS
elif ! jq -e '.statusLine' "$claude_settings" > /dev/null 2>&1; then
  jq '. + {"statusLine": {"type": "command", "command": "/workspace/scripts/context-bar.sh"}}' \
    "$claude_settings" > "${claude_settings}.tmp" && mv "${claude_settings}.tmp" "$claude_settings"
fi

# .bash_aliases 로드 (dev-update 함수 사용)
[ -f /home/dev/.bash_aliases ] && . /home/dev/.bash_aliases

# 도구 업데이트
dev-update

# 기존 명령 실행 (TPM 설치 → tmuxinator → tail)
exec "$@"
