# tmux 환경 설정

이 프로젝트에서 사용하는 tmux 세션 구성을 재현하기 위한 가이드입니다.

## 1. 설치

### macOS

```bash
brew install tmux
gem install tmuxinator
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y tmux
gem install tmuxinator
```

### Arch Linux

```bash
sudo pacman -S tmux
gem install tmuxinator
```

> tmuxinator는 Ruby gem입니다. `ruby`와 `gem`이 설치되어 있어야 합니다.

## 2. tmux 설정 적용

프로젝트에 포함된 `.tmux.conf`를 홈 디렉토리에 복사합니다.

```bash
cp docs/tmux/.tmux.conf ~/.tmux.conf
```

> 기존 `~/.tmux.conf`가 있다면 백업 후 진행하세요: `cp ~/.tmux.conf ~/.tmux.conf.bak`

## 3. TPM (Tmux Plugin Manager) 설치

`.tmux.conf`에서 `tmux-resurrect` 플러그인을 사용하므로 TPM을 설치해야 합니다.

```bash
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

tmux를 실행한 뒤 플러그인을 설치합니다.

```bash
tmux
```

tmux 안에서 `prefix + I` (기본: `Ctrl-b` → `I`)를 눌러 플러그인을 설치합니다.

## 4. tmuxinator로 세션 시작

```bash
tmuxinator start -p docs/tmux/session.yml
```

### 세션 구조

| Window | 이름 | Layout | Panes | 용도 |
|--------|------|--------|-------|------|
| 0 | work | tiled (2x2) | 4 | 메인 작업 |
| 1 | server1 | even-vertical | 4 | 서버 에이전트 |
| 2 | server2 | even-vertical | 4 | 서버 에이전트 |
| 3 | client1 | even-vertical | 4 | 클라이언트 에이전트 |
| 4 | client2 | even-vertical | 4 | 클라이언트 에이전트 |
