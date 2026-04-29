FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 기본 도구
RUN apt-get update && apt-get install -y \
    curl git gh tmux zsh ca-certificates gnupg sudo \
    python3 python3-pip vim jq \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Locale 설정 (TUI 앱 UTF-8 필수)
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# tmuxinator
RUN apt-get update && apt-get install -y ruby && gem install tmuxinator \
    && rm -rf /var/lib/apt/lists/*

# Codex CLI
RUN npm install -g @openai/codex

# Chromium for Playwright-based browser automation (ARM64 native)
# Ubuntu 24.04에서 chromium-browser는 snap wrapper이므로 Playwright 전용 Chromium 사용.
# PLAYWRIGHT_BROWSERS_PATH를 /opt/ms-playwright로 고정하여 빌드·런타임 모두 동일 경로 참조.
# chrome 채널 shim(/opt/google/chrome/chrome): Playwright 기본 설정(chrome channel)이
# 해당 경로를 탐색하므로 추가 설정 없이 연결.
# --no-sandbox: Docker 컨테이너는 user namespace가 없어 sandbox 없이 실행 필요.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
RUN npm install -g playwright \
    && playwright install --with-deps chromium \
    && CHROME=$(find /opt/ms-playwright -name chrome -type f | head -1) \
    && mkdir -p /opt/google/chrome \
    && printf '#!/bin/sh\nexec "%s" --no-sandbox "$@"\n' "$CHROME" \
       > /opt/google/chrome/chrome \
    && chmod +x /opt/google/chrome/chrome \
    && chmod -R a+rx /opt/ms-playwright

# entrypoint 스크립트
COPY tools/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# non-root 사용자 생성
RUN useradd -m -s /bin/bash -G sudo dev \
    && echo 'dev ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# .bash_aliases 자동 로드
RUN echo '[ -f /home/dev/.bash_aliases ] && . /home/dev/.bash_aliases' >> /home/dev/.bashrc

# TPM (Tmux Plugin Manager)
RUN git clone https://github.com/tmux-plugins/tpm /home/dev/.tmux/plugins/tpm \
    && chown -R dev:dev /home/dev/.tmux

USER dev

# Claude Code CLI (native installer — ~/.local/bin/claude)
# 설치 후 생성된 ~/.claude 제거 (entrypoint.sh에서 auth volume 심링크로 교체)
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && rm -rf /home/dev/.claude /home/dev/.claude.json
ENV PATH="/home/dev/.local/bin:$PATH"

WORKDIR /workspace

ENTRYPOINT ["entrypoint.sh"]
