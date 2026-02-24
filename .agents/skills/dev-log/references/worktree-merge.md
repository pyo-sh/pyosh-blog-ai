# Worktree Merge 전략

## 개요

병렬 에이전트가 동시에 `docs/` 파일을 수정할 때 충돌을 방지하기 위한 worktree 격리 + lock 기반 merge 전략.

```
Agent A: [worktree 생성] [문서 작성] [commit] [LOCK] [rebase+merge] [UNLOCK] [정리]
Agent B: [worktree 생성] [문서 작성] [commit] ......[LOCK] [rebase+merge] [UNLOCK] [정리]
                                                  ↑ wait
```

## 상수

```bash
ROOT_REPO="/Users/pyosh/Workspace/pyosh-blog"
LOCK_FILE="$ROOT_REPO/.claude/dev-log.lock"
LOCK_TIMEOUT=60   # 초
LOCK_INTERVAL=5   # 초
```

## Phase 1: Worktree 생성

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
WORKTREE_PATH="$ROOT_REPO/.claude/worktrees/dev-log-${TIMESTAMP}"
BRANCH_NAME="dev-log/${TIMESTAMP}"

cd "$ROOT_REPO"
git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" main
```

- `.claude/worktrees/`는 `.gitignore`에 포함됨
- 브랜치명은 timestamp 기반으로 유니크 보장

## Phase 4: Commit

```bash
cd "$WORKTREE_PATH"
git add docs/
git commit -m "docs: {type} - {summary}"
```

- `{type}`: progress, findings, decision 중 하나
- 여러 유형 동시 기록 시: `docs: progress + findings - {summary}`

## Phase 5: Lock → Merge → Unlock

### Lock 획득

`mkdir`은 원자적(atomic) 연산으로, 동시 접근 시 하나만 성공.

```bash
cd "$ROOT_REPO"
ELAPSED=0
while ! mkdir "$LOCK_FILE" 2>/dev/null; do
  ELAPSED=$((ELAPSED + LOCK_INTERVAL))
  if [ "$ELAPSED" -ge "$LOCK_TIMEOUT" ]; then
    echo "ERROR: Lock 획득 타임아웃 (${LOCK_TIMEOUT}초). 다른 에이전트가 merge 중일 수 있음."
    echo "수동 확인: ls -la $LOCK_FILE"
    exit 1
  fi
  echo "Lock 대기 중... (${ELAPSED}/${LOCK_TIMEOUT}초)"
  sleep "$LOCK_INTERVAL"
done
echo "Lock 획득 완료"
```

### Rebase + Merge

```bash
# Rebase: worktree 브랜치를 main 최신 위로
cd "$WORKTREE_PATH"
if ! git rebase main; then
  echo "ERROR: Rebase 충돌 발생"
  git rebase --abort
  cd "$ROOT_REPO"
  rmdir "$LOCK_FILE"  # 반드시 lock 해제
  echo "Lock 해제 완료. Worktree 유지: $WORKTREE_PATH"
  echo "수동 해결 후 재시도 필요"
  exit 1
fi

# Fast-forward merge
cd "$ROOT_REPO"
if ! git merge "$BRANCH_NAME" --ff-only; then
  echo "ERROR: Fast-forward merge 실패"
  rmdir "$LOCK_FILE"  # 반드시 lock 해제
  echo "Lock 해제 완료. Worktree 유지: $WORKTREE_PATH"
  exit 1
fi
```

### Lock 해제

```bash
rmdir "$LOCK_FILE"
echo "Lock 해제 완료. Merge 성공."
```

**중요**: 어떤 경로로든 Phase 5를 벗어날 때 반드시 `rmdir "$LOCK_FILE"` 실행.

## Phase 6: 정리

### 성공 시

```bash
cd "$ROOT_REPO"
git worktree remove "$WORKTREE_PATH"
git branch -d "$BRANCH_NAME"
echo "Worktree 정리 완료: $WORKTREE_PATH"
```

### 실패 시

worktree를 유지하여 수동 재시도 가능:

```bash
echo "Worktree 유지됨: $WORKTREE_PATH"
echo "브랜치: $BRANCH_NAME"
echo ""
echo "재시도 방법:"
echo "  cd $WORKTREE_PATH"
echo "  git rebase main"
echo "  # 충돌 해결 후"
echo "  cd $ROOT_REPO"
echo "  mkdir $LOCK_FILE && git merge $BRANCH_NAME --ff-only && rmdir $LOCK_FILE"
echo "  git worktree remove $WORKTREE_PATH && git branch -d $BRANCH_NAME"
```

## Stale Lock 처리

Lock이 비정상적으로 남아있는 경우 (에이전트 크래시 등):

```bash
# lock 디렉토리 확인
ls -la "$LOCK_FILE"

# 다른 에이전트가 사용 중이 아님을 확인한 후 수동 해제
rmdir "$LOCK_FILE"
```

## 에이전트 구현 시 주의사항

1. **모든 파일 경로는 worktree 기준**: `$WORKTREE_PATH/docs/...` 에서 작업
2. **Read/Write/Edit 도구 사용 시 절대 경로**: worktree 내 절대 경로 사용
3. **Lock 구간 최소화**: commit까지 마친 후 lock 획득
4. **에러 시 반드시 lock 해제**: try-finally 패턴으로 구현
5. **인덱스 순번은 worktree 생성 시점 기준**: rebase 후 충돌 시 순번 재확인 필요
