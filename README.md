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
- **`skills/`** — Claude Code 커스텀 스킬 (dev-workflow, dev-log 등)
- **GitHub Issues** — 모든 작업의 Single Source of Truth
