FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 기본 도구
RUN apt-get update && apt-get install -y \
    curl git gh tmux zsh ca-certificates gnupg \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# tmuxinator
RUN apt-get update && apt-get install -y ruby && gem install tmuxinator \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# .bash_aliases 자동 로드
RUN echo '[ -f /root/.bash_aliases ] && . /root/.bash_aliases' >> /root/.bashrc

# TPM (Tmux Plugin Manager)
RUN git clone https://github.com/tmux-plugins/tpm /root/.tmux/plugins/tpm

WORKDIR /workspace
