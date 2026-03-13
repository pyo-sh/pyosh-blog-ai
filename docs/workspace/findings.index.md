# Workspace Findings Index

> 루트 레포 및 워크스페이스 환경 (Docker, tmux, skills, 워크플로) 관련 기술 조사, 문제 해결, 인사이트 모음

## 목차

| ID  | 제목                                                      | 날짜       | 태그                                        |
| --- | --------------------------------------------------------- | ---------- | ------------------------------------------- |
| 001 | tmux 기반 멀티 AI 에이전트 협업 환경                      | 2026-02-25 | #tmux #multi-agent #claude-code #ipc        |
| 002 | Docker 단일 파일 bind mount 깨짐 & Claude Code 세션 캐싱 | 2026-02-28 | #docker #bind-mount #claude-code #cache     |
| 003 | tmux Pane 수명 관리와 Pipeline 안정성                     | 2026-02-28 | #tmux #pane #pipeline #health-check         |
| 004 | Claude Code vs Codex CLI Hook 비교                        | 2026-02-28 | #claude-code #codex #hooks #comparison      |
| 005 | tmux OSC 52 드래그 복사 설정 문제                         | 2026-02-28 | #tmux #osc52 #clipboard #nested-tmux        |
| 006 | Docker 컨테이너 타임존 UTC 고정 버그                      | 2026-03-01 | #docker #timezone #entrypoint #dead-branch  |
| 007 | Claude Code Transcript JSONL 접근 방법                    | 2026-03-01 | #claude-code #transcript #jsonl #tmux #jq   |
| 009 | Pipeline review/resolve pane workdir 설정               | 2026-03-04 | #pipeline #claude-code #skills #workdir #monorepo |
| 008 | Claude Code statusLine의 total_input_tokens 부정확 문제  | 2026-03-04 | #claude-code #statusline #tokens #transcript |
| 010 | Orchestrator dispatch 버그 3종 분석 및 수정              | 2026-03-05 | #orchestrator #dispatch #set-e #sub-pane #dag |
| 011 | Pipeline pane orphan 증식 원인과 해결                    | 2026-03-06 | #pipeline #tmux #pane #orphan #remain-on-exit #retry |
| 012 | agent-tracker 동적 pane 감지 실패 원인 분석             | 2026-03-06 | #agent-tracker #sidecar #pane-id #cache #staleness |
| 013 | Orchestrator pane release 누락 - interactive mode 잔류 | 2026-03-06 | #orchestrator #pane #release #tmux #claude-code |
| 014 | Headless dispatch architecture - tmux pane에서 claude -p 백그라운드 프로세스로 | 2026-03-07 | #headless #claude-p #pid #dispatch #merge-queue |
| 015 | agent-tracker 과도 설계 - `/proc` BFS가 tmux API보다 나쁜 이유 | 2026-03-08 | #agent-tracker #proc #tmux #overengineering #process-detection |
| 017 | pipeline_run_headless_core CLAUDECODE 환경변수 전파 버그 | 2026-03-09 | #pipeline #headless #claude-p #claudecode #env-var #nested-session |
| 016 | Pipeline cwd 혼용 진단 및 3-way 분리 | 2026-03-09 | #pipeline #cwd #worktree #monorepo #skill-discovery #merge-lock |
| 018 | agent-tracker sidecar v2 namespace design | 2026-03-13 | #agent-tracker #sidecar #namespace #tmux #multi-session |
| 019 | Tarjan SCC vs Kahn for dependency cycle quarantine | 2026-03-14 | #orchctl #cycle-detection #tarjan #scc #scheduling |

## 상세 문서

- [findings.001-tmux-multi-agent.md](./findings/findings.001-tmux-multi-agent.md) - tmux 멀티 에이전트 협업 패턴
- [findings.002-docker-bind-mount-and-session-cache.md](./findings/findings.002-docker-bind-mount-and-session-cache.md) - Docker bind mount inode 문제 & Claude Code 캐싱 한계
- [findings.003-tmux-pane-lifecycle.md](./findings/findings.003-tmux-pane-lifecycle.md) - tmux Pane 수명 관리, health check 패턴, return code 규약
- [findings.004-claude-code-vs-codex-hooks.md](./findings/findings.004-claude-code-vs-codex-hooks.md) - Claude Code vs Codex CLI Hook 아키텍처 비교
- [findings.005-tmux-osc52-clipboard.md](./findings/findings.005-tmux-osc52-clipboard.md) - tmux OSC 52 드래그 복사: set-clipboard scope, Ms 포맷, mode-keys 수정
- [findings.006-docker-tz-dead-branch.md](./findings/findings.006-docker-tz-dead-branch.md) - Docker 컨테이너 TZ 기본값 미적용: entrypoint.sh 데드 브랜치 + docker-compose 빈 기본값
- [findings.007-claude-transcript-jsonl.md](./findings/findings.007-claude-transcript-jsonl.md) - Claude Code transcript JSONL: cwd→project dir 매핑, null-safe jq 쿼리, user message 형식
- [findings.009-pipeline-pane-workdir.md](./findings/findings.009-pipeline-pane-workdir.md) - review/resolve pane은 /workspace(모노레포 루트)에서 시작해야 skills 탐색 가능
- [findings.008-statusline-total-input-tokens.md](./findings/findings.008-statusline-total-input-tokens.md) - Claude Code statusLine의 total_input_tokens가 시스템 프롬프트/도구/메모리 제외하여 부정확
- [findings.010-orchestrator-dispatch-bugs.md](./findings/findings.010-orchestrator-dispatch-bugs.md) - set-e 크래시, sub-pane 과잉 dispatch, 외부 dep 영구 차단 3종 분석
- [findings.011-pane-orphan-proliferation.md](./findings/findings.011-pane-orphan-proliferation.md) - pipeline pane orphan 증식: remain-on-exit 상호작용, alive vs verified 분리, jq 우선순위
- [findings.012-agent-tracker-detection-failures.md](./findings/findings.012-agent-tracker-detection-failures.md) - agent-tracker 동적 pane 감지 실패: negative cache, PPID 불안정, TRANSCRIPT_LAST_MSG 회귀
- [findings.013-orchestrator-pane-release.md](./findings/findings.013-orchestrator-pane-release.md) - Orchestrator pane release 누락: interactive mode 잔류, Ctrl+C fallback, `-p` 비호환
- [findings.014-headless-dispatch-architecture.md](./findings/findings.014-headless-dispatch-architecture.md) - tmux pane → claude -p 헤드리스 전환: nested headless, CLAUDECODE= unset, $BASHPID, merge queue
- [findings.015-agent-tracker-overengineering.md](./findings/findings.015-agent-tracker-overengineering.md) - agent-tracker 과도 설계: /proc BFS vs tmux API, AI 행동 패턴 분석, 단순화 원칙
- [findings.017-pipeline-headless-claudecode-env.md](./findings/findings.017-pipeline-headless-claudecode-env.md) - pipeline_run_headless_core CLAUDECODE 미해제: Claude Code 세션 안에서 claude -p 호출 시 중첩 세션 오류, unset CLAUDECODE 해결
- [findings.016-pipeline-cwd-separation.md](./findings/findings.016-pipeline-cwd-separation.md) - Pipeline cwd 혼용 진단: skill cwd / repo dir / worktree dir 3-way 분리, TTL merge lock, area-scoped 경로
- [findings.018-sidecar-v2-namespace.md](./findings/findings.018-sidecar-v2-namespace.md) - agent-tracker sidecar v2: socket-hash/session/pane 3레벨 경로, immediate cutover, source precedence, md5sum Linux-only 주의
- [findings.019-tarjan-scc-cycle-quarantine.md](./findings/findings.019-tarjan-scc-cycle-quarantine.md) - Tarjan SCC correctly isolates cycle members only; Kahn's algorithm incorrectly quarantines downstream dependents; rate-limit detection scoped to discovery pass

## 주요 원칙

- **Docker 단일 파일 bind mount 금지** → 디렉토리 마운트 + 심링크 패턴 사용
- **Claude Code 설정 변경 = 프로세스 재시작 필수** → `/clear`로는 불충분
- **Pane health check 순서: API 먼저 → health 나중** → 정상 종료 후 결과 누락 방지
- **Claude Code Hook = 양방향 Gate** → Codex CLI는 단방향 Notify만 지원
- **tmux set-clipboard은 server option** → `set -s` 사용, `Ms` 포맷에 `%p1%s` 필수
- **Pipeline pane workdir = /workspace** → client/server는 독립 git repo라 `.claude/skills/` 탐색 불가. pane은 항상 모노레포 루트에서 시작.
- **Orchestrator helper 함수는 항상 return 0** → stdout으로만 상태 전달. `set -e` caller 안전.
- **orch_find_idle_panes는 window당 1 pane** → sub-pane dispatch 방지. `head -1`로 `pane-base-index` 무관.
- **orch_init DAG 자동 필터링** → batch에 없는 외부 dep을 자동 제거. AI 수동 필터 불필요.
- **완료 후 pane release는 Ctrl+C 2회** → prompt exit 미이행 시 fallback. pane 파괴 아닌 shell 복귀.
- **`-p`(print) 모드는 pipeline과 비호환** → AskUserQuestion 호출 시 stdin 불가. interactive 모드 필수.
- **remain-on-exit on 상태에서 pane_alive는 dead pane도 true** → `#{pane_dead}` flag로 직접 확인 필요
- **Polling은 pane_alive, recovery는 pane_alive_verified** → child process가 `#{pane_current_command}` 변경하므로 polling에서 verified 사용 금지
- **State 기반 retry counter는 성공 시에만 reset** → PANE_DEAD에서 reset하면 무한 루프
- **캐시 제거가 캐시 무효화보다 낫다** → /proc 탐색 비용은 무시 가능. 캐시 무효화 버그 위험이 더 큼
- **다단계 프로세스 체인에서 PPID는 불안정** → wrapper 경유 시 env var로 안정 식별자 전달
- **env var export 삭제 전 소비처 확인 필수** → `grep -r VAR_NAME` 후 제거
- **`CLAUDECODE=` unset 필수** → 자식 claude -p가 부모 환경변수 상속하면 충돌. `pipeline_run_headless_core`는 내부 서브쉘에서 `unset CLAUDECODE` 선행 필요 (orch-dispatch-wrapper는 setsid로 격리되어 무관)
- **`$$` 대신 `$BASHPID`** → 서브셸/백그라운드에서 `$$`는 top-level shell PID. lock PID 기록 시 `${BASHPID:-$$}` 사용
- **병렬 merge는 lock 직렬화 필수** → 같은 area 동시 merge 시 rebase 충돌. `mkdir` atomic lock + PID stale 감지
- **가장 높은 수준의 API를 사용할 것** → tmux `#{pane_current_command}`, `ps -t`로 충분하면 `/proc` BFS 탐색 불필요. 저수준 재구현은 환경별 깨짐 위험이 더 큼
- **2단계 이상 fallback 체인 금지** → 3번째 fallback부터는 문제를 가리는 것. 실패를 명시적으로 드러내는 게 디버깅에 유리
- **버그 수정 시 삭제를 먼저 고려** → workaround 추가보다 원인 코드 제거가 우선. 기존 코드를 "정답"으로 전제하지 말 것
- **Claude session root ≠ 코드 수정 위치** → skill cwd(monorepo root), repo dir(area checkout), worktree dir(feature branch)은 반드시 분리
- **gh 명령은 explicit repo 사용** → cwd 의존 제거. `-R owner/repo` 또는 `repos/owner/repo/...` 명시
- **merge lock은 한 프로세스에서 acquire/release 완결** → 별도 Bash tool 호출 분리 금지. TTL 기반 stale 판단
- **모든 transient 파일 경로에 area 포함** → client/server 번호 충돌 방지. worktree, log, message, state 전부 area-scoped
