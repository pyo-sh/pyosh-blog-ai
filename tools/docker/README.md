# Docker 개발 환경

AI 에이전트(Claude Code)를 Docker 컨테이너 안에서 실행하기 위한 환경입니다.
컨테이너 내부에서 tmux를 사용해 여러 에이전트를 병렬로 실행할 수 있습니다.

## 구조

```
Host (Windows / macOS / Linux)
  └─ Docker container (Ubuntu 24.04)
       └─ tmux session "blog" (tmuxinator)
            ├─ pane 1: claude (Issue A)
            ├─ pane 2: claude (Issue B)
            └─ ...
```

## 사전 준비

### 1. Docker 설치

| OS | 설치 방법 |
|----|----------|
| Windows | [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) |
| macOS | [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) |
| Linux | [Docker Engine](https://docs.docker.com/engine/install/) |

설치 후 확인:

```bash
docker --version
docker compose version
```

### 2. GitHub CLI 인증 (호스트에서)

컨테이너가 호스트의 GitHub 인증 정보를 공유합니다. 호스트에서 먼저 인증이 되어 있어야 합니다.

```bash
gh auth login
```

### 3. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```bash
cp .env.example .env
```

`.env` 파일을 열어 값을 채웁니다:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

API 키는 https://console.anthropic.com/settings/keys 에서 발급받을 수 있습니다.

## 사용법

### 컨테이너 빌드 및 시작

```bash
cd tools/docker

# 이미지 빌드 + 컨테이너 시작 (백그라운드)
docker compose up -d
```

빌드 로그를 보고 싶다면 `-d`를 빼고 실행하세요.

### 컨테이너 접속

컨테이너가 시작되면 tmuxinator가 `lab` 세션을 자동으로 생성합니다.

```bash
docker exec -it dev-lab tmux attach -t lab
```

### 컨테이너 중지 및 삭제

```bash
cd tools/docker

# 중지
docker compose stop

# 중지 + 컨테이너 삭제
docker compose down

# 이미지까지 삭제 (재빌드 필요)
docker compose down --rmi all
```

## Aliases

컨테이너 내부에서 사용할 수 있는 단축 명령어가 `.bash_aliases`에 정의되어 있습니다.
세부 내용은 `tools/docker/.bash_aliases` 파일을 참조하세요.

## Nested tmux (F12 토글)

호스트에서 `docker exec`로 컨테이너 tmux에 접속하면 **tmux가 중첩**됩니다.
이때 `Ctrl-b` prefix가 항상 호스트(outer) tmux에서 먼저 처리되므로, 컨테이너(inner) tmux를 직접 조작할 수 없습니다.

**F12 키로 outer tmux의 키바인딩을 on/off 전환**할 수 있습니다.

| 동작 | 설명 |
|------|------|
| `F12` 누르기 | outer tmux OFF → `Ctrl-b`가 inner tmux로 전달됨 |
| `F12` 다시 누르기 | outer tmux ON 복원 → `Ctrl-b`가 outer tmux에서 처리됨 |

상태바 스타일이 어두워지고 `(OFF)` 표시가 나타나면 outer tmux가 비활성 상태입니다.

> 이 설정은 `tools/tmux/.tmux.conf`에 정의되어 있으며, 호스트와 컨테이너가 동일한 파일을 공유합니다.
> F12는 항상 가장 바깥 tmux에서 가로채므로 충돌 없이 동작합니다.

## 컨테이너 내부 환경

| 도구 | 버전/설명 |
|------|----------|
| Ubuntu | 24.04 |
| Node.js | 22.x |
| pnpm | latest (corepack) |
| Python | 3.x |
| Git | apt 기본 |
| GitHub CLI (gh) | apt 기본 |
| tmux | apt 기본 |
| tmuxinator | gem 설치 |
| Claude Code | npm global |

## 네트워크

`network_mode: host`를 사용하므로 컨테이너와 호스트가 동일한 네트워크를 공유합니다.

## 볼륨 마운트

| 호스트 경로 | 컨테이너 경로 | 모드 | 용도 |
|------------|--------------|------|------|
| 프로젝트 루트 (`../../`) | `/workspace` | read-write | 소스코드 |
| `~/.gitconfig` | `/root/.gitconfig` | read-only | Git 설정 |
| `~/.config/gh` | `/root/.config/gh` | read-only | GitHub CLI 인증 |
| `~/.ssh` | `/root/.ssh` | read-only | SSH 키 |
| `~/.claude` | `/root/.claude` | read-write | Claude Code 설정/메모리 |
| `tools/tmux/.tmux.conf` | `/root/.tmux.conf` | read-only | tmux 설정 (F12 토글 포함) |
| `tools/docker/.bash_aliases` | `/root/.bash_aliases` | read-only | 단축 명령어 |

> 프로젝트 루트가 read-write로 마운트되므로 컨테이너 안에서 수정한 파일은 호스트에도 반영됩니다.

## 트러블슈팅

### 빌드 실패

```bash
docker compose build --no-cache
```

### `gh` 인증 실패

호스트에서 `gh auth status`를 확인하세요. 로그인이 되어 있지 않으면 `gh auth login`을 먼저 실행해야 합니다.

### 컨테이너 접속 불가

```bash
# 컨테이너 실행 상태 확인
docker ps

# 로그 확인
docker logs dev-lab
```
