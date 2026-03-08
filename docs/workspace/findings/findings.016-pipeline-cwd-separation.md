# Pipeline cwd 혼용 진단 및 3-way 분리

> 날짜: 2026-03-09
> 태그: #pipeline #cwd #worktree #monorepo #skill-discovery #merge-lock
> 관련 Issue: #106

## 문제

파이프라인이 세 가지 실행 컨텍스트를 `workdir` 하나로 처리하고 있었다.

1. **skill cwd** - Claude session이 `.claude/skills/`를 탐색하는 기준 (항상 monorepo root여야 함)
2. **repo dir** - `gh`/repo 수준 git 명령 실행 위치 (client/ 또는 server/)
3. **worktree dir** - feature branch 파일 수정 위치 (.workspace/worktrees/{area}/issue-{N})

이 혼용으로 인해 다음 문제들이 반복 발생했다.

- worktree에서 `claude -p` 실행 시 `Unknown skill: dev-resolve`
- client/server issue 번호 겹침 시 worktree 경로 충돌
- client/server PR 번호 겹침 시 로그/메시지 파일 덮어쓰기
- merge lock PID 기반 stale 판단이 Bash tool 호출 경계에서 오작동
- `pipeline_recovery_log`의 jq 변수 미전달 버그
- merge 직전 rebase/push를 repo dir에서 실행하는 논리 오류

## 해결

### 3-way cwd 분리

| 컨텍스트 | 용도 | 값 |
|----------|------|-----|
| `pipeline_skill_cwd()` | Claude headless session cwd | 항상 `$MONOREPO_ROOT` |
| `pipeline_repo_dir($area)` | gh/git repo 명령 | `$MONOREPO_ROOT/{area}` |
| `pipeline_worktree_path($issue, $area)` | feature branch 파일 수정 | `.workspace/worktrees/{area}/issue-{N}` |

### gh 명령 explicit repo

`gh api repos/{owner}/{repo}/...` 대신 `gh ... -R owner/repo` 또는 `pipeline_repo_name($area)` 사용.
cwd 의존 완전 제거.

### merge lock TTL 기반 전환

PID 기반 stale 판단 제거. TTL(기본 1800초) 기반으로 전환.
Bash tool 호출이 끊겨도 lock이 너무 빨리 회수되는 문제 해결.

### pipeline_merge_pr 단일 함수화

lock 획득 - sync - merge - release를 한 함수 안에서 처리.
별도 Bash tool 호출로 분리하면 lock holder PID가 달라지는 문제 원천 차단.

### area-scoped 경로

- worktree: `.workspace/worktrees/{area}/issue-{N}`
- state: `.workspace/pipeline/{area}/issue-{N}.state.json`
- log: `.workspace/pipeline/logs/{area}/issue-{N}-{stage}.log`
- message: `.workspace/messages/{area}-pr-{N}-{kind}.md`

### pipeline_state_update jq args 전달

`pipeline_state_update`가 `shift 3` 후 나머지 인자를 jq에 전달.
`pipeline_recovery_log`에서 `--argjson entry "$entry"` 정상 전달.

## 주요 원칙

- **Claude session root와 코드 수정 위치를 같은 개념으로 다루지 말 것**
- **gh 명령은 cwd 의존 대신 explicit repo 사용**
- **merge lock은 한 프로세스 안에서 acquire/release 완결**
- **모든 transient 파일 경로에 area 포함 필수**
