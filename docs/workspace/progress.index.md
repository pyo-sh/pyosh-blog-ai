# Workspace Progress Index

> 루트 레포(pyosh-blog-ai) 및 개발 환경 인프라 진행 상황 요약

## 타임라인

| 날짜       | 주요 작업                            | 상태 |
| ---------- | ------------------------------------ | ---- |
| 2026-03-10 | Archive + rotation - batch 완료 후 상태/log/artifact를 archive/{batchId}/로 보존, orch_archive_batch + orch_archive_list + orch_archive_rotate 추가, SKILL.md + recovery.md rm -rf 제거 (#81) | done |
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
