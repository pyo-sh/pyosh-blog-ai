# Docker 개발 환경

AI 에이전트(Claude Code)를 Docker 컨테이너 안에서 실행하기 위한 환경입니다.
컨테이너 내부에서 tmux를 사용해 여러 에이전트를 병렬로 실행할 수 있습니다.

## 구조

```
Host (Windows / macOS / Linux)
  └─ Docker container (Ubuntu 24.04, user: dev)
       └─ tmux session "lab" (tmuxinator)
            ├─ pane 1: claude (Issue A)
            ├─ pane 2: claude (Issue B)
            └─ ...
```

> **Note**: 컨테이너는 non-root 사용자 `dev`로 실행됩니다. Claude Code의 `--dangerously-skip-permissions` 플래그는 root 권한에서 사용할 수 없기 때문입니다.

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

### 2. 인증 설정

인증은 컨테이너 내부의 독립 volume에서 관리됩니다. 호스트에서의 사전 인증은 필요하지 않습니다.
컨테이너에 처음 접속한 뒤 `dev-auth-setup`을 실행하면 각 도구의 로그인을 안내합니다.
자세한 내용은 [인증 volume 아키텍처](#인증-volume-아키텍처) 섹션을 참고하세요.

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

# 중지 + 컨테이너 삭제 (인증 volume 유지)
docker compose down

# 이미지까지 삭제 (인증 volume 유지, 재빌드 필요)
docker compose down --rmi all

# 인증 volume까지 삭제 (재인증 필요)
docker compose down --rmi all --volumes
# 또는 개별: docker volume rm dev-lab-auth
```

## 인증 volume 아키텍처

### 왜 독립 volume인가?

이전에는 호스트의 인증 파일(`~/.gitconfig`, `~/.config/gh`, `~/.ssh`)을 read-only로 바인드 마운트했습니다.
이 방식에는 두 가지 문제가 있었습니다:

1. **read-only 충돌** — `gh auth login`은 `hosts.yml`에 토큰을 써야 하는데, read-only 마운트라 `read-only file system` 에러가 발생
2. **Keyring 부재** — 호스트(macOS)에서는 Keychain에 토큰을 저장하지만, 컨테이너(Linux)에는 Keyring이 없어 토큰 참조 불가

따라서 **컨테이너 독립 named volume**으로 전환하여, 컨테이너 안에서 직접 로그인하고 토큰을 파일로 저장하는 방식을 채택했습니다.

### Volume과 Container의 관계

```
docker volume: dev-lab-auth          컨테이너 파일시스템 (임시)
┌─────────────────────────┐          ┌──────────────────────────┐
│ /home/dev/.auth/        │          │                          │
│   ├── gh/               │◀─symlink─│ ~/.config/gh             │
│   │   ├── config.yml    │          │                          │
│   │   └── hosts.yml     │          │                          │
│   ├── claude/           │◀─symlink─│ ~/.claude                │
│   │   ├── .credentials  │          │                          │
│   │   └── settings.json │          │                          │
│   ├── claude.json       │◀─symlink─│ ~/.claude.json           │
│   ├── codex/            │◀─symlink─│ ~/.codex                 │
│   │   └── auth.json     │          │                          │
│   ├── gitconfig         │◀─symlink─│ ~/.gitconfig             │
│   └── ssh/              │◀─symlink─│ ~/.ssh                   │
└─────────────────────────┘          └──────────────────────────┘
       영속 (컨테이너 삭제해도 유지)            컨테이너 삭제 시 소멸
```

- **Volume** (`dev-lab-auth`): Docker가 관리하는 독립 저장소. `docker compose down`으로 컨테이너를 삭제해도 데이터가 유지됨
- **심볼릭 링크**: entrypoint에서 각 도구의 표준 경로(`~/.config/gh`, `~/.claude` 등)를 volume 경로로 연결. 도구들은 평소처럼 표준 경로에 읽고 쓰지만, 실제 데이터는 volume에 저장됨

### 각 도구의 인증 저장 방식

| 도구 | 인증 파일 (volume 내) | 로그인 명령 |
|------|---------------------|------------|
| Git | `gitconfig` | `dev-auth-setup`에서 자동 안내 |
| GitHub CLI | `gh/hosts.yml` (`--insecure-storage`) | `gh auth login` |
| Claude Code | `claude/.credentials.json` | `claude` 실행 후 OAuth |
| Codex | `codex/auth.json` | `codex` 실행 후 로그인 |

### 인증 관리 명령어

```bash
# 인증 상태 확인
dev-auth-status

# 인증 재설정 (수동)
dev-auth-setup

# 인증 volume 초기화 (컨테이너 외부에서)
docker volume rm dev-lab-auth
```

## Aliases

컨테이너 내부에서 사용할 수 있는 단축 명령어가 `.bash_aliases`에 정의되어 있습니다.
세부 내용은 `tools/docker/.bash_aliases` 파일을 참조하세요.

## Nested tmux (키바인딩 토글)

호스트에서 `docker exec`로 컨테이너 tmux에 접속하면 **tmux가 중첩**됩니다.
이때 `Ctrl-b` prefix가 항상 호스트(outer) tmux에서 먼저 처리되므로, 컨테이너(inner) tmux를 직접 조작할 수 없습니다.

**호스트와 Docker에서 각각 다른 토글 키를 사용합니다.**

| 환경 | 토글 키 | 설정 파일 |
|------|---------|----------|
| Host (outer) | `Ctrl+F12` | `tools/tmux/host.tmux.conf` |
| Docker (inner) | `F12` | `tools/tmux/docker.tmux.conf` |

| 동작 | 설명 |
|------|------|
| `Ctrl+F12` 누르기 | outer tmux OFF → `Ctrl-b`가 inner tmux로 전달됨 |
| `Ctrl+F12` 다시 누르기 | outer tmux ON 복원 → `Ctrl-b`가 outer tmux에서 처리됨 |
| `F12` 누르기 | inner tmux OFF (inner 안에서 추가 중첩 시 사용) |

상태바 스타일이 어두워지고 `(OFF)` 표시가 나타나면 해당 tmux가 비활성 상태입니다.

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
| Codex | npm global |

## 네트워크

`network_mode: host`를 사용하므로 컨테이너와 호스트가 동일한 네트워크를 공유합니다.

## 볼륨 마운트

| 소스 | 컨테이너 경로 | 유형 | 용도 |
|------|-------------|------|------|
| 프로젝트 루트 (`../../`) | `/workspace` | bind (rw) | 소스코드 |
| `dev-lab-auth` | `/home/dev/.auth` | named volume | 인증/설정 (gh, claude, codex, git, ssh) |
| `tools/tmux/docker.tmux.conf` | `/home/dev/.tmux.conf` | bind (ro) | tmux 설정 |
| `tools/docker/.bash_aliases` | `/home/dev/.bash_aliases` | bind (ro) | 단축 명령어 |

> 프로젝트 루트가 read-write로 마운트되므로 컨테이너 안에서 수정한 파일은 호스트에도 반영됩니다.

## 트러블슈팅

### 빌드 실패

```bash
docker compose build --no-cache
```

### `gh` 인증 실패

컨테이너 안에서 `dev-auth-status`로 상태를 확인하세요.
재인증이 필요하면 `gh auth login --git-protocol https --insecure-storage`를 실행합니다.

### 인증 volume 초기화

인증 상태가 꼬였다면 volume을 삭제하고 다시 설정할 수 있습니다.

```bash
docker compose down
docker volume rm dev-lab-auth
docker compose up -d
# 접속 후 dev-auth-setup 실행
```

### 컨테이너 접속 불가

```bash
# 컨테이너 실행 상태 확인
docker ps

# 로그 확인
docker logs dev-lab
```
