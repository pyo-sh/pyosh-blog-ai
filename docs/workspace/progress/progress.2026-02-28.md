# Progress: 2026-02-28

## Completed
- [x] Docker 컨테이너 Claude Code를 native installer로 전환
  - Dockerfile: `npm install -g @anthropic-ai/claude-code` → `curl -fsSL https://claude.ai/install.sh | bash` (USER dev 이후 실행)
  - `.bash_aliases`: `dev-update()` 내 Claude Code 업데이트를 native installer 재실행으로 변경
  - `ARCHITECTURE.md`: Dockerfile 설명 반영
  - 효과: 시작 시 npx 경고 메시지 제거, 자동 백그라운드 업데이트 지원
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
- [x] CLAUDE.md Task Rules repo별 분리 및 스킬 중복 제거
  - root CLAUDE.md: Task Rules를 client/server(Issue-driven)와 root repo(사용자 지시 기반)로 분리
  - 스킬(`/dev-build`, `/dev-pipeline`)이 내장한 브랜치/커밋/PR 네이밍 규칙을 CLAUDE.md에서 제거 (92줄 → 89줄)
  - Git Workflow → Git Rules로 슬림화, Multi-Agent 규칙 한 줄로 통합
  - root repo 워크플로우 추가: worktree 네이밍 `{type}-{description}`, 로컬 merge 또는 PR 선택 가능
  - client/server CLAUDE.md: Workflow 섹션을 `/dev-pipeline` 직접 참조로 변경
  - 3개 repo 동시 PR 생성 및 merge (pyosh-blog-ai#3, pyosh-blog-fe#20, pyosh-blog-be#23)

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
