# pyosh-blog-ai

AI 컨텍스트 및 개발 워크플로를 관리하는 부모 레포지토리입니다.

실제 애플리케이션 코드는 별도 레포지토리(`pyosh-blog-fe`, `pyosh-blog-be`)에서 관리되며, 이 레포지토리는 AI 도구(Claude Code 등)가 모노레포처럼 작업할 수 있도록 컨텍스트를 통합합니다.

## 초기 세팅

이 레포지토리를 클론한 뒤, `client/`와 `server/` 폴더에 각각의 애플리케이션 레포지토리를 클론해야 합니다.

```bash
# 1. 부모 레포지토리 클론
git clone https://github.com/pyo-sh/pyosh-blog-ai.git pyosh-blog
cd pyosh-blog

# 2. client (프론트엔드) 레포지토리 클론
git clone https://github.com/pyo-sh/pyosh-blog-fe.git client

# 3. server (백엔드) 레포지토리 클론
git clone https://github.com/pyo-sh/pyosh-blog-be.git server
```

> `client/`와 `server/`는 `.gitignore`에 포함되어 있어 부모 레포지토리에서 추적하지 않습니다.

## 프로젝트 구조

```
pyosh-blog/
├── CLAUDE.md                    # AI 에이전트 전역 규칙
├── client/                      # pyosh-blog-fe (Next.js)
├── server/                      # pyosh-blog-be (Fastify + Drizzle ORM + MySQL)
├── docs/
│   ├── client/                  # client 작업 기록 (progress / findings / decisions)
│   └── server/                  # server 작업 기록
├── tools/                       # 개발자 편의 도구 (tmux 등)
├── skills/                      # Claude Code 스킬
├── scripts/                     # 유틸리티 스크립트
├── .env.example                 # 환경 변수 템플릿
└── pyosh-blog.code-workspace    # VS Code 워크스페이스
```

## 레포지토리 관계

| 역할                  | 레포지토리                                               | 로컬 경로  |
| --------------------- | -------------------------------------------------------- | ---------- |
| AI 컨텍스트 (이 레포) | [pyosh-blog-ai](https://github.com/pyo-sh/pyosh-blog-ai) | `/` (루트) |
| 프론트엔드            | [pyosh-blog-fe](https://github.com/pyo-sh/pyosh-blog-fe) | `/client`  |
| 백엔드                | [pyosh-blog-be](https://github.com/pyo-sh/pyosh-blog-be) | `/server`  |

각 레포지토리는 독립적인 Git 히스토리를 가지며, 부모 레포지토리에서 서브모듈이 아닌 별도 클론으로 관리됩니다.

## 이 레포지토리가 관리하는 것

- **`CLAUDE.md`** — AI 에이전트의 작업 규칙 (Issue 기반 워크플로, Git 컨벤션 등)
- **`docs/`** — 개발 진행 기록, 기술 조사, 아키텍처 결정 문서
- **`.agents/skills/`** — Claude Code 커스텀 스킬
- **GitHub Issues** — 모든 작업의 Single Source of Truth

## 환경 변수 설정

`tools/` 폴더의 개발자 편의 도구(tmux 세션 등)는 환경 변수를 통해 로컬 경로를 설정합니다. 처음 세팅할 때 `.env.example`을 복사하여 본인의 환경에 맞게 수정하세요.

```bash
cp .env.example .env
# .env 파일을 열어 경로를 수정
```

> `.env`는 `.gitignore`에 포함되어 있어 git에 추적되지 않습니다.

## AI 개발 워크플로

모든 코딩 작업은 GitHub Issue에서 시작하여 PR Merge로 종료됩니다. 코드 작성과 리뷰는 **별도 AI 세션**에서 실행하여 컨텍스트 오염을 방지합니다.

### 자동 파이프라인 (`/dev-pipeline`)

`/dev-pipeline`은 코딩부터 Merge까지 전체 사이클을 오케스트레이션합니다. 리뷰/수정은 tmux 사이드 패인에서 별도 Claude 인스턴스가 처리하며, 사용자는 각 단계에서 의사결정만 합니다.

```
┌─ 메인 세션 (오케스트레이터) ──────────────────────────────────┐
│                                                               │
│  /dev-build (코딩 + PR 생성)                                  │
│       │                                                       │
│       ▼                                                       │
│  ┌─ tmux 사이드 패인 ──────┐                                  │
│  │  /dev-review (코드 리뷰) │                                  │
│  └──────────┬──────────────┘                                  │
│             │                                                 │
│             ▼                                                 │
│  ┌─ Critical 있음 ─────────────────────────────────────────┐  │
│  │  ┌─ tmux 사이드 패인 ──────┐                            │  │
│  │  │  /dev-resolve (코드 수정) │ ──→ 재리뷰 (자동 반복)    │  │
│  │  └─────────────────────────┘                            │  │
│  └─────────────────────────────────────────────────────────┘  │
│             │                                                 │
│             ▼                                                 │
│  ┌─ Critical 없음 ─── 사용자 결정 ─────┐                     │
│  │                                      │                     │
│  │  "Merge"          → 바로 Merge       │                     │
│  │  "Fix & Re-review" → 수정 후 재리뷰  │                     │
│  │  "Fix & Merge"    → 수정 후 바로 Merge │                    │
│  └──────────────────────────────────────┘                     │
│             │                                                 │
│             ▼                                                 │
│  Merge → Worktree 정리 → /dev-log                             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

> **토큰 효율성**: 오케스트레이터는 `gh api` 폴링만 수행하고, 코드 분석은 하지 않습니다. Review/Resolve는 별도 Claude 인스턴스에서 실행되어 토큰이 분리됩니다.

### 수동 실행

각 스킬을 별도 세션에서 개별 실행할 수도 있습니다:

```bash
# 세션 A: 코딩
/dev-build

# 세션 B: 리뷰 (코드 작성과 다른 세션에서 실행)
/dev-review

# 세션 C: 리뷰 대응 (필요시)
/dev-resolve
```

### 스킬 목록

| 스킬 | 용도 |
|------|------|
| **dev-pipeline** | 전체 자동화 오케스트레이션 (build → review → resolve → merge) |
| **dev-build** | Issue → Worktree → 코딩 → Push → PR 생성 |
| **dev-review** | PR 코드 리뷰 (심각도: Critical / Warning / Suggestion) |
| **dev-resolve** | 리뷰 코멘트 대응 및 코드 수정 |
| **dev-log** | progress / findings / decisions 기록 관리 |
| **dev-plan** | decisions 파일을 GitHub Issue로 변환 |

### 리뷰 심각도와 Merge 흐름

| 심각도 | 의미 | 파이프라인 동작 |
|--------|------|----------------|
| **Critical** | 버그, 보안 취약점, 데이터 손실 위험 | 자동으로 `/dev-resolve` 트리거, 수정 후 재리뷰 |
| **Warning** | 잠재적 문제, 성능 저하 | 사용자가 수정 여부 결정 |
| **Suggestion** | 가독성, 컨벤션 개선 | 사용자가 수정 여부 결정 |

Critical이 모두 해결되면 사용자에게 Warning/Suggestion 처리 방법을 묻습니다. 사용자가 수용 가능하다고 판단하면 즉시 Merge할 수 있습니다.

### tmux 환경 설정

tmux 및 tmuxinator 설치, 세션 구성에 대해서는 [tools/tmux/README.md](tools/tmux/README.md)를 참조하세요.

### 왜 세션을 분리하는가?

같은 AI 세션이 코드 작성과 리뷰를 모두 수행하면, 작성 시의 컨텍스트가 리뷰를 편향시킵니다. 세션을 분리하면:

- **리뷰어는 코드만 봅니다** — "왜 이렇게 했는지"를 모르기 때문에 코드 자체의 품질을 평가
- **엣지케이스 발견률 향상** — 작성자의 blind spot을 다른 시각에서 포착
- **리뷰 기준의 일관성** — 체크리스트 기반으로 매번 동일한 기준 적용
