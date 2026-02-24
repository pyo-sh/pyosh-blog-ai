# 작업 예시

## 시나리오 1: Progress 기록 (작업 완료)

**Issue**: `#42 - 블로그 포스트 카드 컴포넌트 개발`

1. `docs/client/progress.index.md` 읽기 → 최근 작업 확인
2. `progress/progress.2026-02-15.md` 생성 (상세 로그, `#42` 참조)
3. `progress.index.md` 최상단에 한줄 요약 추가

---

## 시나리오 2: Findings 기록 (기술 조사)

**Issue**: `#55 - 포스트 목록 조회 API 구현`

1. `docs/server/findings.index.md` 읽기 → 기존 관련 조사 확인
2. 페이지네이션 전략 조사 (cursor-based vs offset-based)
3. `findings/findings.004-pagination-strategy.md` 생성
4. `findings.index.md`에 항목 추가
5. progress 기록 (시나리오 1과 동일)

---

## 시나리오 3: Decision 기록 (아키텍처 결정)

**Issue**: `#78 - 이미지 스토리지 전략 결정`

1. `docs/server/decisions.index.md` 읽기 → 기존 결정 확인
2. S3 vs Cloudflare R2 vs 로컬 스토리지 조사
3. `decisions/decision-003-image-storage.md` 생성 (상태: **draft**, 옵션 비교 포함)
4. `decisions.index.md`에 항목 추가
5. 사용자에게 결정 요청 → 승인 후 상태를 `accepted`로 변경

---

## 시나리오 4: 병렬 에이전트 (Worktree 격리)

**상황**: Agent A (server progress) + Agent B (client findings) 동시 실행

### Agent A 흐름
1. `git worktree add .claude/worktrees/dev-log-20260224-143022 -b dev-log/20260224-143022 main`
2. worktree 내에서 `docs/server/progress/progress.2026-02-24.md` 작성
3. `git add docs/ && git commit -m "docs: progress - API 엔드포인트 구현"`
4. `mkdir .claude/dev-log.lock` → lock 획득
5. `git rebase main` → `git merge dev-log/20260224-143022 --ff-only`
6. `rmdir .claude/dev-log.lock` → lock 해제
7. `git worktree remove ...` → 정리

### Agent B 흐름 (동시)
1. `git worktree add .claude/worktrees/dev-log-20260224-143025 -b dev-log/20260224-143025 main`
2. worktree 내에서 `docs/client/findings/findings.009-ssr-caching.md` 작성
3. `git add docs/ && git commit -m "docs: findings - SSR 캐싱 전략 조사"`
4. `mkdir .claude/dev-log.lock` → **대기** (Agent A가 lock 보유)
5. Agent A merge 완료 → lock 획득
6. `git rebase main` → main에 Agent A의 변경사항 반영됨
7. `git merge dev-log/20260224-143025 --ff-only` → 성공
8. lock 해제 → 정리

**핵심**: 문서 작성은 병렬, merge만 순차 처리
