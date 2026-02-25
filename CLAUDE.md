# pyosh-blog - 전역 규칙

## 프로젝트 개요

이 프로젝트는 **모노레포(monorepo)** 구조로, 다음 3개 디렉토리로 구성됩니다:

- **client**: Next.js 프론트엔드 (블로그 공개 페이지 + 관리자 페이지)
- **server**: Fastify API 서버 (Drizzle ORM + MySQL)
- **docs**: 프로젝트 메모리 및 문서 저장소 (client/server 분리)

## 디렉토리 구조

```
pyosh-blog/
├── .claudeignore                # 무시 패턴
├── CLAUDE.md                    # (현재 파일) 전역 규칙
├── .claude/
│   ├── settings.local.json      # 권한 설정
│   └── skills/                  # 스킬 심볼릭 링크
├── .workspace/                  # gitignored
│   ├── worktrees/               # Git worktree
│   └── pipeline/                # 파이프라인 상태 파일
├── docs/
│   ├── client/                  # client 작업 기록
│   │   ├── progress.index.md
│   │   ├── findings.index.md
│   │   ├── decisions.index.md
│   │   ├── progress/
│   │   ├── findings/
│   │   └── decisions/
│   └── server/                  # server 작업 기록
│       ├── progress.index.md
│       ├── findings.index.md
│       ├── decisions.index.md
│       ├── progress/
│       ├── findings/
│       └── decisions/
├── skills/                      # 스킬 소스
│   ├── dev-build/            # 개발 워크플로
│   ├── dev-log/                 # 기록 관리
│   └── subagent-creator/        # 서브에이전트 생성
├── client/
│   ├── CLAUDE.md                # client 전용 규칙
│   └── ...
├── server/
│   ├── CLAUDE.md                # server 전용 규칙
│   └── ...
└── pyosh-blog.code-workspace
```

## 무시 규칙

- `@.claudeignore` 참조

---

## Issue 기반 작업 관리

**GitHub Issues가 유일한 작업 소스**입니다. 모든 AI 도구(Claude Code, Codex 등)는 이 규칙을 따릅니다.

### 핵심 원칙
1. **Issue 없는 코딩 금지** — 모든 작업은 GitHub Issue에서 시작
2. **Issue가 Single Source of Truth** — 작업 상태, 요구사항, 논의 모두 Issue에 기록
3. 사용자와 AI 모두 Issue 생성 가능
4. 커밋과 PR에 이슈 번호 필수 포함

### Issue 확인
```bash
gh issue list                    # 전체 이슈
gh issue list --assignee @me     # 내 이슈
gh issue view {N}                # 상세 보기
```

---

## Git 워크플로

**Simplified Git Flow**: main + feature 브랜치만 사용 (develop 브랜치 없음)

### 필수 규칙
1. **main 직접 push 금지**
2. **모든 작업은 worktree로 분리**
3. **브랜치명**: `{feat|fix|docs|refactor}/issue-{N}-{설명}`
4. **커밋 메시지**: `{type}: {description} (#{N})`
5. **PR에 `Closes #{N}` 포함**
6. **사용자 승인 없이 merge 금지**

### 워크플로 순서
```
Issue 확인 → worktree 생성 → 코딩 → push → PR 생성 → AI 리뷰 → 사용자 승인 → merge → worktree 정리
```

---

## 멀티 에이전트 규칙

여러 AI 에이전트가 동시에 작업할 수 있습니다:

1. **에이전트 수 무제한** — Task 기반으로 필요한 만큼 생성
2. **1 에이전트 = 1 Issue** — 각 에이전트는 할당된 Issue만 담당
3. **Worktree 격리 필수** — 에이전트마다 별도 worktree
4. **파일 충돌 방지** — 같은 파일을 수정하는 Issue는 동시 진행 금지
5. **기술 결정은 `docs/{area}/decisions/`에 draft 작성** — 사용자 승인 후 진행

---

## 작업 선택 규칙

코딩 작업을 요청받으면 **반드시 아래 순서를 따르라:**

1. **Issue 확인** — `gh issue list`로 해당 작업의 Issue가 있는지 확인. 없으면 사용자 승인 후 생성.
2. **`/dev-build` 스킬 실행** — Issue 번호가 확보되면 dev-build에 따라 worktree 생성 → 코딩 → PR 생성.
3. **`/dev-log` 스킬 실행** — 코딩 중 기술 조사/결정 발생 시, 코딩 완료 후 PR 생성 전에 반드시 dev-log로 `docs/{area}/`에 기록.

**금지**: Issue 확인 없이 바로 코딩 시작하는 것.

---

## 스킬 참조

| 스킬 | 용도 |
|------|------|
| **dev-build** | Issue → Worktree → Code → PR → Merge 전체 워크플로 |
| **dev-log** | progress / findings / decisions 기록 관리 |
| **subagent-creator** | 서브 에이전트 생성 |

---

## 공통 개발 원칙

- **TypeScript Strict Mode** 사용
- **pnpm** 패키지 매니저
- **ESLint + Prettier** 자동 포맷팅

## 권한 설정

- `@.claude/settings.local.json` 참조
