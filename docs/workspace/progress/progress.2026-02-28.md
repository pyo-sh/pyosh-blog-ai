# Progress: 2026-02-28

## Completed
- [x] dev-pipeline 스킬에 Pane Lifecycle Tracking 추가
  - `pipeline_pane_alive()` 버그 수정 (`-a` 플래그, `grep -qx` 앵커 매칭)
  - `pipeline_resolve_worktree_path()` 신규 — 현재/레거시 worktree 경로 자동 탐색
  - `pipeline_open_pane_verified()` 신규 — 디렉토리 검증 → pane 열기 → 3초 생존 확인 → 1회 자동 재시도
  - `pipeline_poll_review()` 수정 — optional pane health monitoring 추가 (API 우선 → health 체크)
  - `pipeline_poll_commits()` 신규 — resolve 단계 커밋 polling 함수화 + health check
  - skill.md Steps 2/3/4a/4b 업데이트, Pane Lifecycle 섹션 추가
  - recovery.md에 pane-aware recovery 및 failure diagnostics 추가
- [x] skill-creator 기반 dev-pipeline 스킬 최적화
  - SKILL.md: 237 → 179 lines (-24%)
  - recovery.md: 128 → 91 lines (-29%)
  - 중복 제거, 에러 핸들링 통합, 불필요한 prose 축약

## Discoveries
- tmux pane은 window별 레이아웃 독립 관리 — 다른 window에서 split해도 전환 시 정상 표시
- `tmux list-panes` 기본값은 현재 window만 검색 → `-a` 필수 for cross-window/session
- `grep -q "%1"` → `%10`, `%100`에도 매칭됨 → `grep -qx` 앵커 필요

## Issues & Resolutions
- **Issue**: Pipeline Issue #10 — worktree 경로 불일치로 resolve pane 즉시 소멸
  - state.json에는 monorepo root 기준 경로, 실제 worktree는 레거시(area-specific) 경로에 잔존
  - `cd` 실패 → `&&` 체이닝으로 claude 미실행 → shell 종료 → pane 자동 소멸
  - 오케스트레이터는 pane 사망 미감지, GitHub API만 15분간 polling
- **Resolution**: pane lifecycle tracking 메커니즘 도입 — 검증된 pane 열기 + health-monitored polling + 자동 1회 재시도
