---
name: dev-workflow
description: GitHub Issue 기반 개발 워크플로. Issue → Worktree → Code → Push → PR 생성까지 수행. 코딩 작업 시작 시 자동 활성화. 리뷰는 별도 세션에서 /dev-review로 진행.
---

# Dev-Workflow for pyosh-blog

모든 코딩 작업은 **GitHub Issue에서 시작**하여 **PR 생성으로 종료**. 리뷰·머지는 별도 스킬로 분리. 전역 규칙(브랜치명, 커밋 형식, 멀티 에이전트 등)은 `CLAUDE.md` 참조.

## Git Remote 규칙 (필수)

이 프로젝트는 monorepo이며, `server/`와 `client/`는 **각각 독립된 Git 리포**를 가진다.

| 영역 | 경로 | GitHub 리포 | Git 작업 디렉토리 |
|------|------|-------------|-------------------|
| server | `server/` | `pyo-sh/pyosh-blog-be` | `server/` 내에서 실행 |
| client | `client/` | `pyo-sh/pyosh-blog-fe` | `client/` 내에서 실행 |

**핵심 원칙:**
- `gh issue`, `gh pr`, `git push` 등 **모든 Git/GitHub 명령은 해당 영역의 디렉토리에서 실행**하거나 `--repo` 플래그로 대상 리포를 명시
- 루트(`pyosh-blog/`)에서 실행하면 **잘못된 리포**에 반영됨 — 절대 금지
- 라벨은 각 리포의 `.github/labels.json` 참조

```bash
# server 작업 시
cd server && gh issue list
gh issue create --repo pyo-sh/pyosh-blog-be ...

# client 작업 시
cd client && gh issue list
gh issue create --repo pyo-sh/pyosh-blog-fe ...
```

## 워크플로 순서

### 0. Issue 확인/생성
- 해당 영역 디렉토리에서 `gh issue list --assignee @me` 실행
- Issue 없으면 사용자 승인 후 **해당 리포에** 생성:
  ```bash
  # 예: server 작업
  gh issue create --repo pyo-sh/pyosh-blog-be \
    --title "[server] {설명}" \
    --body "## 배경\n...\n## 요구사항\n...\n## 완료 기준\n..." \
    --label "{type}"
  ```

### 1. Worktree 생성
해당 영역 디렉토리 내에서 worktree 생성:
```bash
# 예: server 작업
cd server
git worktree add -b {type}/issue-{N}-{설명} .claude/worktrees/issue-{N} main
cd .claude/worktrees/issue-{N}
```

### 2. 코딩
- `client/CLAUDE.md` 또는 `server/CLAUDE.md` 규칙 준수
- 커밋 형식: `{type}: {description} (#{N})`

### 2-1. `/dev-log` — 코딩 중 기록 (트리거 조건별)

| 트리거 조건 | 기록 대상 | 파일 |
|---|---|---|
| 라이브러리 비교, 기술 조사 수행 | **findings** | `findings/findings.NNN-topic.md` |
| 아키텍처/기술 선택 필요 | **decision** (draft) | `decisions/decision-NNN-topic.md` |

### 2-2. `/dev-log` — PR 생성 전 progress 기록 (필수)

Push 전에 **반드시** `/dev-log`로 progress 기록:

| 트리거 조건 | 기록 대상 | 파일 |
|---|---|---|
| 코딩 완료, push 직전 (항상) | **progress** | `progress/progress.YYYY-MM-DD.md` |

### 3. Push & PR 생성
해당 영역의 worktree 내에서 실행:
```bash
git push -u origin {type}/issue-{N}-{설명}
```
PR 생성은 **반드시 `--body-file` 사용** (셸 이스케이프 버그 방지):
```bash
# 1. 임시 파일에 PR 본문 작성
cat > /tmp/pr-{N}-body.md <<'PREOF'
## Summary
Closes #{N}

- 변경 사항 1

## Test plan
- [ ] 테스트 항목
PREOF

# 2. --body-file로 PR 생성
gh pr create \
  --title "{type}: description (#{N})" \
  --body-file /tmp/pr-{N}-body.md
```
PR 템플릿: [pr-template.md](assets/pr-template.md)

### 4. 리뷰 요청 안내
- PR 생성 후 사용자에게 **새 세션에서 `/dev-review` 실행**을 안내
- 이 세션에서는 리뷰를 수행하지 않음 (컨텍스트 오염 방지)

> **후속 흐름**: `/dev-review` (별도 세션) → 수정 필요 시 `/dev-review-answer` → 재리뷰 → 사용자 승인 & Merge

### 5. 정리
해당 영역 디렉토리에서 실행:
```bash
cd server  # 또는 cd client
git worktree remove .claude/worktrees/issue-{N}
git branch -d {type}/issue-{N}-{설명}
```

## Issue 생명주기

```
Open → In Progress (assigned) → PR Created → Review (dev-review) → Fix (dev-review-answer) → Merged → Closed
```

## 관련 스킬

| 스킬 | 용도 | 실행 세션 |
|------|------|-----------|
| **dev-review** | PR 코드 리뷰 | 코드 작성과 **다른 세션** |
| **dev-review-answer** | 리뷰 코멘트 수정 대응 | 코드 작성 세션 또는 별도 세션 |

## 참조

- [브랜치 명명 규칙](assets/branch-naming.md)
- [PR 템플릿](assets/pr-template.md)
