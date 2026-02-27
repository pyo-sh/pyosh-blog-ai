FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 기본 도구
RUN apt-get update && apt-get install -y \
    curl git gh tmux zsh ca-certificates gnupg sudo \
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

# entrypoint 스크립트
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
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
WORKDIR /workspace

ENTRYPOINT ["entrypoint.sh"]
