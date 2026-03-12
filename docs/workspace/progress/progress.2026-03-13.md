# Progress 2026-03-13

## dev-pipeline: log → merge 순서 변경 (#164, PR #165)

- **문제**: dev-pipeline 상태 머신이 `merge → log → done` 순서로 실행되어, dev-log가 standalone 모드의 `lock_merge`로 local main에 커밋하지만 push하지 않음. 다음 PR squash merge 시 origin/main과 발산하여 `ff-only` 실패 100% 재현
- **해결**: 상태 머신 순서를 `log → merge → done`으로 변경
  - dev-log가 issue worktree에서 실행되어 `inRootWorktree: true` 경로를 타고 PR branch에 push
  - `lock_merge`(Phase 5)를 완전히 우회하여 local-only 커밋 원천 차단
- **변경**: SKILL.md state machine, `steps.py` 전이 변경(`step_log_setup` 추가, `step_merge` cleanup 통합), `cli.py` dispatch table
- **리뷰 피드백**: `push_safely` 반환값 미검사 경고 수정, `log_transition` audit trail 추가
- 2라운드 리뷰, PR #165 squash merge 완료

## docs branch git strategy (#168, PR #169)

- **목적**: dev-log 커밋이 main에 직접 노이즈를 만들지 않고, 배치 관리가 가능한 구조로 전환
- **Phase A - dev-log 재작성**:
  - `context.py`/`test_context.py` 삭제 (worktree 감지 불필요)
  - `git_ops.py`: `push_to_docs`, `branch_exists_remote`, `create_branch_from` 추가
  - `worktree.py`: base를 `docs`로 변경, `ensure_docs_branch()` 추가
  - `merge.py`: `lock_merge` -> `merge_to_docs` (origin/docs에 rebase 후 push)
  - `cli.py`: `detect-context`/`push` 제거, `ensure-branch`/`merge-to-docs` 추가
  - SKILL.md: 7단계 선형 워크플로우로 재작성
- **Phase B - dev-archive 신규 스킬**: `check-diff`, `ensure-label`, `create-pr`, `squash-merge`, `sync-branch` 5개 CLI 서브커맨드
- **Phase C - pipeline 상태 머신 재배치**: merge -> log 순서로 변경, `step_merge`는 log로 전이, `step_log_finalize`에서 cleanup + done 반환
- 24 tests pass, 1라운드 리뷰 (WARNING 1 + SUGGESTION 1 수정)

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

## dev-pipeline 4개 버그 수정 (#170, PR #171)

- **배경**: PR #167 (issue #85) 파이프라인 5라운드 실행 중 실증 확인된 4개 버그를 handoff 문서로 인수받아 수정
- **Bug 1 (Critical) - review-wait pending 분기 누락**:
  - task-notification 도착 시 `claude -p` 프로세스는 아직 RUNNING → GitHub에 review 없음 → 최하단 fallthrough `escalate`
  - `_FAILED_STATUSES` 체크 이후 `RUNNING` 분기를 추가하여 `action="pending"` 반환, SKILL.md 테이블에 `pending` 행 추가
  - 결과: 매 리뷰 라운드마다 수동 개입 필요하던 문제 해소, 파이프라인 자동화 복원
- **Bug 2 (Medium) - suggestion_only round 카운터 미증가**:
  - `suggestion_only` 경로에서 `round_num` 그대로 반환하여 실제 회차와 불일치 (2회차→1 반환, 5회차→4 반환)
  - `"round": round_num` → `"round": round_num + 1` 수정 (state 업데이트는 `suggestion_decide`에서 유지)
- **Bug 3 (Medium) - review_normalizer 들여쓰기 오파싱**:
  - `stripped` 기준 `^\d+\.` 매칭으로 들여쓰인 번호 하위 목록을 최상위 항목으로 카운트
  - 원본 `line`으로 들여쓰기 체크 (`not line.startswith((" ", "\t"))`) 조건 추가
- **Bug 4 (Low) - suggestion_only data에 reviewBody 없음**:
  - AI 결정에 리뷰 내용이 필요하지만 counts만 반환하여 `resolve --phase setup` 우회 필요
  - suggestion_only data에 `"reviewBody": body` 추가
- **회귀 테스트**: 4개 신규 테스트 추가 (264 → 268 passed)
- 1라운드 리뷰, 클린 통과, PR #171 머지 완료

## dev-log detect-context area 검증 (#164, PR #166)

- **문제**: `detect-context`가 `.workspace/worktrees/` 하위 경로만으로 `inRootWorktree: true` 판단하여 client/server worktree에서 false positive 발생. dev-log가 client/server PR branch에 docs를 혼입할 위험
- **해결**: worktree의 `.git` 파일에서 `gitdir:` 경로를 읽어 root repo에 속하는지 검증
  - `_find_worktree_root()`: nested path에서 `.git` 파일이 있는 worktree root 탐색
  - `_is_root_repo_worktree()`: gitdir 경로가 `{root_repo}/.git/` 하위인지 확인
- **테스트**: client/server false positive, no `.git` file 케이스 등 7개 테스트, 전체 25개 pass
