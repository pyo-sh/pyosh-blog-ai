# 2026-03-09 Progress

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
