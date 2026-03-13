# Workspace Progress Index

> 루트 레포(pyosh-blog-ai) 및 개발 환경 인프라 진행 상황 요약

## 타임라인

| 날짜       | 주요 작업                            | 상태 |
| ---------- | ------------------------------------ | ---- |
| 2026-03-13 | orchctl failure classification system (#95, PR #191) - FailureClass(11) + NextAction(4) enum, failure_classifier.py(regex pattern table, timed-out short-circuit, INFRA_CRASH/oom word-boundary fixes), schema v8(attempts.failure_class), reconcile retry budget routing, int() null guard, 45 tests, 6라운드 리뷰 | done |
| 2026-03-13 | legacy cutover / shell compatibility migration (#94, PR #190) - orchctl import-state(13 state 매핑), schema v7 legacy_mode, control cutover/rollback, orch_assert_legacy_active sentinel 가드, 3라운드 리뷰, 287 tests | done |
| 2026-03-13 | dev-orchestrator SKILL.md thin wrapper over orchctl (#93, PR #189) - 240줄→210줄 shell-helper 제거, start/resume/status/doctor/reconcile/pause/drain/stop orchctl 매핑, Poll loop 1h 타임아웃, Invariants/Policy/References 복원, 5라운드 리뷰 APPROVE | done |
| 2026-03-13 | orchctl policy config + operational commands + merge gate (#92, PR #187) - YAML policy 로더, control(pause/resume/drain/undrain/stop/cancel-attempt/requeue), 5-check merge gate, repo allowlist/scheduler_overlap/owns_lease guardrails, schema v6(retry_count/merge_state), 262 tests | done |
| 2026-03-13 | agent-tracker regression / fixture / portability suite (#113, PR #188) - bash 6개 신규(list-panes failure/partial-write/dead-orch/stale-token/control-char/path-traversal), Python pytest 105개(file_adapter/process_adapter/collector/models/display_adapter), display_adapter.py(wc -L→unicodedata), list-panes race condition fix, UnicodeDecodeError fix | done |
| 2026-03-13 | agent-tracker orchctl normalized export contract + adapter (#112, PR #186) - orchctl export command(SQLite→JSON), contract/validate_export(), orchctl_adapter(fixture fallback), collector.py legacy batch.state.json 교체, 35 tests, pipeline runner max-turns 15→30 fix | done |
| 2026-03-13 | orchctl issue discovery + auto-enqueue + configurable scope (#89, PR #185) - reconcile cycle discovery phase, github.py(OR label filter, 30s timeout, limit warning), _REOPEN_STATES auto-derived, re-open transitions(completed/failed-terminal/cancelled→pending), schema v5(5 scope keys), 174 tests, 3라운드 리뷰 | done |
| 2026-03-13 | agent-tracker Python backend + normalized domain model (#111, PR #183) - contract/models/adapters(process+tmux+file)/collector/exporter/__main__, sidecar v2 읽기, atomic export, 8라운드 리뷰 | done |
| 2026-03-13 | orchctl reconcile loop + admission control (#88, PR #184) - observe/diff/act 패턴, mark-complete/unblock/dispatch pass, atomic maxOpenPR TOCTOU 방지, schema v4, 13 new tests, 3라운드 리뷰 | done |
| 2026-03-13 | Skill Python 호출 경로 + 부수 버그 5건 수정 (#181, PR #182) - PYTHONPATH 방식 통일, `--model` 플래그, `gh issue view --json` 제약, cleanup_wt 단계 분리, codex review_runner 디버깅 개선, SKILL 압축 최적화 | done |
| 2026-03-13 | 확장 terminal states + claim/hold 라벨 (#91, PR #179) - `failed-terminal`/`needs-human`/`needs-spec`/`cancelled` 신규 terminal state, `orch_set_terminal` 래퍼, `claimed-by-orch`/`needs-human`/`needs-spec`/`manual-hold` issue 라벨 자동 관리, dispatch 전 `manual-hold` skip | done |
| 2026-03-13 | agent-tracker writer contract alignment (#110, PR #180) - ANSI/OSC sanitization, model "unknown" fallback, tokens_updated_at 정확성, v1 sidecar 마이그레이션, pipeline state issue int 정규화 | done |
| 2026-03-13 | dev-pipeline/dev-log 안정성 버그 10건 수정 (#177, PR #178) - dev-log rebase base fix, failed_postcondition retry(B/D 무한루프 방지), merge conflict 진단, stageRetries 이월, round_limit 기록, dispatch cwd+review-wait 의무, approve publish 강제, pr_helpers --head, gh CLI 업데이트, resolve_finalize 항상 push | done |
| 2026-03-13 | hard/soft dependency + cross-area policy (#90) - fenced orchestrator 블록 파서, `--parse-typed`/`--find-sccs` 모드, SCC cycle 격리, `blocked-failed-dependency`/`blocked-external`/`cycle-isolated` 신규 상태, 25 tests (PR #176) | done |
| 2026-03-13 | agent-tracker sidecar v2 + immediate cutover (#109) - schema_version/session_name/tmux_server 필드 추가, socket-hash/session/pane 3레벨 namespace로 변경, v1 flat 파일 자동 정리, source precedence 문서화 (PR #175) | done |
| 2026-03-13 | agent-tracker Bash safety hotfix (#108) - @tsv 필드 밀림(RS=\x1e+base64), dead orchestrator [DEAD] 표시, 토큰 0/0 unknown, done 체크 무조건화, pane_id guard, stale/fault/dead 분리 (PR #174) | done |
| 2026-03-13 | orchctl leader lease + dispatch idempotency (#87) - schema migration v3 (heartbeat_at + unique partial index), db/lease.py 신규(acquire/renew/release/cleanup_stale/has_active_attempt), reconcile version guard + per-issue renew, 41 new tests, 8라운드 리뷰 (PR #173) | done |
| 2026-03-13 | orchctl core state machine Python 이전 + 기본 테스트 (#86) - IssueState/AttemptStatus enums, ISSUE_TRANSITIONS/ATTEMPT_TRANSITIONS 맵, optimistic-lock apply_*_transition(StaleStateError), resolve_blocked_issue(soft/hard dep), try_acquire_lease upsert, schema v2(state 어휘 확장 + idx_issues_state), 93 tests, 5라운드 리뷰 (PR #172) | done |
| 2026-03-13 | dev-pipeline 4개 버그 수정 (#170) - review-wait pending 분기 추가, suggestion_only round 카운터 수정, normalizer 들여쓰기 오파싱 수정, reviewBody 데이터 포함 (PR #171) | done |
| 2026-03-13 | docs branch git strategy (#168) - dev-log 커밋을 long-lived `docs` 브랜치로 전환, `/dev-archive` squash-merge PR 신규 스킬, pipeline merge -> log 순서 재배치 (PR #169) | done |
| 2026-03-13 | orchctl CLI skeleton + SQLite schema (#85) - `tools/orchctl/` Python 패키지, Click CLI(init/status/doctor/reconcile), WAL+FK SQLite schema v1(issues/attempts/heartbeats/leases/config), 마이그레이션 러너, 16 tests, 5라운드 리뷰 (PR #167) | done |
| 2026-03-13 | dev-pipeline log → merge 순서 변경 (#164) - 상태 머신 `log → merge → done` 재배치로 `lock_merge` 발산 원천 차단 + detect-context area 검증 추가 (PR #165, #166) | done |
| 2026-03-12 | dev-log Python CLI + SKILL.md thin contract (#153) - dev_log Python 패키지 8모듈, SKILL.md 108→71줄(-34%), 참조 3파일 삭제, AI 컨텍스트 537→211줄(-61%), 22 tests, 4라운드 리뷰 (PR #159) | done |
| 2026-03-12 | dev-pipeline SKILL.md thin contract 재작성 (#151) - 409→125줄(-69%), bash 블록 26→0, step 서브커맨드+action 테이블 기반 thin contract, #152 표준 섹션 구조 적용, 참조 파일 정리(process-lifecycle step subcommands 추가, recovery v3 간소화, pipeline-audit 삭제) (PR #158) | done |
| 2026-03-12 | dev-pipeline Python CLI step subcommand + bug fixes (#150) - `steps.py` 9개 step 함수 + `StepResult` 라우팅 데이터클래스, `step` CLI 서브커맨드, codex `--output-schema` → `--output-last-message` (v0.114.0), 전체 `failed_*` 상태 codex→claude 폴백, `init --issue` 상태 파일 생성; 37 new tests, 258 total (PR #157) | done |
| 2026-03-12 | dev-review + dev-issue SKILL.md 표준화 (#152) - 표준 섹션 순서(Invariants → Environment → Workflow → Constraints) 적용, dev-review `Prohibited`/`Steps` → `Invariants`/`Workflow`, dev-issue `Constraints` → `Invariants` 승격 + Title rules/Labels → `Constraints` 하위 이동 (PR #156) | done |
| 2026-03-12 | dev-review 자동 게시 + dev-log standalone squash merge 충돌 수정 (#148) - REVIEW_MODE 기본값 publish, `_is_pr_author` verdict 하강, dev-log Phase 0 worktree 컨텍스트 감지; codex `--output-schema` 제거(v0.114.0) → claude 폴백 확인 (PR #149) | done |
| 2026-03-12 | PR identity metadata + doctor command (#84) - `orch_branch_name()` deterministic branch naming, `_orch_pr_list()` branch>label>body fallback chain, `orch_label_pr()` identity labels, `orch_doctor()` 6-check diagnostics, `issueMetadata` durable PR tracking (PR #145) | done |
| 2026-03-12 | dispatch_codex structured output (#142) + contract-driven review publisher (#144) - `review_publish.py` CLI(schema 검증+contamination 검사+markdown 렌더링), `review_schema.json` canonical schema, SKILL.md JSON-first flow 전면 개편, codex path publisher 위임, 스킬 최적화(109→42줄), 2라운드 리뷰 resolve; 36 tests (PR #143) | done |
| 2026-03-11 | Worker auto-merge 중단 + merge eligibility contract - dispatch prompt "auto-approve merge" 제거, `orch-dispatch-wrapper.sh` EXIT trap에 4-way eligibility check(`checksPass`/`noConflict`/`noBlockingLabels`/`shaMatch`) + `terminal.json` `mergeEligible`/`mergeEligibilityChecks` 추가, `state-detection.md` 스키마 업데이트 (#83, PR #141) | done |
| 2026-03-11 | dev-pipeline 신뢰 경계 재설계 - fail-closed 파싱(`FAILED_PARSE` + raw transcript 업로드 금지), 40-char SHA 강제, atomic issue lease(`O_CREAT|O_EXCL`, `acquired` bool), `sync-state` self-healing, review fingerprint + 수렴 감지, 이중 형식 리뷰 본문, SKILL.md skill-creator 최적화; 5 test suites (#139, PR #139) | done |
| 2026-03-11 | Worker worktree isolation + GC for orchestrator - `orch_worktree_quarantine` (git metadata preservation + name collision), `orch_orphan_gc` (current-batch + `everDispatched` guard), `orch_disk_budget_gc` (500 MB ceiling), `everDispatched[N]` batch flag, `abnormal_exit`+merged PR→`completed` fix; SKILL.md lifecycle section; 11라운드 Codex 리뷰 (#82, PR #137) | done |
| 2026-03-11 | dev-pipeline shell 잔재 제거 + dev-resolve 정리 + review template 준수 - `pipeline-helpers.sh`/`smoke-test.sh` 삭제, CLI 5개 추가(init/state-update/stage-retry/check-review/check-commits), SKILL.md shell→Python CLI 재작성, codex `normalize_codex_output()` blockquote 방식; 133 tests (#129, #133, PR #136) | done |
| 2026-03-11 | dev-pipeline Python 마이그레이션 리뷰 피드백 수정 - CLAUDECODE env, step migration, review state filter, area validation, typed model, stale recovery, cmd_state fix, path validation, max review id; 128 tests (#129, #133, PR #134) | done |
| 2026-03-11 | dev-pipeline 안정화 Epic 1 - review 3분할, `pipeline_run_review` 단일 진입점, `reviewJob` 메타 + 중복 방지, `pipeline_parse_review_body`, resolve 결정 테이블, state machine 전이 테이블, `pipeline_log_transition`, smoke test (#131, PR #130) | done |
| 2026-03-11 | Codex headless review 3 bugs + SKILL turn conflict - `--sandbox danger-full-access` → `--dangerously-bypass-approvals-and-sandbox`, stderr→log redirect, SKILL.md turn-end + task-notification wait + review carve-out (#128) | done |
| 2026-03-11 | Archive + rotation for orchestrator - `orch_archive_batch` / `orch_archive_list` / `orch_archive_rotate` helper functions, batchId collision-resistance, `.archived-at` rotation ordering, SKILL.md + recovery.md 업데이트 (#81, PR #127) | done |
| 2026-03-10 | Pipeline auto-proceed + codex review bug fixes - build 후 자동 진행 미작동(pre-build state + 턴 종료 금지), codex --base+prompt 충돌, config schema 오류, sandbox 중첩 getdents64 차단(danger-full-access), --output-last-message 빈 파일(stdout 직접 사용) | done |
| 2026-03-10 | Orchestrator atomic state + process group termination - dispatched worker identity에 startTime 추가, flock 직렬화 + kill -- -pgid 기존 구현 확인, acceptance criteria 완료 (#80) | done |
| 2026-03-10 | Headless review agent dispatch - Claude Code / Codex tool selection, `pipeline_run_headless_core` tool 파라미터 추가, codex exec review 연동, `--output-last-message` + 동적 base ref + codex review 포스팅 (#123, PR #124) | done |
| 2026-03-10 | Attempt isolation - attemptId + artifact directory separation, attemptId format `issue-{N}-a{M}`, per-attempt directory `.workspace/orchestrate/{area}/issues/{N}/attempts/{attemptId}/`, previous attempt artifact preservation (#79) | done |
| 2026-03-10 | Pipeline direct resolve + auto-merge - headless resolve 제거, 직접 resolve 전환, review-resolve 자동 루프(5라운드), severity 기반 auto-merge, lock fencing+grace-period reclaim (#120, PR #121) | done |
| 2026-03-10 | Pipeline headless CLAUDECODE unset + audit fixes - CLAUDECODE 미해제 버그 수정, gh stderr mktemp 격리, meta guard, merge lock 서브셸, rc=2 API 오류, SKILL.md 경로 수정 (PR #119) | done |
| 2026-03-09 | Orchestrator terminal result contract - terminal.json schema 도입, orch_check_completion 재작성 (terminal file만이 completed 근거), PR fallback 보조화 (#78) | done |
| 2026-03-09 | Claude Code shared config bootstrap - CLAUDE.md 모듈 분리, .claude/rules/ + settings.json + validate-bash.py hook, bootstrap 스크립트, permissions 축소 (#115) | done |
| 2026-03-09 | Pipeline cwd 3-way 분리 - skill cwd / repo dir / worktree dir 혼용 수정, area-scoped 경로, TTL merge lock, 숨은 버그 8건 수정 (#106) | done |
| 2026-03-08 | Orchestrator/pipeline 신뢰성 전면 개편 - attemptId, setsid+PGID, provider health circuit breaker, heartbeat, skipped_dep_failed, flock (#76) | done |
| 2026-03-08 | agent-tracker 토큰 표시 신뢰성 개선 - coherent snapshot, freshness 분리, 파싱 실패 폴백, 105 fixture 테스트 (#74) | done |
| 2026-03-08 | agent-tracker 구조적 데이터 경계 및 신뢰성 전면 개편 - lib/ 3-layer 분리, JSON+@tsv 프로토콜, 66 fixture 테스트 (#72) | done |
| 2026-03-08 | Shell script cleanup - stale code 삭제 및 과도한 복잡성 제거 (#70) | done |
| 2026-03-08 | agent-tracker 프로세스 감지 단순화 + orchestrator liveness 수정 (#68) | done |
| 2026-03-08 | agent-tracker 칸 밀림 근본 수정 + orchestrator pane 기반 렌더링 (#66) | done |
| 2026-03-07 | agent-tracker UI 버그 수정 - 칸 밀림, done/idle 구분, batch liveness PID 기반 감지 (#64) | done |
| 2026-03-07 | agent-tracker sidecar 경로 이동 + pipeline 중복 제거 + 토큰 버그 수정 - current_usage 기반 전환 (#62) | done |
| 2026-03-07 | Orchestrator 안정성 개선 - agent-tracker 배치 UI, pipeline model 전달, atomic dispatch (#59, #60, #61) | done |
| 2026-03-07 | Orchestrator headless 전환 + merge queue - tmux pane dispatch를 `claude -p` 백그라운드 프로세스로 교체, lock 기반 merge 직렬화 (#57) | done |
| 2026-03-07 | Headless pipeline - tmux pane을 synchronous `claude -p` subprocess로 전환 + self-healing 통합 (#55, PR #56) | done |
| 2026-03-06 | Orchestrator pane release 누락 + agent model/pane flexibility 수정 - orch_release_pane, _orch_parse_agent, ORCH_WORK_PANES (#53, PR #54) | done |
| 2026-03-06 | agent-tracker 동적 pane 감지 실패 수정 - AGENT_TYPE_CACHE 제거, pane ID 안정화, staleness 감지, chmod 700 (PR #50, #47) | done |
| 2026-03-06 | Orchestrator pipeline 완료 감지 - state file 부재 기반, pipelineStarted 플래그, 3회 버그 검증 (#48, PR #49) | done |
| 2026-03-06 | Pipeline tmux pane resilience 개선 - orphan pane 증식 방지, atomic state, state 기반 retry, remain-on-exit 검증, RAPHL self-fix (PR #46) | done |
| 2026-03-05 | Orchestrator dispatch 버그 6종 수정 - set-e 안전, sub-pane 필터, maxConcurrent, DAG 외부 dep 필터, startup 검증, recovery jq (PR #44) | done |
| 2026-03-04 | agent-tracker 토큰 표시 수정 + transcript 읽기 최적화 (#42, PR #43) | done |
| 2026-03-04 | Skill 간 중복된 monorepo 로직을 공유 reference + helper로 추출 (#40) | done |
| 2026-03-03 | agent-tracker Task/Activity 영숫자 누락 수정 - jq gsub regex `[[:cntrl:]]` 교체 (#34) | done |
| 2026-03-03 | PR #33 머지 완료 - agent-tracker 버그 수정, 성능 최적화, lifecycle 개선 4라운드 리뷰 통과 (#30 #31 #32) | done |
| 2026-03-02 | PR #27 머지 완료 - agent-tracker push architecture (#25) + Activity column (#26), 12라운드 Codex 리뷰 | done |
| 2026-03-02 | PR #29 머지 완료 — dev-pipeline 스킬 버그 수정 4라운드 리뷰 통과 (#28) | done |
| 2026-03-02 | PR #29 3차 리뷰 수정 — MONOREPO_ROOT 감지 git worktree list → BASH_SOURCE 역추적 교체 (#28) | done |
| 2026-03-02 | dev-pipeline 스킬 버그 수정 10개 항목 - eval 인젝션, awk 파싱, MONOREPO_ROOT, gh api 오류, tmux 체크, state 충돌 등 (#28) | done |
| 2026-03-02 | dev-pipeline merge 단계 버그 수정 (exit code check, state namespace, cleanup 순서) + Check plan 개편 + skill-creator 최적화 — PR #24 (#21, #22, #23) | done |
| 2026-03-01 | PR #15 최종 resolve (Option A 호환성 복원) + 범위 밖 변경 제거 → PR #15 머지 (#14) | done |
| 2026-03-01 | dev-pipeline pane 관리 결함 수정 및 test plan 검증 루프 추가 — PR #20 머지 (#17, #18) | done |
| 2026-03-01 | PR #15 10차 리뷰 수정 — pipeline state area 네임스페이싱 (pipeline-helpers + orchestrate-helpers) (#14) | done |
| 2026-03-01 | PR #19 머지 완료 — agent-tracker Codex 감지 / Task·Token 표시 / /clear 토큰 리셋 (#16) | done |
| 2026-03-01 | PR #15 최종(8-9차) 리뷰 수정 — retry dispatchedAt 초기화, orch_print_summary 문서 인자 추가 (#14) | done |
| 2026-03-01 | PR #20 [SUGGESTION] 수정 — pipeline_orchestrator_pane() $TMUX_PANE 미설정 시 tmux display-message 폴백 (#17, #18) | done |
| 2026-03-01 | PR #15 5-7차 리뷰 최종 수정 — orch_find_idle_panes 세션 범위 필터, orch_state_update 원자적 쓰기 (#14) | done |
| 2026-03-01 | PR #19 [CRITICAL] 수정 — Codex 감지: exe 경로 → argv 기반 재귀 탐색으로 교체 (#16) | done |
| 2026-03-01 | PR #15 3-4차 리뷰 수정 — DAG_JSON 파라미터 확장, jq 우선순위, 대소문자 키워드 (#14) | done |
| 2026-03-01 | PR #15 2차 리뷰 수정 — orch_unblock() dep_status 판별: completed 단독 → completed\|failed 허용, deadlock 완전 수정 | done |
| 2026-03-01 | PR #15 리뷰 수정 — dev-orchestrator: --check-cycles 도달 불가 / failed deadlock / grep pipefail / SKILL.md 인자 정정 | done |
| 2026-03-01 | `/dev-orchestrator` 스킬 구현 — 다중 이슈 병렬 배치 오케스트레이터 (#14) | done |
| 2026-03-01 | PR #13 리뷰 수정 — parse_claude_pane() 멀티라인 task 잘림: @base64 인코딩으로 해결 (#12) | done |
| 2026-03-01 | agent-tracker 다중 에이전트 트래킹 오류 및 대시보드 개선 (#12, PR #13 머지 완료) | done |
| 2026-03-01 | agent-tracker 컬럼 정렬 수정 + transcript 기반 Task/Token 갱신 (#9, #10, PR #11) | done |
| 2026-03-01 | PR #8 머지 완료 — tracker window 추가 (session.docker.yml + ARCHITECTURE.md), Issue #7 종료 | done |
| 2026-03-01 | PR #8 리뷰 코멘트 수정 — agent-tracker.sh: PIPELINE_DIR 경로, grep -P 이식성, Codex 세션 매핑, INTERVAL 검증 | done |
| 2026-03-01 | tmux Agent Tracker 대시보드 `scripts/agent-tracker.sh` 구현 (#7) | done |
| 2026-03-01 | Docker 컨테이너 TZ 기본값 Seoul 버그 수정 (docker-compose + entrypoint 데드 브랜치 제거) | done |
| 2026-02-28 | brainstorming + writing-plans 스킬 경로/구조 개선 + 최적화 | done |
| 2026-02-28 | dev-issue 스킬 리비전: 입력 소스 확장 + ISSUE_TEMPLATE 참조 + 구조 최적화 | done |
| 2026-02-28 | Feature Spec v1 리비전 + 48 GitHub Issues 마이그레이션 (client #23-#70, server #26) | done |
| 2026-02-28 | Labels/PR template standardization + CLAUDE.md English (3 repos) | done |
| 2026-02-28 | Docker auth volume fix (native installer) + CLAUDE.md English + worktree/post-commit rules | done |
| 2026-02-28 | Issue 템플릿 개편 + priority 5단계 축소 + 라벨 마이그레이션 (3 repo) | done |
| 2026-02-28 | dev-pipeline Pane Lifecycle Tracking + 스킬 최적화 + CLAUDE.md repo별 워크플로우 분리 | done |

<!-- 새 항목은 위에 추가 -->
