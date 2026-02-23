---
name: dev-workflow
description: GitHub Issue 기반 개발 워크플로. Issue → Worktree → Code → Push → PR → Review → Merge 순서로 작업을 수행. 코딩 작업 시작 시 자동 활성화.
---

# Dev-Workflow for pyosh-blog

모든 코딩 작업은 **GitHub Issue에서 시작**하여 **PR Merge로 종료**. 전역 규칙(브랜치명, 커밋 형식, 멀티 에이전트 등)은 `CLAUDE.md` 참조.

## 워크플로 순서

### 0. Issue 확인/생성
- `gh issue list --assignee @me`로 할당 Issue 확인
- Issue 없으면 사용자 승인 후 생성:
  ```bash
  gh issue create --title "[{area}] {설명}" --body "## 배경\n...\n## 요구사항\n...\n## 완료 기준\n..." --label "{area},{type}"
  ```

### 1. Worktree 생성
```bash
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
```bash
git push -u origin {type}/issue-{N}-{설명}
gh pr create --title "{type}: description (#{N})" --body "Closes #{N}\n\n## 변경 사항\n..."
```
PR 템플릿: [pr-template.md](assets/pr-template.md)

### 4. AI 리뷰
- 코드 품질, 보안, 성능 체크
- 리뷰 코멘트를 PR에 작성

### 5. 사용자 승인 & Merge
- 사용자 최종 승인 필수 (AI 자동 merge 금지)
- Squash merge 권장

### 6. 정리
```bash
git worktree remove .claude/worktrees/issue-{N}
git branch -d {type}/issue-{N}-{설명}
```

## Issue 생명주기

```
Open → In Progress (assigned) → PR Created → Review → Merged → Closed
```

## 참조

- [브랜치 명명 규칙](assets/branch-naming.md)
- [PR 템플릿](assets/pr-template.md)
