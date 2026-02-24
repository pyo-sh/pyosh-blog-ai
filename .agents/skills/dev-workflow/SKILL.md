---
name: dev-workflow
description: GitHub Issue 기반 개발 워크플로. Issue → Worktree → Code → Push → PR 생성까지 수행. 코딩 작업 시작 시 자동 활성화. 리뷰는 별도 세션에서 /dev-review로 진행.
---

# Dev-Workflow

Issue → Worktree → Code → Push → PR 생성. 리뷰·머지는 별도 스킬. 전역 규칙(브랜치명, 커밋 형식, 멀티에이전트)은 `CLAUDE.md` 참조.

## 필수 전제: Git Remote

monorepo — `server/`, `client/`는 **각각 독립 Git 리포**. 모든 git/gh 명령은 **해당 영역 디렉토리에서 실행** (루트 실행 금지).

| 영역 | GitHub 리포 |
|------|-------------|
| `server/` | `pyo-sh/pyosh-blog-be` |
| `client/` | `pyo-sh/pyosh-blog-fe` |

## 워크플로

### 0. Issue 확인/생성
해당 영역에서 `gh issue list --assignee @me`. 없으면 사용자 승인 후 생성.

### 1. Worktree 생성
```bash
cd {영역}
git worktree add -b {type}/issue-{N}-{설명} .claude/worktrees/issue-{N} main
cd .claude/worktrees/issue-{N}
```
→ 브랜치 규칙: [branch-naming.md](references/branch-naming.md)

### 2. 코딩
- `{영역}/CLAUDE.md` 규칙 준수
- 기술 조사/결정 발생 시 → `/dev-log`로 findings/decision 기록

### 3. Progress 기록 (필수)
Push 전 **반드시** `/dev-log`로 progress 기록.

### 4. Push & PR 생성
```bash
git push -u origin {type}/issue-{N}-{설명}
```
PR은 **`--body-file` 필수** (셸 이스케이프 버그 방지). → 템플릿: [pr-template.md](references/pr-template.md)

### 5. 리뷰 요청 안내
PR 생성 후 사용자에게 **새 세션에서 `/dev-review` 실행** 안내. 이 세션에서 리뷰하지 않음.

> 후속: `/dev-review` → 수정 시 `/dev-review-answer` → 재리뷰 → 사용자 승인 & Merge

### 6. 정리
```bash
cd {영역}
git worktree remove .claude/worktrees/issue-{N}
git branch -d {type}/issue-{N}-{설명}
```

## 참조
- [브랜치 & 커밋 규칙](references/branch-naming.md)
- [PR 템플릿](references/pr-template.md)
