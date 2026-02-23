# Git Worktree 사용법

## 개요

Git worktree는 하나의 리포지토리에서 여러 브랜치를 동시에 체크아웃할 수 있게 해줍니다. 각 worktree는 독립된 작업 디렉토리를 가지므로 멀티 에이전트 작업에 적합합니다.

## 기본 명령어

### Worktree 생성

```bash
# 새 브랜치를 만들면서 worktree 생성
git worktree add -b {branch-name} .claude/worktrees/issue-{N} main

# 예시
git worktree add -b feat/issue-42-post-card .claude/worktrees/issue-42 main
```

### Worktree 목록 확인

```bash
git worktree list
```

### Worktree 제거

```bash
# worktree 제거 (작업 완료 후)
git worktree remove .claude/worktrees/issue-{N}

# 브랜치도 함께 삭제 (merge 완료 후)
git branch -d feat/issue-{N}-{설명}
```

### Worktree 정리 (고아 worktree 제거)

```bash
git worktree prune
```

## 디렉토리 구조

```
pyosh-blog/
├── .claude/
│   └── worktrees/           # ← .gitignore에 등록됨
│       ├── issue-42/        # 각 Issue별 독립 워킹 디렉토리
│       ├── issue-55/
│       └── issue-78/
├── client/
├── server/
└── ...
```

## 주의사항

1. **같은 브랜치를 두 worktree에서 체크아웃할 수 없음**
2. **worktree 내에서 `git checkout`으로 다른 브랜치로 전환 가능** (단, main은 피할 것)
3. **`.claude/worktrees/`는 `.gitignore`에 등록** — 원격에 push되지 않음
4. **worktree에서 push 가능** — 일반 리포지토리처럼 사용

## 워크플로 예시

```bash
# 1. Issue 확인
gh issue view 42

# 2. Worktree 생성
git worktree add -b feat/issue-42-post-card .claude/worktrees/issue-42 main

# 3. Worktree로 이동하여 작업
cd .claude/worktrees/issue-42

# 4. 코딩 & 커밋
git add .
git commit -m "feat: add post card component (#42)"

# 5. Push & PR
git push -u origin feat/issue-42-post-card
gh pr create --title "feat: add post card component (#42)" --body "Closes #42"

# 6. Merge 후 정리 (메인 디렉토리에서)
cd /path/to/pyosh-blog
git worktree remove .claude/worktrees/issue-42
git branch -d feat/issue-42-post-card
```
