# Progress 2026-03-13

## dev-pipeline: log → merge 순서 변경 (#164, PR #165)

- **문제**: dev-pipeline 상태 머신이 `merge → log → done` 순서로 실행되어, dev-log가 standalone 모드의 `lock_merge`로 local main에 커밋하지만 push하지 않음. 다음 PR squash merge 시 origin/main과 발산하여 `ff-only` 실패 100% 재현
- **해결**: 상태 머신 순서를 `log → merge → done`으로 변경
  - dev-log가 issue worktree에서 실행되어 `inRootWorktree: true` 경로를 타고 PR branch에 push
  - `lock_merge`(Phase 5)를 완전히 우회하여 local-only 커밋 원천 차단
- **변경**: SKILL.md state machine, `steps.py` 전이 변경(`step_log_setup` 추가, `step_merge` cleanup 통합), `cli.py` dispatch table
- **리뷰 피드백**: `push_safely` 반환값 미검사 경고 수정, `log_transition` audit trail 추가
- 2라운드 리뷰, PR #165 squash merge 완료

## orchctl CLI skeleton + SQLite schema (#85, PR #167)

- **목적**: Stage 2 오케스트레이터 재설계의 기반 - Python 기반 `orchctl` CLI와 WAL+FK SQLite 데이터베이스
- **구현**: `tools/orchctl/` 패키지 신규 생성
  - Click CLI 진입점: `init`, `status`, `doctor`, `reconcile` (stub) subcommands
  - SQLite schema v1: `issues`(CHECK constraints), `attempts`, `heartbeats`, `leases`, `config` + `issues_updated_at` 트리거
  - 마이그레이션 러너: idempotent DDL(`IF NOT EXISTS` / `ON CONFLICT DO NOTHING`), `current_version()` 공개 API
  - FK 인덱스: `idx_attempts_issue_id`, `idx_heartbeats_attempt_id`
  - `status`/`doctor`는 uninit DB에서 `ClickException` 발생, try/finally로 connection 보장 해제
- **테스트**: 16개 tests (DB 초기화, schema, CRUD, 멱등성, CLI 명령, doctor dirty-data 탐지)
- **리뷰**: 5라운드 - `_current_version` 공개 API 승격, heartbeats FK 인덱스, `check_same_thread=False` 제거, `run_migrations()` hardcoded constant 수정, try/finally 패턴, 탐지 테스트 추가
- PR #167 5라운드 리뷰 resolve 완료

## dev-log detect-context area 검증 (#164, PR #166)

- **문제**: `detect-context`가 `.workspace/worktrees/` 하위 경로만으로 `inRootWorktree: true` 판단하여 client/server worktree에서 false positive 발생. dev-log가 client/server PR branch에 docs를 혼입할 위험
- **해결**: worktree의 `.git` 파일에서 `gitdir:` 경로를 읽어 root repo에 속하는지 검증
  - `_find_worktree_root()`: nested path에서 `.git` 파일이 있는 worktree root 탐색
  - `_is_root_repo_worktree()`: gitdir 경로가 `{root_repo}/.git/` 하위인지 확인
- **테스트**: client/server false positive, no `.git` file 케이스 등 7개 테스트, 전체 25개 pass
