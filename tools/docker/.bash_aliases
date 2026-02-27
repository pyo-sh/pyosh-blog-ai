# Disable Ctrl+s terminal freeze (XOFF flow control)
stty -ixon 2>/dev/null

# Docker dev-lab aliases

alias cc="claude --dangerously-skip-permissions"
alias ccc="claude --continue --dangerously-skip-permissions"
alias cr="claude --resume --dangerously-skip-permissions"
alias ch="claude --chrome --dangerously-skip-permissions"

alias cdx="codex --dangerously-bypass-approvals-and-sandbox"

# 전체 업데이트 함수
dev-update() {
  echo "=== Updating dev tools ==="

  # System packages
  sudo apt-get update && sudo apt-get upgrade -y && sudo rm -rf /var/lib/apt/lists/*

  # Claude Code CLI & Codex CLI
  sudo npm update -g @anthropic-ai/claude-code @openai/codex

  # pnpm (corepack)
  sudo corepack prepare pnpm@latest --activate

  # 명령어 경로 캐시 초기화
  hash -r

  echo "=== Update complete ==="
}

# 기존 tmux pane에서 환경 재로드
dev-refresh() {
  hash -r
  source ~/.bashrc
  echo "=== Shell refreshed ==="
}