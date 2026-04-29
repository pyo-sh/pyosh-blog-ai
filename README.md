# pyosh-blog-ai

`pyosh-blog-ai`는 pyosh-blog 개발을 위한 AI 컨텍스트, 작업 기록, 자동화 스킬, Docker/tmux 개발 환경을 관리하는 루트 레포지토리입니다.

애플리케이션 코드는 이 레포지토리에 포함되지 않습니다. `client/`와 `server/`는 같은 워크스페이스 아래에 별도로 클론되는 독립 Git 레포지토리입니다.

## Repositories

| Area | GitHub repo | Local path | 역할 |
|------|-------------|------------|------|
| `workspace` | `pyo-sh/pyosh-blog-ai` | `/workspace` | AI 컨텍스트, docs, skills, 개발 환경 |
| `client` | `pyo-sh/pyosh-blog-fe` | `/workspace/client` | Next.js 프론트엔드 |
| `server` | `pyo-sh/pyosh-blog-be` | `/workspace/server` | Fastify API 서버 |

각 area는 독립 Git repo입니다. `client`나 `server` 작업에서 `git`, `gh`, `pnpm`을 실행할 때는 해당 디렉터리로 이동해서 실행합니다.

## Setup

```bash
git clone https://github.com/pyo-sh/pyosh-blog-ai.git pyosh-blog
cd pyosh-blog

git clone https://github.com/pyo-sh/pyosh-blog-fe.git client
git clone https://github.com/pyo-sh/pyosh-blog-be.git server

cp .env.example .env
```

`client/`와 `server/`는 루트 repo의 `.gitignore`에 포함되어 있습니다. 루트 repo는 서브모듈을 사용하지 않습니다.

## Directory Map

```text
pyosh-blog/
├── AGENTS.md                    # Codex/agent 공통 작업 규칙
├── CLAUDE.md                    # Claude Code 루트 컨텍스트
├── client/                      # pyosh-blog-fe, 별도 Git repo
├── server/                      # pyosh-blog-be, 별도 Git repo
├── docs/
│   ├── client/                  # client progress / findings / decisions
│   ├── server/                  # server progress / findings / decisions
│   └── workspace/               # root repo, tools, workflow 기록
├── .agents/
│   ├── references/              # area/repo/worktree 공통 정의
│   ├── scripts/                 # monorepo shell helpers
│   └── skills/                  # Codex/Claude workflow skills
├── .claude/                     # 루트 repo Claude Code 설정과 shared rules
├── tools/
│   ├── claude/                  # Claude 설정 템플릿과 bootstrap
│   ├── docker/                  # dev-lab Docker 환경
│   └── tmux/                    # host/container tmux 설정
├── scripts/
│   └── context-bar.sh           # Claude Code statusLine
└── .workspace/                  # worktrees, pipeline state, 임시 산출물 (ignored)
```

## Managed Content

- `docs/`: 진행 기록, 기술 조사, 의사결정 문서. `/dev-log`는 long-lived `docs` 브랜치에 기록하고, `/dev-archive`로 main에 반영합니다.
- `.agents/skills/`: issue 기반 개발, 리뷰, 기록, GitHub CLI, handoff, design-system 관련 스킬.
- `.agents/references/monorepo-layout.md`: area, repo, worktree path의 단일 기준.
- `tools/`: Docker, tmux, Claude 설정 동기화 도구.
- `scripts/context-bar.sh`: Claude Code status line. 현재 Claude hook 기반 tracker는 사용하지 않습니다.

`.workspace/`는 런타임 상태와 임시 파일을 담는 ignored 디렉터리입니다. 과거 도구의 산출물이 남아 있을 수 있지만, 소스 오브 트루스로 취급하지 않습니다.

## Environment

`.env`는 로컬 전용입니다.

| 변수 | 용도 |
|------|------|
| `TMUX_ROOT` | tmuxinator 세션 root 경로 |
| `TZ` | Docker 컨테이너 timezone. 기본값은 `Asia/Seoul` |

## Docker And Tmux

Docker 개발 환경은 [tools/docker/README.md](tools/docker/README.md)를 참조하세요.

```bash
cd tools/docker
docker compose up -d
docker exec -it dev-lab tmux attach -t lab
```

tmux 설정과 세션 시작 방법은 [tools/tmux/README.md](tools/tmux/README.md)를 참조하세요. 현재 컨테이너 세션은 `lab`, `server1`, `client1` 세 window로 구성됩니다. 파이프라인 실행에 tmux는 필수가 아니며, 병렬 작업을 위한 편의 환경입니다.

## Claude Code Config

공유 Claude 설정의 원본은 `tools/claude/templates/`입니다. 배포된 `.claude/` 파일을 직접 수정하기보다 템플릿을 수정하고 bootstrap을 실행합니다.

```bash
bash tools/claude/bootstrap.sh --dry-run
bash tools/claude/bootstrap.sh --apply
```

컨테이너에서는 `entrypoint.sh`가 `/home/dev/.auth` volume을 `~/.claude`, `~/.codex`, `~/.config/gh`, `~/.gitconfig`, `~/.ssh`로 연결합니다. Claude Code의 `statusLine`은 `/workspace/scripts/context-bar.sh`를 직접 참조합니다.

## Workflow

애플리케이션 작업은 GitHub Issue에서 시작해 PR merge로 끝납니다. 루트 repo 작업은 사용자 지시를 우선하며, 완료 후 `docs/workspace/`에 기록합니다.

### Core Skills

| Skill | 용도 |
|-------|------|
| `dev-build` | Issue → worktree → 코드 변경 → push → PR 생성 |
| `dev-review` | PR 코드 리뷰. 작성 세션과 분리해서 실행 |
| `dev-resolve` | 리뷰 코멘트 대응, 수정, re-review 요청 |
| `dev-pipeline` | build → review → resolve → merge → log 자동화 |
| `dev-codex-pipeline` | Codex 중심 synchronous pipeline |
| `dev-log` | progress / findings / decisions 기록을 `docs` 브랜치에 저장 |
| `dev-archive` | 누적된 `docs` 브랜치를 PR로 main에 squash merge |
| `dev-issue` | docs나 사용자 요청을 GitHub Issue로 변환 |

추가 스킬은 `.agents/skills/` 아래에 있습니다. 특정 스킬의 세부 절차는 각 `SKILL.md`를 기준으로 합니다.

### Worktrees

작업 worktree는 루트 repo 아래에 area별로 생성됩니다.

```text
.workspace/worktrees/{area}/issue-{N}
```

이 경로는 area별 issue 번호 충돌을 피하고, `client`/`server` Git repo 내부에 pipeline 상태를 섞지 않기 위한 규칙입니다.

### Verification

| Area | 확인 명령 |
|------|-----------|
| `client` | `(cd client && pnpm compile:types && pnpm lint && pnpm build)` |
| `server` | `(cd server && pnpm test)` |
| `workspace` | 변경 내용에 맞는 문서/스크립트 검증. 고정 verify 명령 없음 |

## Retired Runtime Tooling

다음 구성은 런타임 도구에서 제거되었습니다. 관련 과거 기록은 `docs/`와 Git history에 남깁니다.

- `dev-orchestrator`
- `tools/orchctl`
- `tools/agent-tracker`
- Figma MCP 설정 (`.mcp.json`, `mcp/figma-*`)
- Claude hook 기반 agent tracker

새 자동화는 현재 남아 있는 `.agents/skills/`, `tools/`, `scripts/`를 기준으로 추가합니다.
