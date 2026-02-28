# Progress: 2026-02-28

## Completed
- [x] Fix Docker auth volume symlink failure with native Claude Code installer
  - `Dockerfile`: `rm -rf ~/.claude ~/.claude.json` after install to prevent stale image layer directory
  - `entrypoint.sh`: defensive removal of real dirs/files before symlink creation
  - `entrypoint.sh`: 3rd `elif` branch to auto-correct stale `statusLine.command` path
  - `entrypoint.sh`: fixed heredoc single-quote preventing `$STATUSLINE_CMD` interpolation
- [x] Add worktree-first enforcement rule to CLAUDE.md
  - Added IMPORTANT block: any file edit must be preceded by worktree creation
- [x] Translate CLAUDE.md to English + add post-commit stop rule
  - Full English translation of all Korean prose
  - Added IMPORTANT block: always stop and ask user after commit (never auto-merge)
- [x] Issue 템플릿 개편 및 priority 라벨 5단계 축소 (3개 repo 동시 적용)
  - ISSUE.md 삭제, bug/feature/refactor.yml 신규 추가
  - 공통 필드 통일: Area dropdown(client/server/workspace), Scope, Definition of Done, Priority(required)
  - 템플릿별 특성 유지: bug(Symptom/Logs/Cause/Solution), feature(Goal/Context/Requirements/Tech), refactor(Problem/Improvement)
  - label 영어화 (Goal, Symptom, Problem 등), description/placeholder는 한국어 유지
  - priority 8단계(priority:0~7) → 5단계(priority:0~4: Critical/High/Medium/Low/Backlog)
  - labels.json 동기화 (3개 repo 동일)
  - client/server 기존 이슈 priority 라벨 마이그레이션 (client 15건, server 11건)
  - 3개 repo 동시 PR 생성 및 merge (pyosh-blog-ai#4, pyosh-blog-fe#21, pyosh-blog-be#24)
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

- [x] dev-issue 스킬 리비전
  - 입력 소스 확장: decisions 전용 → decisions + plans + user direct request
  - decisions 상태 검사(Status 기반 분류) 유지
  - 이슈 포맷: 하드코딩된 마크다운 템플릿 → 각 repo의 `.github/ISSUE_TEMPLATE/*.yml` 참조로 변경
  - `references/priority-guide.md` 삭제 (0-7 체계가 ISSUE_TEMPLATE의 0-4와 불일치)
  - skill-creator 기반 구조 최적화: description 트리거 강화, 중복 제거, 84행 → 52행 (-38%)
- [x] brainstorming + writing-plans 스킬 경로 및 구조 개선
  - brainstorming: design doc 출력 경로 `docs/plans/` → `docs/workspace/decisions/`
  - writing-plans: 플랜 저장 경로 `docs/plans/` → `docs/{area}/plans/`
  - writing-plans: 실행 핸드오프(subagent/manual) → `/dev-issue` 즉시 실행 or decisions 분리 선택지로 교체
  - writing-plans: skill-creator 기반 최적화 195행 → 121행 (-38%)

- [x] Feature Spec v1 리비전 + Implementation Plan → GitHub Issues 마이그레이션
  - `docs/client/feature_spec.md` 서버 API 대조 검토 후 리비전 (12건 인터뷰 Q&A 반영)
  - Phase 1-4 client implementation plans 작성 (`docs/client/plans/`)
  - Server v1 API status 문서 작성 (`docs/server/plans/v1-api-status.md`)
  - 48개 decision files → GitHub Issues 변환 (pyo-sh/pyosh-blog-fe #23-#70)
    - Phase 1 Core (priority:1): 15 issues — Post, Pagination, Markdown, Category
    - Phase 2 Admin (priority:1): 12 issues — CSRF, Auth, Dashboard, Editor
    - Phase 3 Public (priority:2): 10 issues — Comments, Guestbook, Tags, Popular, View Count
    - Phase 4 Extras (priority:3): 11 issues — Category Admin, Assets, SEO, Search
  - 기존 client issues #5-#18 close + delete (새 plan으로 대체)
  - 중복 issues #71-#117 삭제
  - Server issue pyo-sh/pyosh-blog-be#26 생성 (v1 API 상태 문서화, priority:2)
  - plan/decision files 정리 삭제 후 커밋

- [x] Standardize labels.json + PR template + CLAUDE.md across 3 repos
  - labels.json: removed emojis, lowercase names, all English descriptions
  - Renamed ambiguous labels: HEY→attention, ASK→question, CLEANING→refactor
  - GitHub remote labels updated via `gh label edit` (rename preserves existing issue associations)
  - Root repo: deleted legacy priority:5-7 labels from remote
  - PR template: structured sections (Summary, Changes table, Type checkbox, Author Korean checklist, Reviewer English checklist, Screenshots, Notes)
  - server/client CLAUDE.md: translated remaining Korean (Workflow section) to English
  - Root: local merge + push, Server: PR #25 merged, Client: PR #22 merged
  - Deleted `.workspace/handoffs/handoff_templates.md` (completed handoff)

## Discoveries
- **Native installer creates `~/.claude` as a real directory** at Docker build time. `ln -sfn` silently fails to replace a real directory, breaking the auth volume symlink. `npx` did not have this issue.
- **CLAUDE.md workflow rules have no enforcement mechanism** — they rely on AI judgment. Ambiguous phrasing ("user choice") was treated as optional; making it an explicit IMPORTANT block reduces the chance of skipping.
- tmux pane은 window별 레이아웃 독립 관리 — 다른 window에서 split해도 전환 시 정상 표시
- `tmux list-panes` 기본값은 현재 window만 검색 → `-a` 필수 for cross-window/session
- `grep -q "%1"` → `%10`, `%100`에도 매칭됨 → `grep -qx` 앵커 필요

## Issues & Resolutions
- **Issue**: Pipeline Issue #10 — worktree 경로 불일치로 resolve pane 즉시 소멸
  - state.json에는 monorepo root 기준 경로, 실제 worktree는 레거시(area-specific) 경로에 잔존
  - `cd` 실패 → `&&` 체이닝으로 claude 미실행 → shell 종료 → pane 자동 소멸
  - 오케스트레이터는 pane 사망 미감지, GitHub API만 15분간 polling
- **Resolution**: pane lifecycle tracking 메커니즘 도입 — 검증된 pane 열기 + health-monitored polling + 자동 1회 재시도
