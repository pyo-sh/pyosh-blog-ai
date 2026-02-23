# 멀티 에이전트 규칙

## 기본 원칙

1. **에이전트 수 무제한** — Task 기반으로 필요한 만큼 생성
2. **1 에이전트 = 1 Issue** — 각 에이전트는 할당된 Issue만 담당
3. **Worktree 격리 필수** — 에이전트마다 별도의 worktree에서 작업
4. **파일 충돌 방지** — 같은 파일을 수정하는 Issue는 동시 진행 금지

## 동시 작업 가능 조건

| 조건 | 가능 여부 |
|------|-----------|
| 서로 다른 영역 (client/server) | ✅ 가능 |
| 같은 영역, 다른 파일 | ✅ 가능 |
| 같은 파일 수정 | ❌ 순차 처리 |
| 공통 설정 파일 수정 | ⚠️ 주의 필요 |

## Worktree 할당

```
.claude/worktrees/
├── issue-42/    ← Agent A (client: 포스트 카드)
├── issue-55/    ← Agent B (server: 포스트 API)
└── issue-78/    ← Agent C (client: 다크모드)
```

## 충돌 방지 전략

### 1. Issue 할당 시 확인
```bash
# 현재 진행 중인 worktree 확인
git worktree list

# 다른 에이전트가 수정 중인 파일 확인
# (같은 파일을 수정하는 Issue면 대기)
```

### 2. 공유 리소스 수정 시
- `package.json`, `tsconfig.json` 등 공유 설정 파일 수정이 필요하면:
  1. 먼저 해당 파일을 수정하는 다른 worktree가 없는지 확인
  2. 빠르게 수정 후 main에 merge
  3. 다른 worktree에서 `git pull origin main` (rebase)

### 3. 기술 결정 충돌 방지
- 아키텍처 결정이 필요하면 `docs/{area}/decisions/` 에 draft 작성
- 다른 에이전트가 이미 관련 decision을 draft 중이면 대기
- 사용자 승인 후 진행

## 에이전트 식별

각 에이전트는 커밋 메시지에 작업 컨텍스트를 포함:

```
feat: add post card component (#42)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## 에이전트 생성 시 체크리스트

```
- [ ] 할당할 Issue 번호 확인
- [ ] 기존 worktree 목록 확인 (충돌 방지)
- [ ] worktree 생성
- [ ] 작업 시작
```
