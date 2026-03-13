# Progress 2026-03-13

## Skill Python 호출 경로 + 부수 버그 5건 수정 (#181, PR #182)

- **목적**: dev-pipeline 실행 중 반복 발생한 5가지 오류 수정
- **Bug A-1** - 패키지 모듈 경로: `cd ... && python3 -m <pkg>` 패턴에서 에이전트가 `cd` 누락 시 `No module named` 오류. CLI hint를 `PYTHONPATH=$MONOREPO_ROOT/...` 방식으로 변경, MONOREPO_ROOT 판단 방법 명시 (headless: `$PIPELINE_MONOREPO_ROOT` / interactive: `monorepo-helpers.sh`). dev-archive, dev-log, dev-pipeline SKILL.md + references 적용
- **Bug A-2** - 상대경로 standalone 스크립트: dev-build, dev-resolve SKILL.md의 `python3 .agents/...` 상대경로를 `$MONOREPO_ROOT/...` 절대경로로 변경
- **Bug B** - `step review-dispatch --model` 미지원: `cli.py` p_step에 `--model` 인수 추가, `steps.py` `step_review_dispatch()` 시그니처에 `model` 파라미터 추가, dispatch action data에 `model` 포함
- **Bug C** - `gh issue view` exit 1: GitHub Projects (classic) deprecated 오류. dev-pipeline, dev-build SKILL.md Invariants에 `--json number,title,body,state,labels` 필수 제약 추가
- **Bug D** - worktree 제거 실패 pipeline crash: `merge → log` 구조에서 `merge → cleanup_wt → log → finalize` 3단계로 분리. `controller.py`에서 `cleanup()` → `cleanup_worktree()` + `cleanup_state()` 분리, `models.py`에 `CLEANUP_WT` step 추가, `steps.py`에 `step_cleanup_wt()` 추가
- **Bug E** - codex review_runner 데드코드: `schema_path` 변수 삭제 (`codex exec review`는 `--output-schema` 미지원), `_fail_parse()`에 `raw_content` 파라미터 추가하여 파싱 실패 시 원본 출력 snippet stderr 기록
- **SKILL 압축 최적화**: PYTHONPATH prefix 18회 반복 → CLI hint 1회 + "Prepend" 지시 1줄로 압축 (dev-pipeline, dev-archive, dev-log). process-lifecycle.md에 `cleanup-wt` single-call 등록
- **테스트**: `test_steps.py` 업데이트 - merge→cleanup_wt 전이, step_cleanup_wt coverage, log_finalize cleanup_state 분리. 47 tests pass
- 1라운드 리뷰 (CRITICAL 1 - 테스트 미갱신), resolve 후 merge 완료

## 확장 terminal states + claim/hold 라벨 (#91, PR #179)

- **목적**: orchestrator 상태 머신에 신규 terminal state 4종 추가 + GitHub issue 라벨 자동 관리
- **구현**:
  - `orchestrate-helpers.sh`: `failed-terminal`, `needs-human`, `needs-spec`, `cancelled` 신규 terminal state 추가
  - `orchestrate-helpers.sh`: `orch_set_terminal()` 래퍼 신규 - 단일 진입점으로 상태 설정 + issue 라벨 side-effect 처리
  - `orchestrate-helpers.sh`: `orch_issue_add_label()` / `orch_issue_remove_label()` / `orch_issue_post_comment()` 신규 - best-effort issue 라벨 관리 (bare gh 사용, provider health 비관여)
  - `orchestrate-helpers.sh`: `orch_check_manual_hold()` 신규 - dispatch 전 `manual-hold` 라벨 체크 (orch_gh 사용, provider health 관여)
  - `orchestrate-helpers.sh`: `orch_dispatch()` - dispatch 전 `manual-hold` 체크 추가, 성공 시 `claimed-by-orch` 라벨 부착
  - `orchestrate-helpers.sh`: `orch_set_terminal()` - `claimed-by-orch` 제거는 dispatched 맵 확인 후 실행 (never-dispatched 이슈의 불필요한 API 호출 방지)
  - `orch_unblock()` / `_orch_mark_failed_and_unblock()` / `orch_poll_cycle()` - `orch_status_set` → `orch_set_terminal` 전환
  - `state-detection.md`: 상태 머신 다이어그램 업데이트, GitHub issue 라벨 관리 섹션 신규
  - `dependency-resolution.md`: terminal non-completed statuses 목록 업데이트
- **라벨 정책**: `claimed-by-orch`(dispatch 시 부착/terminal 시 제거), `needs-human`(전이 시 부착 + 코멘트), `needs-spec`(전이 시 부착), `manual-hold`(human이 설정 - orchestrator skip)
- **결과**: 1라운드 warning(never-dispatched API 호출 최적화) → fix, 2라운드 suggestion-only → skip, merge

## Agent tracker writer contract alignment (#110, PR #180)

- **목적**: agent-tracker hooks/writer/reader 계약을 sidecar v2 schema와 일관되게 강화
- **구현**:
  - `hooks/on-status.sh`: task(UserPromptSubmit) 및 key_arg(PreToolUse) 처리 시 ANSI CSI/OSC/ESC 시퀀스 제거 3단계(`\\u001b\\[...[A-Za-z]` → `\\u001b]...\\u0007` → `\\u001b.`) 추가, 기존 `[[:cntrl:]]` strip 이전에 수행
  - `hooks/on-statusline.sh`: model fallback을 `"Claude"` 하드코딩 → `$existing.model // "unknown"` 조건부 보존으로 변경; `tokens_updated_at`는 `$used_tokens > 0`일 때만 갱신하여 토큰 데이터 없는 경우 허위 freshness 방지
  - `statusline-wrapper.sh`: `TRANSCRIPT_LAST_MSG` jq 파이프라인에 ANSI/OSC sanitization 추가
  - `lib/collect.sh`: model reader fallback `"Claude"` → `"unknown"` (default 및 jq fallback 모두)
  - `setup.sh`: sidecar directory 출력을 v2 namespace 형식으로 업데이트; v1 flat sidecar 파일(`.workspace/agent-tracker/*.json`) 자동 마이그레이션 추가
  - `.agents/skills/dev-pipeline/scripts/dev_pipeline/models.py`: `issue` 필드 로드 시 `int(d.get("issue") or 0)`으로 정규화 - 구 bash 기반 writer가 생성한 string 타입("30") → int 타입(30) 자동 변환
- **결과**: review clean (critical 0, warning 0, suggestion 0), 1라운드 통과

## Hard/soft dependency + cross-area policy (#90, PR #176)

- **목적**: dev-orchestrator Stage 2 - dependency 유형을 hard/soft로 구분하고 cross-area 및 SCC cycle 격리 정책 정의
- **구현**:
  - `parse-dependencies.sh`: `--parse-typed` 모드 신규 (fenced orchestrator 블록 우선 파싱, `### Dependencies` fallback) - JSON 반환 `{hard:[...], soft:[...], crossArea:[...]}`
  - `parse-dependencies.sh`: `--find-sccs` 모드 신규 - BFS 기반 정확한 SCC cycle 노드 검출 (downstream 의존 노드 미포함)
  - `orchestrate-helpers.sh`: `orch_init` SCC 격리(`cycle-isolated` 상태 부여, 배치 전체 abort 대신), `dagTypes`/`crossAreaDeps` 상태 필드 추가, cross-area hard dep -> `blocked-external` 초기화
  - `orchestrate-helpers.sh`: `orch_unblock` dep-type-aware 분기 - hard dep 실패 -> `blocked-failed-dependency`, soft dep 실패 -> `pending`, cross-area hard dep -> `blocked-external`
  - 신규 terminal 상태: `blocked-failed-dependency`, `blocked-external`, `cycle-isolated` (`orch_doctor` 검증 포함)
  - `orch_init` 선택적 파라미터 6번/7번으로 backward compat 유지 (`skipped_dep_failed` legacy 유지)
- **Fenced block 형식**: ````orchestrator` 블록 - `hard:`, `soft:`, `cross-area:`, `cross-area soft:` 라인
- **테스트**: `test-dep-policy.sh` 25개 - mock `gh`로 실제 `--parse-typed` 호출, `orch_unblock` 통합 6케이스, `--find-sccs` cycle 격리 검증
- **리뷰 수정**: doc 예제 `issues_json` 루프 전 선언 오류 수정, test 1 inline jq → 실제 스크립트 호출, 테스트 5-7 `orch_unblock` 통합 테스트로 교체
- 2라운드 리뷰, PR #176 머지 완료

## orchctl leader lease + dispatch idempotency (#87, PR #173)

- **목적**: 다중 프로세스 환경에서 reconcile 루프 중복 실행 방지 및 attempt 중복 dispatch 차단
- **schema migration v3**:
  - `ALTER TABLE leases ADD COLUMN heartbeat_at TEXT` (simple ALTER TABLE - atomic, no intermediate state)
  - `CREATE UNIQUE INDEX IF NOT EXISTS idx_attempts_active_unique ON attempts(issue_id) WHERE status = 'running'` (partial unique index)
  - migration 번호 v3으로 변경 - PR #172(issue #85 follow-up)가 main에 먼저 merge되어 v2 충돌 발생, origin/main 합병 후 재번호화
- **`orchctl/db/lease.py` 신규 모듈**: `acquire` / `renew` / `release` / `cleanup_stale` / `has_active_attempt`
  - `_utcnow()`: SQLite `datetime()` 출력과 일치하도록 `"%Y-%m-%d %H:%M:%S"` 공백 구분자 사용 (ISO T-format 아님)
  - `_pid_alive()`: `PermissionError` → alive(프로세스 존재, signal 권한 없음), `ProcessLookupError` → dead
  - `acquire()`: `cleanup_stale()` 후 `conn.commit()` 호출 - IntegrityError rollback이 cleanup 삭제를 되돌리지 않도록
  - `cleanup_stale()`: commit 미포함 - caller 책임. expiry는 atomic SQL DELETE, dead-PID는 `(area, holder_pid, expires_at)` 정밀 predicate
- **reconcile 커맨드**: area 리스 취득 후 진입, version guard(스키마 버전 미달 시 ClickException), 이슈별 renew, 리스 분실 시 abort
- **테스트**: 41개 신규 (test_lease.py 17개 + test_cli.py 업데이트), v2 vocabulary 적용(`state='pending'`, `status='completed'`/`'failed'`)
- **리뷰 8라운드**: migration 멱등성, cleanup_stale TOCTOU, version guard, datetime format, commit 책임 분리, schema vocabulary 호환

## dev-pipeline/dev-log 파이프라인 안정성 버그 10건 수정 (#177, PR #178)

- **범위**: dev-pipeline 실행 중 실증 확인된 10개 버그 - issue #87, #109 파이프라인에서 각각 수동 개입 필요
- **Bug A (High)** - dev-log rebase 오류: `worktree.py:create_worktree()`의 `base="docs"` (로컬 브랜치)가 `origin/docs`와 gap이 생겨 checkout 거부. `base="origin/docs"`로 변경하여 fetch된 remote ref에서 직접 분기
- **Bug B (High)** - `failed_postcondition` 폴백 부재: `step_review_wait`에서 `FAILED_POSTCONDITION` 전용 분기가 없어 무조건 escalate. `_FAILED_STATUSES` 체크 앞에 전용 retry 블록 추가. 단, Bug D(dispatch reset)와의 상호작용으로 `"review_postcondition"` 전용 stage key 사용하여 무한 루프 방지
- **Bug C (Medium)** - merge conflict 진단 부족: `git_ops.py`에 `get_conflict_files()` 헬퍼 추가, `controller.py`에 `MergeConflictError` 클래스 도입, `step_merge()` retry/escalate data에 `errorKind` + `conflictFiles` 포함
- **Bug D (Medium)** - `stageRetries` 라운드 간 이월: `step_review_dispatch()`에서 `review_wait` 전이 시 `stageRetries["review_dispatch"]`를 0으로 리셋. `state_update`의 deep merge 특성 활용하여 다른 stage 카운터 유지
- **Bug E (Medium)** - `round_limit` 복구 경로 없음: `models.py`에 `round_limit_reached_at` 필드 추가, `step_review_process()`에서 round_limit 반환 시 state에 타임스탬프 기록
- **Bug F+G (Medium/Low)** - dispatch cwd 누락 + review-wait 의무 미명시: SKILL.md Step 2a dispatch 명령에 `cd .agents/skills/dev-pipeline/scripts &&` 추가, Step 2b 헤더를 `(call unconditionally on any task-notification)`으로 변경
- **Bug H (Low)** - approve verdict 시 publish 미호출: dev-review SKILL.md Invariants에 "All verdicts publish" 규칙을 Invariant 3으로 추가
- **Bug I (Medium)** - `pr_helpers.py` `--head` 미지정: `gh pr create -R {repo}` 호출 시 브랜치 자동 감지 실패. `cmd_create()`에 optional `--head` 인자 추가
- **Bug J (Low)** - `gh` CLI 버전 미갱신: `tools/docker/.bash_aliases` `dev-update()`에 `[2/5] GitHub CLI (gh)` 업그레이드 단계 추가, 전체 단계 [N/5]로 갱신
- **파이프라인 실행 중 추가 발견**: `step_resolve_finalize()`가 staged changes 없을 때 push를 건너뛰어 remote가 구버전을 보는 문제. `push_safely()`를 if 블록 밖으로 이동하여 항상 push 보장
- **3라운드 리뷰**: round 1 - B/D 상호작용 infinite loop Critical 발견 및 수정, round 2 - 이미 수정된 커밋 기준 (push 타이밍 버그로 구버전 리뷰), round 3 - clean 통과
- PR #178 squash merge 완료

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

## orchctl core state machine Python 이전 + 기본 테스트 (#86, PR #172)

- **목적**: issue lifecycle과 attempt tracking의 핵심 상태 전이 로직을 Python으로 이전하고, 기본 테스트 작성 (Stage 2)
- **구현**: `tools/orchctl/` 2개 모듈 + schema migration v2
  - `models.py`: `IssueState`/`AttemptStatus`/`DependencyType` str enums, `ISSUE_TRANSITIONS`/`ATTEMPT_TRANSITIONS` frozenset 맵, `TERMINAL_*` 집합
  - `state_machine.py`: `InvalidTransitionError`/`StaleStateError` 예외 클래스, `transition_issue`/`transition_attempt`(pure), `resolve_blocked_issue`(dep 타입별 분기), `try_acquire_lease`(DELETE + INSERT ON CONFLICT DO UPDATE WHERE), `release_lease`, `can_dispatch`, `apply_issue_transition`/`apply_attempt_transition`(optimistic-lock predicate)
  - `db/schema.py` migration v2: `issues` 상태 어휘 확장(pending/dispatched/completed/failed-terminal/needs-human/blocked-external/cancelled/blocked/blocked-failed-dependency), `attempts` 상태 어휘 교체(created/running/completed/failed/timed-out), 데이터 마이그레이션(running→dispatched, done→completed 등), `idx_issues_state` 인덱스 추가
- **테스트**: `tests/test_state_machine.py` 신규 - 93 tests pass 전체 (90 state machine)
  - issue/attempt 전이 유효성(모든 edge), 잘못된 전이 거부, `StaleStateError` vs `InvalidTransitionError` 구분
  - `resolve_blocked_issue`: soft/hard dep, NEEDS_HUMAN/BLOCKED_FAILED_DEP 포함 모든 terminal state
  - `apply_*_transition` DB-backed optimistic-lock, 누락 row ValueError
  - `can_dispatch` 상태별 eligibility, 중복 dispatch 방지
  - Reconcile idempotency (3회 반복 안정), golden-path integration (register→dispatch→complete→unblock)
  - Lease conflict: acquire/renew/release/expire/다중 area 독립성
- **리뷰 주요 수정 (5라운드)**:
  - R1: `has_failure` NEEDS_HUMAN 누락(hard dep → 모든 non-completed terminal을 failure로 처리), `INSERT OR IGNORE` → renewal 지원 upsert
  - R2: `apply_*_transition` non-atomic SELECT+UPDATE → `WHERE ... AND state=?` predicate + rowcount 체크, `idx_issues_state` 인덱스 추가
  - R3: terminal state comment에 deferred retry path 명시(retry_budget 컬럼 예약), UPSERT CASE ELSE dead branch 제거
  - R4: `StaleStateError` 신규 예외 클래스(optimistic-lock race용), `conn` fixture `return` → `yield` + `conn.close()` teardown
  - R5: suggestion_only (1-line doc) → auto-merge
- PR #172 5라운드 리뷰 resolve 완료, squash merge

## Agent tracker Bash safety hotfix (#108, PR #174)

- **목적**: Bash tracker의 운영상 오판을 줄이기 위한 최소 범위 correctness hotfix (live 버그 6개 수정)
- **Bug 1 - @tsv 필드 밀림**: `IFS=$'\t' read`는 bash whitespace-IFS 규칙으로 연속 탭을 하나로 축소. `activity`가 비어 있으면 `updated_at`이 `activity` 열에 노출. `join("\u001e")` + `IFS=$'\x1e'`(비공백 구분자) + `@base64`(task/activity)로 교체
- **Bug 2 - dead orchestrator 은닉**: `_check_pid_alive || continue`로 죽은 배치가 완전 숨겨짐. `batch_alive=false` 추적으로 변경, `batch_status="dead"` 설정 후 ROSE 색상 + `[DEAD]` 레이블로 표시
- **Bug 3 - 토큰 0/0 source 오표시**: 사이드카 존재하지만 토큰 미기록 시 `source=sidecar, fresh=true` 표시. `tok_used==0 && tok_total==0`이면 `tok_source="unknown"` 설정
- **Bug 4 - done 태스크 working으로 오표시**: `_infer_status_from_pane` 스피너 감지가 `(Done) ` prefix 확인보다 먼저 실행되어 `idle→working` 덮어씀. `(Done) ` prefix 확인을 무조건적(status 조건 제거)으로 변경
- **Bug 5 - pane_id 경로 탐색 취약점**: `pane_id`를 직접 파일 경로에 사용. `^%[0-9]+$` 형식 검증 guard 추가
- **Bug 6 - stale/fault/dead/unknown idle 혼입**: stale(갱신 초과 비idle) → `status="stale"`, 파싱 실패 → `status="fault"`, done은 staleness 체크 제외. `n_stale` 카운터 분리, `status_badge`에 `stale`(GOLD)/`fault`(ROSE) 추가
- 클린 리뷰 통과(0/0/0), PR #174 머지 완료

## agent-tracker: sidecar v2 contract + immediate cutover (#109, PR #175)

- **목적**: sidecar JSON schema를 v2로 업그레이드하고 namespace를 multi-server/multi-session 안전 구조로 변경
- **신규 필드**: `schema_version: "v2"`, `session_name` (tmux session 이름), `tmux_server` (소켓 경로)
- **namespace 변경**: `.workspace/agent-tracker/{pane_id}.json` - `.workspace/agent-tracker/<socket-hash>/<session>/<pane>.json`
  - `socket-hash`: `$TMUX` 소켓 경로의 MD5 앞 6자 - 다중 tmux 서버 충돌 방지
  - `session`: tmux session 이름 (예: `lab`)
  - `pane`: pane id % prefix 제거 (예: `5`)
- **즉시 cutover**: `agent-tracker.sh` 시작 시 v1 flat 파일(`SIDECAR_DIR/*.json`) 자동 정리
- **reader 업데이트**: `collect.sh`에서 socket hash + session 계산 후 v2 경로로 sidecar 조회. source precedence 문서화 추가
- **리뷰 피드백 수정**: `_pid` unset 누락 수정, `md5sum` Linux-only 주석 추가, 활성 세션 orphan 삭제 테스트 신규 추가 (4 - 6개)
- **병렬 수정**: origin/main에 #108 변경(path traversal guard, `status: "stale"/"fault"` 신규, base64 인코딩)이 선반영되어 merge conflict 해소 후 PR merge

## dev-log detect-context area 검증 (#164, PR #166)

- **문제**: `detect-context`가 `.workspace/worktrees/` 하위 경로만으로 `inRootWorktree: true` 판단하여 client/server worktree에서 false positive 발생. dev-log가 client/server PR branch에 docs를 혼입할 위험
- **해결**: worktree의 `.git` 파일에서 `gitdir:` 경로를 읽어 root repo에 속하는지 검증
  - `_find_worktree_root()`: nested path에서 `.git` 파일이 있는 worktree root 탐색
  - `_is_root_repo_worktree()`: gitdir 경로가 `{root_repo}/.git/` 하위인지 확인
- **테스트**: client/server false positive, no `.git` file 케이스 등 7개 테스트, 전체 25개 pass
