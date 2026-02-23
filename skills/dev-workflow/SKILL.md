---
name: dev-workflow
description: GitHub Issue 기반 개발 워크플로. Issue → Worktree → Code → Push → PR → Review → Merge 순서로 작업을 수행. 코딩 작업 시작 시 자동 활성화.
disable-model-invocation: false
user-invocable: true
---

# Dev-Workflow for pyosh-blog

## 개요

모든 코딩 작업은 **GitHub Issue에서 시작**하여 **PR Merge로 종료**됩니다. 이 스킬은 Issue 확인부터 Merge까지의 전체 개발 흐름을 정의합니다.

## 필수 규칙 8가지

1. **작업은 반드시 GitHub Issue에서 시작** — Issue 없는 코딩 금지
2. **코딩 전 git worktree 생성 필수** — main에서 직접 작업 금지
3. **브랜치명**: `{feat|fix|docs|refactor}/issue-{N}-{설명}` ([branch-naming.md](assets/branch-naming.md) 참고)
4. **커밋 메시지에 이슈 번호 포함**: `feat: description (#123)`
5. **작업 완료 후 PR 생성** — [pr-template.md](assets/pr-template.md) 형식 사용
6. **PR에 `Closes #N` 포함** — 자동 Issue 종료
7. **AI 리뷰 수행, 사용자 승인 필수** — AI가 자동 merge 금지
8. **main 직접 push 금지**

## 워크플로 순서

### 0. Issue 생성 (해당 Issue가 없는 경우)

작업에 대응하는 GitHub Issue가 없으면 AI가 직접 생성할 수 있다. **단, 반드시 사용자에게 승인을 받은 후 생성해야 한다.**

1. Issue 제목, 라벨, 본문 초안을 사용자에게 제시
2. 사용자가 승인하면 생성

```bash
gh issue create \
  --title "[{area}] {설명}" \
  --body "## 배경\n...\n\n## 요구사항\n...\n\n## 완료 기준\n..." \
  --label "{area},{type}"
```

> Issue가 이미 존재하면 이 단계를 건너뛴다.

### 1. Issue 확인
```bash
gh issue list --assignee @me
gh issue view {N}
```

### 2. Worktree 생성
```bash
git worktree add -b feat/issue-{N}-{설명} .claude/worktrees/issue-{N} main
cd .claude/worktrees/issue-{N}
```
> 상세: [git-worktree-guide.md](references/git-worktree-guide.md)

### 3. 코딩
- `client/CLAUDE.md` 또는 `server/CLAUDE.md` 규칙 준수
- 커밋 메시지 형식: `{type}: {description} (#{N})`

### 3-1. `/dev-log` — 코딩 중 기록 (트리거 조건별)

코딩 중 아래 조건에 해당하면 **즉시** `/dev-log` 스킬을 실행하여 기록한다:

| 트리거 조건 | 기록 대상 | 파일 |
|---|---|---|
| 라이브러리 비교, 기술 조사를 수행했을 때 | **findings** | `findings/findings.NNN-topic.md` |
| 아키텍처/기술 선택이 필요할 때 | **decision** (draft) | `decisions/decision-NNN-topic.md` |

### 3-2. `/dev-log` — PR 생성 전 progress 기록 (필수)

Push 전에 **반드시** `/dev-log` 스킬을 실행하여 progress를 기록한다:

| 트리거 조건 | 기록 대상 | 파일 |
|---|---|---|
| 코딩 완료, push 직전 (항상) | **progress** | `progress/progress.YYYY-MM-DD.md` |

> findings/decision은 코딩 중 조건 충족 시 즉시, progress는 push 전 반드시 1회.

### 4. Push & PR 생성
```bash
git push -u origin feat/issue-{N}-{설명}
gh pr create --title "feat: description (#N)" --body "Closes #N\n\n## 변경 사항\n..."
```

### 5. AI 리뷰
- 코드 품질, 보안, 성능 체크
- 리뷰 코멘트를 PR에 작성

### 6. 사용자 승인 & Merge
- 사용자가 최종 승인
- Squash merge 권장

### 7. 정리
```bash
git worktree remove .claude/worktrees/issue-{N}
git branch -d feat/issue-{N}-{설명}
```

## Issue 생명주기

> 상세: [issue-workflow.md](references/issue-workflow.md)

```
Open → In Progress (assigned) → PR Created → Review → Merged → Closed
```

## 멀티 에이전트 규칙

> 상세: [multi-agent-rules.md](references/multi-agent-rules.md)

- 에이전트 수 무제한 (Task 기반)
- 각 에이전트는 할당된 Issue만 담당
- worktree 격리 필수
- 에이전트 간 파일 충돌 방지

## 상세 문서

- [브랜치 명명 규칙](assets/branch-naming.md)
- [PR 템플릿](assets/pr-template.md)
- [Worktree 사용법](references/git-worktree-guide.md)
- [Issue 생명주기](references/issue-workflow.md)
- [멀티 에이전트 규칙](references/multi-agent-rules.md)
