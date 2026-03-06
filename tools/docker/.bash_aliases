# Disable Ctrl+s terminal freeze (XOFF flow control)
stty -ixon 2>/dev/null

# Docker dev-lab aliases

alias cc="claude --dangerously-skip-permissions"
alias ccc="claude --continue --dangerously-skip-permissions"
alias cr="claude --resume --dangerously-skip-permissions"
alias ch="claude --chrome --dangerously-skip-permissions"

alias cdx="codex --dangerously-bypass-approvals-and-sandbox"

# 전체 업데이트 함수 (각 단계 독립 실행 - 하나 실패해도 나머지 계속)
dev-update() {
  echo "=== Updating dev tools ==="
  local failed=0

  # System packages (손상된 apt lists 정리 후 업데이트)
  echo "[1/4] System packages"
  sudo rm -rf /var/lib/apt/lists/*
  if sudo apt-get update && sudo apt-get upgrade -y; then
    sudo rm -rf /var/lib/apt/lists/*
    echo "  done"
  else
    echo "  SKIPPED (apt-get failed)"
    sudo rm -rf /var/lib/apt/lists/*
    ((failed++)) || true
  fi

  # Claude Code CLI (native installer)
  echo "[2/4] Claude Code CLI"
  if curl -fsSL https://claude.ai/install.sh | bash; then
    echo "  done"
  else
    echo "  SKIPPED (install failed)"
    ((failed++)) || true
  fi

  # Codex CLI
  echo "[3/4] Codex CLI"
  if sudo npm update -g @openai/codex; then
    echo "  done"
  else
    echo "  SKIPPED (npm update failed)"
    ((failed++)) || true
  fi

  # pnpm (corepack)
  echo "[4/4] pnpm"
  if sudo corepack prepare pnpm@latest --activate; then
    echo "  done"
  else
    echo "  SKIPPED (corepack failed)"
    ((failed++)) || true
  fi

  # 명령어 경로 캐시 초기화
  hash -r

  if [ "$failed" -gt 0 ]; then
    echo "=== Update complete ($failed step(s) skipped) ==="
  else
    echo "=== Update complete ==="
  fi
}

# 기존 tmux pane에서 환경 재로드
dev-refresh() {
  hash -r
  source ~/.bashrc
  echo "=== Shell refreshed ==="
}

# 인증 초기 설정 (컨테이너 최초 1회)
dev-auth-setup() {
  echo "=== Auth Setup (dev-lab-auth volume) ==="
  echo ""

  # 1. Git
  echo "[1/4] Git config"
  if git config --global user.name > /dev/null 2>&1; then
    echo "  ✓ user.name: $(git config --global user.name)"
  else
    read -rp "  user.name: " name && git config --global user.name "$name"
  fi
  if git config --global user.email > /dev/null 2>&1; then
    echo "  ✓ user.email: $(git config --global user.email)"
  else
    read -rp "  user.email: " email && git config --global user.email "$email"
  fi
  echo ""

  # 2. GitHub CLI
  echo "[2/4] GitHub CLI"
  if gh auth status > /dev/null 2>&1; then
    echo "  ✓ $(gh auth status 2>&1 | head -1)"
  else
    gh auth login --git-protocol https --insecure-storage
    gh auth setup-git
  fi
  echo ""

  # 3. Claude Code
  echo "[3/4] Claude Code"
  if [ -f ~/.claude/.credentials.json ] && jq -e '.claudeAiOauth.refreshToken' ~/.claude/.credentials.json > /dev/null 2>&1; then
    echo "  ✓ logged in"
  else
    echo "  Run: claude  (follow login prompts)"
  fi
  echo ""

  # 4. Codex
  echo "[4/4] Codex"
  if [ -f ~/.codex/auth.json ] && [ -s ~/.codex/auth.json ]; then
    echo "  ✓ logged in"
  else
    echo "  Run: codex  (follow login prompts)"
  fi
  echo ""
  echo "=== Done ==="
}

# 인증 상태 확인
dev-auth-status() {
  echo "=== Auth Status (dev-lab-auth volume) ==="
  echo ""
  echo "Git:"
  echo "  user.name:  $(git config --global user.name 2>/dev/null || echo '✗ not set')"
  echo "  user.email: $(git config --global user.email 2>/dev/null || echo '✗ not set')"
  echo ""
  echo "GitHub CLI:"
  gh auth status 2>&1 | sed 's/^/  /' || echo "  ✗ not logged in"
  echo ""
  echo "Claude Code:"
  if [ -f ~/.claude/.credentials.json ] && jq -e '.claudeAiOauth.refreshToken' ~/.claude/.credentials.json > /dev/null 2>&1; then
    echo "  ✓ logged in"
  else
    echo "  ✗ not logged in"
  fi
  echo ""
  echo "Codex:"
  if [ -f ~/.codex/auth.json ] && [ -s ~/.codex/auth.json ]; then
    echo "  ✓ logged in"
  else
    echo "  ✗ not logged in"
  fi
}

