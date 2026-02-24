---
name: dev-log
description: pyosh-blog 모노레포에서 progress/, findings/, decisions/ 폴더를 중심으로 진행 상황·기술 조사·아키텍처 결정을 기록하는 문서 관리 스킬. 기록 전용 — 작업 관리는 GitHub Issues에서 수행. 병렬 에이전트 안전: worktree 격리 + lock 기반 merge.
---

# Dev-Log for pyosh-blog

기록 전용 스킬. 작업 관리는 GitHub Issues, 전역 규칙은 `CLAUDE.md` 참조.

**핵심 전략**: worktree 격리 → 인덱스 스캔 → 기록 작성 → lock merge → 정리

## 디렉토리 구조

```
docs/{client|server}/
├── progress.index.md
├── findings.index.md
├── decisions.index.md
├── progress/
│   └── progress.YYYY-MM-DD.md
├── findings/
│   └── findings.NNN-topic.md
└── decisions/
    └── decision-NNN-topic.md
```

## 파일 네이밍

| 유형 | 형식 | NNN/날짜 |
|------|------|----------|
| Progress | `progress.YYYY-MM-DD.md` | ISO 8601 |
| Findings | `findings.NNN-topic.md` | 3자리 순번, kebab-case |
| Decision | `decision-NNN-topic.md` | 3자리 순번, kebab-case |

## 워크플로 (병렬 안전)

> 병렬 에이전트 실행 시 파일 충돌 방지를 위해 **반드시 worktree 격리** 사용.
> 상세 git 명령어: [worktree-merge.md](references/worktree-merge.md)

### Phase 1: Worktree 생성

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_PATH=".claude/worktrees/dev-log-${TIMESTAMP}"
BRANCH_NAME="dev-log/${TIMESTAMP}"
ROOT_REPO="/Users/pyosh/Workspace/pyosh-blog"

cd "$ROOT_REPO"
git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" main
```

이후 모든 파일 작업은 `$WORKTREE_PATH` 내에서 수행.

### Phase 2: 기록 전 컨텍스트 확인
- worktree 내 해당 영역의 `progress.index.md` + `findings.index.md` + `decisions.index.md` 읽기
- 관련 항목만 선택적으로 하위 파일 읽기 (전체 읽기 금지)

### Phase 3: 기록 작성 (worktree 내)
- **기술 조사 시**: `findings/findings.NNN-topic.md` 생성 + `findings.index.md` 갱신
- **아키텍처 결정 시**: `decisions/decision-NNN-topic.md` 작성 (draft) + `decisions.index.md` 갱신
- **작업 완료 시**: `progress/progress.YYYY-MM-DD.md` 생성/업데이트 + `progress.index.md` 갱신
- 폴더/파일 없으면 즉시 생성 ([templates.md](assets/templates.md) 참고)
- 관련 GitHub Issue 번호 포함 (예: `#123`)

### Phase 4: Commit (worktree 내)

```bash
cd "$WORKTREE_PATH"
git add docs/
git commit -m "docs: {type} - {summary}"
```

### Phase 5: Lock → Merge → Unlock

**Lock 획득 → rebase → fast-forward merge → lock 해제** 순서.
다른 에이전트가 lock 보유 시 대기 (최대 60초, 5초 간격 재시도).

```bash
cd "$ROOT_REPO"
# 1. Lock 획득
LOCK_FILE=".claude/dev-log.lock"
while ! mkdir "$LOCK_FILE" 2>/dev/null; do sleep 5; done

# 2. Rebase onto latest main
cd "$WORKTREE_PATH"
git rebase main

# 3. Fast-forward merge
cd "$ROOT_REPO"
git merge "$BRANCH_NAME" --ff-only

# 4. Lock 해제
rmdir "$LOCK_FILE"
```

충돌/실패 시 lock 해제 후 worktree 유지. 상세: [worktree-merge.md](references/worktree-merge.md)

### Phase 6: 정리

- **성공 시**: worktree + 브랜치 삭제
  ```bash
  git worktree remove "$WORKTREE_PATH"
  git branch -d "$BRANCH_NAME"
  ```
- **실패 시**: worktree 유지 (수동 재시도 가능), 에러 메시지 출력

### 인덱스 갱신 규칙
- NNN 순번: 해당 디렉토리 스캔 → 최대 순번 + 1
- progress.index.md: **최상단**에 추가
- 상세: [indexing-strategy.md](references/indexing-strategy.md)

## 참조

- [파일 템플릿](assets/templates.md) — findings, progress, decision 파일 포맷
- [인덱싱 전략](references/indexing-strategy.md) — 인덱스 갱신 규칙, 순번 충돌 방지
- [Worktree Merge 전략](references/worktree-merge.md) — git 명령어 상세, lock 메커니즘, 에러 처리
- [작업 예시](references/examples.md) — 시나리오별 워크플로 (병렬 시나리오 포함)
