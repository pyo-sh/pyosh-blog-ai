# 2026-03-09 Progress

## Claude Code shared config bootstrap setup (#115)

단일 CLAUDE.md를 모듈식 공유 설정으로 분리하고, bootstrap 스크립트와 bash validation hook을 도입했다.

### 구조 변경

- `CLAUDE.md` - 134행 → 36행으로 축소, 세부 규칙은 `.claude/rules/`로 이동
- `.claude/settings.json` - permissions allowlist (읽기 전용 git branch 패턴), deny list (.env, secrets), PreToolUse hook 등록
- `.claude/hooks/validate-bash.py` - curl|sh, eval, source <(...) 차단, rm -rf/git clean/sudo/2>&1 확인 요청, 파이프/&& 복잡도 검사
- `.claude/rules/*.md` - bash, git-safety, worktree-workflow, docs-context, markdown-writing (path-scoped)
- `tools/claude/bootstrap.sh` - root/client/server 템플릿 동기화, child repo claudeMdExcludes 생성 (create-only)
- `tools/claude/templates/` - repo별 + shared 템플릿 소스
- `tools/claude/README.md`, `README.ko.md` - 온보딩 가이드

### 주요 결정

- hook command 경로: `$CLAUDE_PROJECT_DIR` 사용 (상대 경로 대신)
- `Bash(git branch *)` → 읽기 전용 하위 패턴 6개 분리, `Bash(find . -maxdepth *)` 제거
- `settings.local.json` 덮어쓰기 방지: bootstrap은 파일 없을 때만 생성
- `ensure_git_info_exclude`: `git rev-parse --git-path info/exclude`로 worktree 호환
- `.claude/README.md` 제거: Claude Code가 자동 로드하지 않으므로 각 repo 복사 불필요
- validate-bash.py: Python 3.7+ 호환 (`str | None` 대신 `Optional[str]`)

## Orchestrator terminal result contract 도입 (#78)

오케스트레이터 완료 판정을 명시적 terminal.json 계약 기반으로 재설계했다.

### 변경 파일

- `.agents/skills/dev-orchestrator/scripts/orch-dispatch-wrapper.sh` - 인자 2개 추가 (`ISSUE`, `PIPELINE_STATE_FILE`), `.exit` → `terminal.json` 리네임, schemaVersion/prNumber/merged/headSha/finishedAt/reason 필드 포함 jq 기반 출력
- `.agents/skills/dev-orchestrator/scripts/orchestrate-helpers.sh` - `orch_signal_path` → `orch_terminal_path` (alias 유지), `orch_dispatch`에 `pipeline_state_file` 변수 추가 + wrapper 호출 인자 확장, `orch_check_completion` 재작성
- `.agents/skills/dev-orchestrator/references/state-detection.md` - terminal result contract 섹션 신설, PR fallback 테이블에서 merged=completed 경로 제거

### orch_check_completion 변경 요약

- **이전**: merged PR → `completed` (terminal file 없어도 판정 가능)
- **이후**: terminal.json만이 `completed`/`failed`의 유일한 근거
- PR fallback: merged PR → `abnormal_exit` (trap이 SIGKILL로 실행 불가였음을 의미), open PR → `abnormal_exit`, PR 없음 → `failed`

### terminal.json 스키마 (schemaVersion 1)

```json
{
  "schemaVersion": 1,
  "attemptId": "batch-20260308-issue78-attempt0",
  "issue": 78,
  "status": "completed",
  "prNumber": 123,
  "merged": true,
  "headSha": "abc1234",
  "finishedAt": "2026-03-09T20:27:00Z",
  "reason": "pipeline completed at step=log"
}
```

## Pipeline cwd 3-way 분리 (#106)

파이프라인의 skill cwd / repo dir / worktree dir 혼용 문제를 구조적으로 수정했다.

### 변경 파일

- `.agents/scripts/monorepo-helpers.sh` - `monorepo_area_from_dir` 재작성, nested/worktree path 대응
- `.agents/skills/dev-pipeline/scripts/pipeline-helpers.sh` - 3-way cwd 분리, area-scoped 경로, TTL merge lock, `pipeline_merge_pr` 통합, `pipeline_state_update` jq args 전달, `pipeline_push_branch_safely`
- `.agents/skills/dev-pipeline/SKILL.md` - non-negotiable invariants 추가, helper 함수 기반 예시
- `.agents/skills/dev-review/SKILL.md` - runtime contract (env vars), explicit `-R` 사용
- `.agents/skills/dev-resolve/SKILL.md` - runtime contract, worktree 분리 명시
- `.agents/skills/dev-pipeline/references/pipeline-audit.md` - 진단 요약 및 숨은 버그 8건 기록

### 수정된 버그

1. `Unknown skill: dev-resolve` - worktree에서 claude -p 실행 시 skill 탐색 실패
2. client/server worktree 경로 충돌 (.workspace/worktrees/issue-N)
3. client/server 로그/메시지 파일명 충돌
4. merge lock PID 기반 stale 판단 오작동
5. `pipeline_recovery_log` jq 변수 전달 실패
6. merge 직전 rebase/push를 repo dir에서 실행
7. `monorepo_area_from_dir` nested/worktree path 오판
8. `pipeline_release_merge_lock` holder 검증 없이 해제
