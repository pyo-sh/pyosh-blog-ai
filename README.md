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
├── skills/                      # Claude Code 스킬
├── scripts/                     # 유틸리티 스크립트
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

## AI 개발 워크플로

모든 코딩 작업은 GitHub Issue에서 시작하여 PR Merge로 종료됩니다. 각 단계는 독립된 AI 세션에서 실행하여 **컨텍스트 오염을 방지**합니다.

### 전체 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  세션 A: /dev-build                                      │
│  Issue 확인 → Worktree 생성 → 코딩 → /dev-log → PR 생성    │
└──────────────────────────┬──────────────────────────────────┘
                           │ PR 생성 완료
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  세션 B: /dev-review                                        │
│  PR diff 분석 → 체크리스트 리뷰 → 심각도별 코멘트 작성      │
└──────────────────────────┬──────────────────────────────────┘
                           │ Critical/Warning 발견 시
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  세션 C: /dev-resolve                                 │
│  리뷰 코멘트 확인 → 코드 수정 → Push → 재리뷰 요청          │
└──────────────────────────┬──────────────────────────────────┘
                           │ 재리뷰 필요 시 세션 B 반복
                           ▼
                    사용자 승인 & Merge
```

### 스킬 목록

| 스킬 | 용도 | 실행 세션 |
|------|------|-----------|
| **dev-build** | Issue → Worktree → 코딩 → Push → PR 생성 | 세션 A |
| **dev-review** | PR 코드 리뷰 (심각도 3단계: Critical / Warning / Suggestion) | 세션 B (코드 작성과 **다른 세션**) |
| **dev-resolve** | 리뷰 코멘트 대응 및 코드 수정 | 세션 C (별도 세션) |
| **dev-log** | progress / findings / decisions 기록 관리 | dev-build 내에서 사용 |
| **dev-plan** | decisions 파일을 GitHub Issue로 변환 | 독립 실행 |

### 왜 세션을 분리하는가?

같은 AI 세션이 코드 작성과 리뷰를 모두 수행하면, 작성 시의 컨텍스트(의도, 트레이드오프 판단)가 리뷰를 편향시킵니다. 세션을 분리하면:

- **리뷰어는 코드만 봅니다** — "왜 이렇게 했는지"를 모르기 때문에 코드 자체의 품질을 평가
- **엣지케이스 발견률 향상** — 작성자의 blind spot을 다른 시각에서 포착
- **리뷰 기준의 일관성** — 체크리스트 기반으로 매번 동일한 기준 적용
